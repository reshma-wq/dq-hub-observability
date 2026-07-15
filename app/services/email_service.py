import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from google.cloud import bigquery
from app.utils.config import PROJECT_ID, TARGET_DATASET, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT

# Indian Standard Time is UTC+5:30
def get_ist_time():
    """Get current time in Indian Standard Time (UTC+5:30)"""
    utc_now = datetime.utcnow()
    ist_offset = timedelta(hours=5, minutes=30)
    return utc_now + ist_offset


class EmailNotificationService:
    """
    Service to send DQ check results via email after dashboard refresh.
    Fetches reports from dq_watchtower_results table and sends formatted email.
    """

    def __init__(self):
        # Load credentials from GCP Secret Manager (via config.py)
        self.sender_email = EMAIL_SENDER
        self.sender_password = EMAIL_PASSWORD
        self.recipient_emails = [email.strip() for email in EMAIL_RECIPIENT.split(',') if email.strip()]
        self.bq_client = bigquery.Client(project=PROJECT_ID)
        self.dataset = TARGET_DATASET
        
        # Validate email credentials are loaded
        print(f"[EmailService Init] sender_email: {'✓ Loaded: ' + self.sender_email if self.sender_email else '✗ NOT LOADED'}")
        print(f"[EmailService Init] recipient_emails: {'✓ Loaded: ' + str(self.recipient_emails) if self.recipient_emails else '✗ NOT LOADED'}")
        print(f"[EmailService Init] sender_password: {'✓ Loaded (length: ' + str(len(self.sender_password)) + ')' if self.sender_password else '✗ NOT LOADED'}")
        
        if not self.sender_email or not self.sender_password or not self.recipient_emails:
            print("[EmailService CRITICAL] Email credentials missing! Check Secret Manager:")
            print("  - EMAIL_SENDER")
            print("  - EMAIL_PASSWORD") 
            print("  - EMAIL_RECIPIENT")

    def fetch_executive_summary(self):
        """
        Fetch executive summary: Dataset Health %, Total Rules, Passed, Failed, Total Table Count, Timestamp.
        """
        try:
            query = f"""
            WITH latest_rules AS (
                SELECT *,
                ROW_NUMBER() OVER (PARTITION BY table_name, column_name, rule_name ORDER BY execution_ts DESC) AS rn
                FROM `{PROJECT_ID}.{self.dataset}.dq_watchtower_results`
                WHERE DATE(execution_ts) = (SELECT MAX(DATE(execution_ts)) FROM `{PROJECT_ID}.{self.dataset}.dq_watchtower_results`)
            ),
            summary AS (
                SELECT
                    COUNT(DISTINCT table_name) AS total_tables,
                    COUNT(*) AS total_rules,
                    SUM(CASE WHEN dq_status = 'PASS' THEN 1 ELSE 0 END) AS passed_rules,
                    SUM(CASE WHEN dq_status = 'FAIL' THEN 1 ELSE 0 END) AS failed_rules,
                    ROUND(100.0 * SUM(CASE WHEN dq_status = 'PASS' THEN 1 ELSE 0 END) / COUNT(*), 2) AS health_pct,
                    MAX(execution_ts) AS latest_execution_ts
                FROM latest_rules
                WHERE rn = 1
            )
            SELECT * FROM summary
            """
            
            query_job = self.bq_client.query(query)
            results = query_job.result()
            
            for row in results:
                return {
                    "total_tables": row.total_tables,
                    "total_rules": row.total_rules,
                    "passed_rules": row.passed_rules,
                    "failed_rules": row.failed_rules,
                    "health_pct": row.health_pct,
                    "latest_execution_ts": str(row.latest_execution_ts)
                }
            
            return None
        
        except Exception as e:
            print(f"ERROR fetching executive summary: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def fetch_health_by_table(self):
        """
        Fetch health by table: Table Name, Passed Checks, Failed Checks, Total Checks, 
        Check Health %, Total Records, Passed Records, Record Pass %.
        """
        try:
            query = f"""
            WITH latest_rules AS (
                SELECT *,
                ROW_NUMBER() OVER (PARTITION BY table_name, column_name, rule_name ORDER BY execution_ts DESC) AS rn
                FROM `{PROJECT_ID}.{self.dataset}.dq_watchtower_results`
                WHERE DATE(execution_ts) = (SELECT MAX(DATE(execution_ts)) FROM `{PROJECT_ID}.{self.dataset}.dq_watchtower_results`)
            ),
            table_health AS (
                SELECT
                    table_name,
                    COUNT(*) AS total_checks,
                    SUM(CASE WHEN dq_status = 'PASS' THEN 1 ELSE 0 END) AS passed_checks,
                    SUM(CASE WHEN dq_status = 'FAIL' THEN 1 ELSE 0 END) AS failed_checks,
                    ROUND(100.0 * SUM(CASE WHEN dq_status = 'PASS' THEN 1 ELSE 0 END) / COUNT(*), 2) AS check_health_pct,
                    SUM(COALESCE(total_records, 0)) AS total_records,
                    SUM(COALESCE(passed_records, 0)) AS passed_records,
                    CASE 
                        WHEN SUM(COALESCE(total_records, 0)) = 0 THEN 0
                        ELSE ROUND(100.0 * SUM(COALESCE(passed_records, 0)) / SUM(COALESCE(total_records, 0)), 2)
                    END AS record_pass_pct
                FROM latest_rules
                WHERE rn = 1
                GROUP BY table_name
            )
            SELECT * FROM table_health
            ORDER BY failed_checks DESC, table_name ASC
            """
            
            query_job = self.bq_client.query(query)
            results = query_job.result()
            
            table_data = []
            for row in results:
                table_data.append({
                    "table_name": row.table_name,
                    "passed_checks": row.passed_checks,
                    "failed_checks": row.failed_checks,
                    "total_checks": row.total_checks,
                    "check_health_pct": row.check_health_pct,
                    "total_records": row.total_records,
                    "passed_records": row.passed_records,
                    "record_pass_pct": row.record_pass_pct
                })
            
            return table_data
        
        except Exception as e:
            print(f"ERROR fetching health by table: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def fetch_priority_tables(self):
        """
        Fetch top 10 priority tables sorted by failed rule count (highest first).
        Returns top 10 tables with most critical issues + project/dataset info.
        Sorted: Most failed checks first → Least failed checks.
        """
        try:
            # Use the same health_by_table data and filter for failed rules
            health_data = self.fetch_health_by_table()
            
            # Filter tables with failed checks > 0
            priority_data = [
                {
                    "project_id": PROJECT_ID,
                    "dataset_name": self.dataset,
                    "table_name": table.get("table_name"),
                    "total_rules": table.get("total_checks"),
                    "passed_rules": table.get("passed_checks"),
                    "failed_rules": table.get("failed_checks"),
                    "health_pct": table.get("check_health_pct")
                }
                for table in health_data
                if table.get("failed_checks", 0) > 0
            ]
            
            # Sort by failed_rules descending (highest first)
            priority_data.sort(key=lambda x: x.get("failed_rules", 0), reverse=True)
            
            # Return only top 10
            return priority_data[:10]
        
        except Exception as e:
            print(f"ERROR fetching priority tables: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def draft_email_html(self, executive_summary, health_by_table, priority_tables):
        """
        Draft production-ready DQ health report email with proper table formatting.
        Clean corporate design with professional borders and spacing.
        """
        report_date = get_ist_time().strftime("%Y-%m-%d")
        
        if not executive_summary:
            return "<html><body><p>No DQ check results found.</p></body></html>"
        
        # Build Top 10 Priority Tables HTML
        priority_table_rows = ""
        
        if priority_tables:
            for table in priority_tables:
                project_id = table.get("project_id", "")
                dataset_name = table.get("dataset_name", "")
                table_name = table.get("table_name", "")
                total_rules = table.get("total_rules", 0)
                failed_rules = table.get("failed_rules", 0)
                health_pct = table.get("health_pct", 0)
                
                priority_table_rows += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #cccccc; text-align: left; background-color: #F5F5F5;">{table_name}</td>
                    <td style="padding: 10px; border: 1px solid #cccccc; text-align: left; background-color: #F5F5F5;">{project_id}</td>
                    <td style="padding: 10px; border: 1px solid #cccccc; text-align: left; background-color: #F5F5F5;">{dataset_name}</td>
                    <td style="padding: 10px; border: 1px solid #cccccc; text-align: center; background-color: #F5F5F5;">{total_rules}</td>
                    <td style="padding: 10px; border: 1px solid #cccccc; text-align: center; background-color: #F5F5F5;">{failed_rules}</td>
                    <td style="padding: 10px; border: 1px solid #cccccc; text-align: center; background-color: #F5F5F5;">{health_pct:.1f}%</td>
                </tr>
                """
        else:
            priority_table_rows = "<tr><td colspan='6' style='padding: 10px; border: 1px solid #cccccc; text-align: center;'>All tables healthy - No issues detected</td></tr>"
        
        html_content = (
            """
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: Arial, Calibri, sans-serif; color: #333333; line-height: 1.6; font-size: 16px; margin: 0; padding: 0;">
                
                <p style="margin: 0 0 12px 0; font-size: 16px;">Hello Team,</p>
                
                <p style="margin: 0 0 8px 0; font-size: 16px; color: #666666;"><strong>Project ID:</strong> """ + PROJECT_ID + """</p>
                <p style="margin: 0 0 12px 0; font-size: 16px; color: #666666;"><strong>Dataset Name:</strong> """ + self.dataset + """</p>
                
                <p style="margin: 0 0 12px 0; font-size: 16px;">Please find attached the DQ Health Report for """ + report_date + """.</p>
                
                <p style="margin: 0 0 16px 0; font-size: 16px;">This report provides a comprehensive overview of current data quality metrics. Review the Executive Summary below for key insights and the DQ Outages Requiring Attention section to identify impacted tables.</p>
                
                <p style="margin: 16px 0 12px 0; font-weight: bold; font-size: 15px; color: #1a1a1a;">Executive Summary</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 0 0 20px 0; border: 1px solid #999999;">
                    <tr>
                        <th style="padding: 10px; border: 1px solid #999999; text-align: center; font-weight: bold; background-color: #f5f5f5; font-size: 16px;">DQ Health Score (%)</th>
                        <th style="padding: 10px; border: 1px solid #999999; text-align: center; font-weight: bold; background-color: #f5f5f5; font-size: 16px;">Total Rules Evaluated</th>
                        <th style="padding: 10px; border: 1px solid #999999; text-align: center; font-weight: bold; background-color: #f5f5f5; font-size: 16px;">Passed Rules</th>
                        <th style="padding: 10px; border: 1px solid #999999; text-align: center; font-weight: bold; background-color: #f5f5f5; font-size: 16px;">Failed Rules</th>
                        <th style="padding: 10px; border: 1px solid #999999; text-align: center; font-weight: bold; background-color: #f5f5f5; font-size: 16px;">Monitored Tables</th>
                        <th style="padding: 10px; border: 1px solid #999999; text-align: center; font-weight: bold; background-color: #f5f5f5; font-size: 16px;">Impacted Tables</th>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #cccccc; text-align: center; font-size: 16px; background-color: #F5F5F5;">""" + f"{executive_summary['health_pct']:.1f}%" + """</td>
                        <td style="padding: 10px; border: 1px solid #cccccc; text-align: center; font-size: 16px; background-color: #F5F5F5;">""" + str(executive_summary['total_rules']) + """</td>
                        <td style="padding: 10px; border: 1px solid #cccccc; text-align: center; font-size: 16px; background-color: #F5F5F5;">""" + str(executive_summary['passed_rules']) + """</td>
                        <td style="padding: 10px; border: 1px solid #cccccc; text-align: center; font-size: 16px; background-color: #F5F5F5;">""" + str(executive_summary['failed_rules']) + """</td>
                        <td style="padding: 10px; border: 1px solid #cccccc; text-align: center; font-size: 16px; background-color: #F5F5F5;">""" + str(executive_summary['total_tables']) + """</td>
                        <td style="padding: 10px; border: 1px solid #cccccc; text-align: center; font-size: 16px; background-color: #F5F5F5;">""" + str(len(priority_tables)) + """</td>
                    </tr>
                </table>
                
                <p style="margin: 12px 0 0 0; font-size: 16px; font-style: italic; color: #1a1a1a;">Key Insight: Overall DQ health stands at """ + f"{executive_summary['health_pct']:.1f}%" + """, with """ + str(executive_summary['failed_rules']) + """ failed rules impacting """ + str(len(priority_tables)) + """ tables. Immediate investigation and remediation are recommended to prevent further data quality degradation.</p>
                
                <p style="margin: 16px 0 12px 0; font-weight: bold; font-size: 15px; color: #1a1a1a;">DQ Outages Requiring Attention</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 0 0 20px 0; border: 1px solid #999999;">
                    <tr>
                        <th style="padding: 10px; border: 1px solid #999999; text-align: left; font-weight: bold; background-color: #f5f5f5; font-size: 16px;">Table Name</th>
                        <th style="padding: 10px; border: 1px solid #999999; text-align: left; font-weight: bold; background-color: #f5f5f5; font-size: 16px;">Project ID</th>
                        <th style="padding: 10px; border: 1px solid #999999; text-align: left; font-weight: bold; background-color: #f5f5f5; font-size: 16px;">Dataset Name</th>
                        <th style="padding: 10px; border: 1px solid #999999; text-align: center; font-weight: bold; background-color: #f5f5f5; font-size: 16px;">Total Rules Evaluated</th>
                        <th style="padding: 10px; border: 1px solid #999999; text-align: center; font-weight: bold; background-color: #f5f5f5; font-size: 16px;">Failed Rules</th>
                        <th style="padding: 10px; border: 1px solid #999999; text-align: center; font-weight: bold; background-color: #f5f5f5; font-size: 16px;">DQ Health Score (%)</th>
                    </tr>
                    """ + priority_table_rows + """
                </table>
                
                <p style="margin: 16px 0 12px 0; font-weight: bold; font-size: 15px; color: #1a1a1a;">Attachments & Resources</p>
                
                <ul style="margin: 0 0 16px 0; padding-left: 20px; font-size: 16px;">
                    <li style="margin: 6px 0;">Excel Report: Detailed rule-level results and failure analysis.</li>
                </ul>
                
                <p style="margin: 0 0 16px 0; font-size: 16px;">For detailed analysis and rule-level results, please refer to the attached report and dashboard.</p>
                
                <p style="margin: 0 0 0 0; font-size: 16px;">Thanks,<br>Data Quality Team</p>
                
            </body>
        </html>
        """
        )
        
        return html_content

    def send_email(self, html_content, excel_file=None):
        """
        Send email with DQ check results and Excel attachment.
        Uses Gmail SMTP with app-specific password.
        """
        try:
            print(f"📧 Preparing email...")
            print(f"   Sender: {self.sender_email}")
            print(f"   Recipients: {', '.join(self.recipient_emails)}")
            
            # Create email message
            message = MIMEMultipart()
            message["Subject"] = f"DQ Health Report | {get_ist_time().strftime('%d-%b-%Y')}"
            message["From"] = self.sender_email
            message["To"] = ', '.join(self.recipient_emails)
            
            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Attach Excel file if provided
            if excel_file is not None:
                try:
                    print(f"📎 Attaching Excel file...")
                    
                    # Read file content
                    if hasattr(excel_file, 'read'):
                        file_content = excel_file.read()
                    else:
                        file_content = excel_file
                    
                    # Create attachment
                    attachment = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    attachment.set_payload(file_content)
                    encoders.encode_base64(attachment)
                    
                    filename = f"DQ_Report_{get_ist_time().strftime('%Y-%m-%d')}.xlsx"
                    attachment.add_header(
                        "Content-Disposition",
                        f"attachment; filename=\"{filename}\""
                    )
                    message.attach(attachment)
                    print(f"✅ Excel file attached: {filename} (Size: {len(file_content)} bytes)")
                except Exception as e:
                    print(f"⚠️ Failed to attach Excel file: {str(e)}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"⚠️ No Excel file to attach")
            
            print(f"🔐 Connecting to Gmail SMTP server...")
            # Send email via Gmail SMTP
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
                print(f"✅ Connected to SMTP server")
                server.login(self.sender_email, self.sender_password)
                print(f"✅ Logged in successfully")
                server.sendmail(self.sender_email, self.recipient_emails, message.as_string())
                print(f"✅ Email message sent")
            
            print(f"✅✅✅ Email delivered successfully to {', '.join(self.recipient_emails)}")
            return True
        
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ Authentication failed: {str(e)}")
            print(f"❌ Check if app password is correct and 2FA is enabled")
            return False
        except Exception as e:
            print(f"❌ ERROR sending email: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def send_dq_report(self):
        """
        Main function: Generate executive summary email with Excel report, and send.
        Call this after dashboard refresh.
        """
        print("📧 Generating DQ health report email...")
        
        # Fetch all required data
        print("📊 Fetching executive summary...")
        executive_summary = self.fetch_executive_summary()
        
        if not executive_summary:
            print("⚠️ No DQ results found for report")
            return False
        
        print("📊 Fetching health by table...")
        health_by_table = self.fetch_health_by_table()
        
        print("📊 Fetching priority tables...")
        priority_tables = self.fetch_priority_tables()
        
        # Draft HTML email content
        print("📝 Drafting email content...")
        html_content = self.draft_email_html(executive_summary, health_by_table, priority_tables)
        
        # Generate Excel report
        excel_file = None
        try:
            from app.services.report_generator import ReportGenerator
            print("📊 Generating Excel report...")
            report_gen = ReportGenerator()
            excel_file = report_gen.generate_report()
            if excel_file:
                print("✅ Excel report generated successfully")
        except Exception as e:
            print(f"⚠️ Failed to generate Excel report: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("📧 Sending email...")
        return self.send_email(html_content, excel_file)
