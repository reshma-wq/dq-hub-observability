from datetime import datetime
import time
import requests
from google.auth.transport.requests import Request
import google.auth
import json
from google.cloud import bigquery

from app.adapters.bq_adapter import BigQueryAdapter
from app.utils.config import PROJECT_ID, TARGET_DATASET, SCAN_JOB_MAPPING_JSON, PROFILING_TABLE

# Scan timeout constant
SCAN_TIMEOUT_SECONDS = 300  # 5 minutes


class RuleService:

    def __init__(self):
        self.bq = BigQueryAdapter(PROJECT_ID)
        self.bq_client = bigquery.Client(project=PROJECT_ID)
        self.project_id = PROJECT_ID
        self.dataset = TARGET_DATASET
        self.profiling_table = PROFILING_TABLE
        self.scan_job_mapping = json.loads(SCAN_JOB_MAPPING_JSON)
        self.scan_timeout_seconds = SCAN_TIMEOUT_SECONDS
        # Get default credentials for API calls
        self.credentials, _ = google.auth.default()

    def compile_sql(self, table_name, rule):
        # Use condition as-is - both Template and Custom SQL send the failure condition
        condition = rule.sql_condition

        # Check if this is a unique rule (condition contains COUNT)
        if 'COUNT(*)' in condition:
            # This is a unique rule - find duplicates
            # condition will be "COUNT(*) > 1"
            return f"""
            SELECT
                CURRENT_TIMESTAMP() AS execution_ts,
                '{table_name}' AS table_name,
                '{rule.column_name}' AS column_name,
                '{rule.rule_name}' AS rule_name,
                COUNT(*) AS total_records,
                SUM(CASE WHEN cnt > 1 THEN 1 ELSE 0 END) AS failed_records
            FROM (
                SELECT *, COUNT(*) OVER (PARTITION BY {rule.column_name}) as cnt
                FROM `{PROJECT_ID}.{TARGET_DATASET}.{table_name}`
            )
            """
        
        # Standard WHERE condition
        return f"""
        SELECT
            CURRENT_TIMESTAMP() AS execution_ts,
            '{table_name}' AS table_name,
            '{rule.column_name}' AS column_name,
            '{rule.rule_name}' AS rule_name,
            COUNT(*) AS total_records,
            SUM(
                CASE
                    WHEN {condition}
                    THEN 1
                    ELSE 0
                END
            ) AS failed_records
        FROM `{PROJECT_ID}.{TARGET_DATASET}.{table_name}`
        """

    def insert_watchtower_result(self, dataset, result_record):

        table_id = f"{self.project_id}.{dataset}.dq_watchtower_results"

        rows = [result_record]

        errors = self.bq_client.insert_rows_json(
            table_id,
            rows
        )

        if errors:
            raise Exception(errors)

    def update_execution_progress(self,dataset,run_id,completed_rules):
        query = f"""
            UPDATE `{self.project_id}.{dataset}.dq_execution_runs`
            SET completed_rules = {completed_rules}
            WHERE run_id = '{run_id}'
            """

        self.bq_client.query(query).result()

    def complete_execution_run(self,dataset,run_id):
        query = f"""
                UPDATE `{self.project_id}.{dataset}.dq_execution_runs`
            SET
                status = 'SUCCESS',
                completed_at = CURRENT_TIMESTAMP()
                WHERE run_id = '{run_id}'
            """

        self.bq_client.query(query).result()   

    def get_execution_status(self,dataset,run_id):
        query = f"""
            SELECT *
            FROM `{self.project_id}.{dataset}.dq_execution_runs`
            WHERE run_id = '{run_id}'
            """

        results = list(
            self.bq_client.query(query).result()
        )

        if not results:
            return {}

        row = results[0]

        progress_percentage = int(
            (
                row["completed_rules"] /
                row["total_rules"]
            ) * 100
        ) if row["total_rules"] > 0 else 0

        return {
            "run_id": row["run_id"],
            "status": row["status"],
            "total_rules": row["total_rules"],
            "completed_rules": row["completed_rules"],
            "progress_percentage": progress_percentage
        }     

    def get_rules(self, dataset, table_name):
        """Fetch all active rules for a table"""
        return self.bq.get_active_rules(dataset, table_name)

    def register_rules(self, table_name, rules):
        print("REGISTERING RULES")
        print(rules)

        for rule in rules:

            compiled_sql = self.compile_sql(table_name, rule)

            registry_record = {
                "table_name": table_name,
                "column_name": rule.column_name,
                "rule_name": rule.rule_name,
                "rule_category":rule.rule_category,
                "description": rule.description,
                "sql_condition": rule.sql_condition,
                "compiled_sql": compiled_sql,
                "created_at": datetime.utcnow().isoformat(),
                "active_flag": "Y"
            }

            self.bq.register_rule(
                TARGET_DATASET,
                registry_record
            )

        return {
            "status": "success",
            "rules_registered": len(rules)
        }

    def register_anomalies(self, table_name, anomalies):
        """Register selected anomalies in dq_anomaly_registry table"""
        print("REGISTERING ANOMALIES")
        print(anomalies)

        for anomaly in anomalies:
            # Handle both dict and string (JSON) formats
            if isinstance(anomaly, str):
                import json
                anomaly = json.loads(anomaly)
            
            registry_record = {
                "table_name": table_name,
                "column_name": anomaly.get("column_name"),
                "anomaly_name": anomaly.get("anomaly_name"),
                "anomaly_category": anomaly.get("anomaly_category"),
                "description": anomaly.get("description"),
                "compiled_sql": anomaly.get("compiled_sql"),
                "created_at": datetime.utcnow().isoformat(),
                "active_flag": "Y"
            }

            self.bq.register_anomaly(
                TARGET_DATASET,
                registry_record
            )

        return {
            "status": "success",
            "anomalies_registered": len(anomalies)
        }

    def preview_data(self, table_name, sql_condition):
        """Preview data for a SQL condition - return failing and passing records"""
        try:
            # Get top 10 failing records
            failing_query = f"""
            SELECT *
            FROM `{PROJECT_ID}.{TARGET_DATASET}.{table_name}`
            WHERE {sql_condition}
            LIMIT 10
            """
            failing_results = list(self.bq.client.query(failing_query).result())
            
            # Get top 10 passing records
            passing_query = f"""
            SELECT *
            FROM `{PROJECT_ID}.{TARGET_DATASET}.{table_name}`
            WHERE NOT ({sql_condition})
            LIMIT 10
            """
            passing_results = list(self.bq.client.query(passing_query).result())
            
            # Count totals
            count_query = f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN {sql_condition} THEN 1 ELSE 0 END) as failing
            FROM `{PROJECT_ID}.{TARGET_DATASET}.{table_name}`
            """
            count_results = list(self.bq.client.query(count_query).result())
            total_rows = count_results[0]['total'] if count_results else 0
            total_failing = count_results[0]['failing'] if count_results else 0
            total_passing = total_rows - total_failing
            
            # Extract column names
            columns = list(failing_results[0].keys()) if failing_results else (list(passing_results[0].keys()) if passing_results else [])
            
            return {
                "status": "success",
                "total_scanned": total_rows,
                "total_passing": total_passing,
                "total_failing": total_failing,
                "failing_rows": [dict(row) for row in failing_results],
                "passing_rows": [dict(row) for row in passing_results],
                "columns": columns
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "total_scanned": 0,
                "total_passing": 0,
                "total_failing": 0,
                "failing_rows": [],
                "passing_rows": [],
                "columns": []
            }

    # ===== DATA CATALOG / PROFILING METHODS =====
    
    def get_scan_job_id(self, table_name: str):
        return self.scan_job_mapping.get(table_name)

    def trigger_scan(self, table_name: str):
        try:
            scan_identifier = self.get_scan_job_id(table_name)
            
            if not scan_identifier:
                print(f"Note: No scan configured for table: {table_name}")
                return {
                    "status": "error",
                    "error": f"No scan configured for table: {table_name}"
                }
            
            print(f"Looking for scan: {scan_identifier}")
            
            # Refresh credentials
            self.credentials.refresh(Request())
            
            # List all data scans via REST API
            parent = f"projects/{self.project_id}/locations/us-central1"
            list_url = f"https://dataplex.googleapis.com/v1/{parent}/dataScans"
            
            headers = {
                "Authorization": f"Bearer {self.credentials.token}",
                "Content-Type": "application/json"
            }
            
            print(f"Listing scans from: {list_url}")
            response = requests.get(list_url, headers=headers)
            
            if response.status_code != 200:
                print(f"Error listing scans: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "error": f"Failed to list scans: {response.text}"
                }
            
            scans = response.json().get('dataScans', [])
            print(f"Found {len(scans)} scans total")
            
            # Try to match by name first (exact match on the resource ID)
            target_scan = None
            
            # Check if scan_identifier is a full resource name or just the ID
            if scan_identifier.startswith('projects/'):
                # It's a full resource name
                for scan in scans:
                    if scan.get('name') == scan_identifier:
                        target_scan = scan
                        break
            else:
                # It's a simple name/display name - try both
                for scan in scans:
                    scan_name = scan.get('name', '')
                    display_name = scan.get('displayName', '')
                    scan_id = scan_name.split('/')[-1]  # Extract ID from full path
                    
                    print(f"Checking scan: name={scan_name}, displayName={display_name}, id={scan_id}")
                    
                    # Match by ID, display name, or full name
                    if (scan_identifier == scan_id or 
                        scan_identifier == display_name or 
                        scan_identifier == scan_name):
                        target_scan = scan
                        print(f"MATCHED!")
                        break
            
            if not target_scan:
                print(f"Scan not found with identifier: {scan_identifier}")
                return {
                    "status": "error",
                    "error": f"Scan '{scan_identifier}' not found in Dataplex"
                }
            
            print(f"Found target scan: {target_scan['name']}")
            
            # Trigger the scan by calling :run
            scan_name = target_scan['name']
            run_url = f"https://dataplex.googleapis.com/v1/{scan_name}:run"
            
            print(f"Triggering scan: {run_url}")
            run_response = requests.post(run_url, headers=headers, json={})
            
            print(f"Trigger response status: {run_response.status_code}")
            print(f"Trigger response: {run_response.text}")
            
            if run_response.status_code in [200, 201]:
                print(f"Successfully triggered scan: {scan_identifier}")
                return {
                    "status": "triggered",
                    "scan_id": scan_name,
                    "message": f"Scan '{scan_identifier}' triggered successfully"
                }
            elif run_response.status_code == 400:
                # Check if it's a "already running" error
                response_text = run_response.text
                if "already a pending" in response_text or "FAILED_PRECONDITION" in response_text:
                    print(f"Scan already running, will wait for completion: {scan_identifier}")
                    return {
                        "status": "triggered",
                        "scan_id": scan_name,
                        "message": f"Scan '{scan_identifier}' is already running"
                    }
                else:
                    print(f"Error triggering scan: {run_response.status_code} - {response_text}")
                    return {
                        "status": "error",
                        "error": f"Failed to trigger scan: {response_text}"
                    }
            else:
                print(f"Error triggering scan: {run_response.status_code} - {run_response.text}")
                return {
                    "status": "error",
                    "error": f"Failed to trigger scan: {run_response.text}"
                }
            
        except Exception as e:
            print(f"Error triggering scan: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": f"Failed to trigger scan: {str(e)}"
            }

    def wait_for_scan_completion(self, table_name: str):
        try:
            scan_id = self.get_scan_job_id(table_name)
            
            print(f"Waiting for scan completion for: {table_name}")
            
            # Poll for data availability
            start_time = time.time()
            poll_interval = 5  # Check every 5 seconds
            max_wait = self.scan_timeout_seconds  # Use timeout from config
            
            while time.time() - start_time < max_wait:
                elapsed = time.time() - start_time
                
                # Check if data is available
                query = f"SELECT MAX(job_end_time) as latest_time, COUNT(*) as total_records FROM `{self.profiling_table}`"
                
                try:
                    results = list(self.bq_client.query(query).result())
                    if results:
                        latest_time = results[0]['latest_time']
                        total_records = results[0]['total_records']
                        
                        # If data is available, we're done
                        if total_records and total_records > 0:
                            print(f"[{elapsed:.0f}s] Scan data is available! Total records: {total_records}, Latest scan: {latest_time}")
                            break
                        else:
                            print(f"[{elapsed:.0f}s] Waiting for scan data... (current: {total_records} records)")
                except Exception as e:
                    print(f"Error checking data: {str(e)}")
                
                time.sleep(poll_interval)
            
            elapsed = time.time() - start_time
            print(f"Scan wait completed after {elapsed:.0f}s")
            
            return {
                "status": "completed",
                "scan_id": scan_id,
                "message": f"Scan completed, profiling data ready"
            }
            
        except Exception as e:
            print(f"Error in wait_for_scan_completion: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "completed",
                "scan_id": self.get_scan_job_id(table_name),
                "message": "Fetching available profiling data"
            }

    def get_table_profile(self, table_name: str):
        try:
            # Get the latest job_end_time first
            latest_query = f"""
            SELECT MAX(job_end_time) as latest_time
            FROM `{self.profiling_table}`
            """
            
            latest_results = list(self.bq_client.query(latest_query).result())
            latest_time = latest_results[0]['latest_time'] if latest_results else None
            
            if not latest_time:
                return {
                    "status": "error",
                    "error": "No profiling data available",
                    "table_name": table_name,
                    "columns": []
                }
            
            # Fetch statistics and unnest top_n data
            query = f"""
            SELECT
                column_name,
                column_type,
                percent_null,
                percent_unique,
                min_string_length,
                max_string_length,
                average_string_length,
                average_value,
                standard_deviation,
                min_value,
                quartile_lower,
                quartile_median,
                quartile_upper,
                max_value,
                top_n
            FROM `{self.profiling_table}`
            WHERE job_end_time = @latest_time
            ORDER BY column_name
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("latest_time", "TIMESTAMP", latest_time)
                ]
            )
            
            results = list(self.bq_client.query(query, job_config=job_config).result())
            
            # Process results and build columns data
            columns_data = []
            for row in results:
                row_dict = dict(row.items())
                col_name = row_dict.get('column_name')
                
                # Extract top_n array from the RECORD field
                top_n_array = row_dict.get('top_n') or []
                top_n_data = []
                
                if top_n_array:
                    # Convert top_n records to list of dicts
                    for item in top_n_array:
                        if isinstance(item, dict):
                            top_n_data.append({
                                "value": str(item.get('value', '')),
                                "count": int(item.get('count', 0)),
                                "percent": float(item.get('percent', 0))
                            })
                
                columns_data.append({
                    "column_name": col_name,
                    "column_type": row_dict.get('column_type'),
                    "null_percentage": row_dict.get('percent_null', 0),
                    "unique_percentage": row_dict.get('percent_unique', 0),
                    "null_percent": row_dict.get('percent_null', 0),
                    "unique_count": int(row_dict.get('percent_unique', 0)) if row_dict.get('percent_unique') else 0,
                    "average": row_dict.get('average_value'),
                    "standard_deviation": row_dict.get('standard_deviation'),
                    "minimum": row_dict.get('min_value'),
                    "lower_quartile": row_dict.get('quartile_lower'),
                    "median_quartile": row_dict.get('quartile_median'),
                    "upper_quartile": row_dict.get('quartile_upper'),
                    "maximum": row_dict.get('max_value'),
                    "min_string_length": row_dict.get('min_string_length'),
                    "max_string_length": row_dict.get('max_string_length'),
                    "average_string_length": row_dict.get('average_string_length'),
                    "top_n_data": top_n_data
                })
            
            return {
                "status": "success",
                "table_name": table_name,
                "columns": columns_data
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "table_name": table_name,
                "columns": []
            }

    def get_column_profile(self, table_name: str, column_name: str):
        try:
            query = f"""
            SELECT *
            FROM `{self.profiling_table}`
            WHERE column_name = @column_name
            ORDER BY job_end_time DESC
            LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("column_name", "STRING", column_name)
                ]
            )
            
            results = list(self.bq_client.query(query, job_config=job_config).result())
            
            if not results:
                return {
                    "status": "error",
                    "error": f"No profiling data found for column {column_name}",
                    "column_name": column_name
                }
            
            row = results[0]
            row_dict = dict(row.items())
            
            profile_stats = {
                "average": row_dict.get('average_value'),
                "standard_deviation": row_dict.get('standard_deviation'),
                "minimum": row_dict.get('min_value'),
                "lower_quartile": row_dict.get('quartile_lower'),
                "median_quartile": row_dict.get('quartile_median'),
                "upper_quartile": row_dict.get('quartile_upper'),
                "maximum": row_dict.get('max_value'),
                "min_string_length": row_dict.get('min_string_length'),
                "max_string_length": row_dict.get('max_string_length'),
                "average_string_length": row_dict.get('average_string_length')
            }
            
            return {
                "status": "success",
                "column_name": column_name,
                "column_type": row_dict.get('column_type'),
                "null_percentage": row_dict.get('percent_null', 0),
                "unique_percentage": row_dict.get('percent_unique', 0),
                "statistics": profile_stats,
                "scan_date": str(row_dict.get('job_end_time'))
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "column_name": column_name
            }