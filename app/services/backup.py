import uuid
from datetime import datetime
from google.cloud import bigquery
from app.utils.config import PROJECT_ID, TARGET_DATASET

# Table incremental configuration - only incremental column
TABLE_INCREMENTAL_CONFIG = {
    "marketing_campaigns": "created_ts",
    "customer_orders": "order_date",
    "customer_profiles": "signup_date",
    "sales_transactions": "transaction_date",
    "product_catalog": "last_updated"
}

class BackupService:
    
    def __init__(self):
        self.bq_client = bigquery.Client(project=PROJECT_ID)
        self.project_id = PROJECT_ID
        self.dataset = TARGET_DATASET
        self.backup_table = f"{PROJECT_ID}.{TARGET_DATASET}.dq_scan_backup"
    
    def get_incremental_column(self, table_name):
        """Get incremental column for a table"""
        return TABLE_INCREMENTAL_CONFIG.get(table_name)
    
    def get_incremental_range(self, table_name):
        """
        Fetch min and max incremental values for NEW data in current run.
        Compares with previous scan to identify only new/incremental records.
        """
        try:
            incremental_column = self.get_incremental_column(table_name)
            
            # Full load - no range needed
            if incremental_column is None:
                return {
                    "start_date": "Full Load",
                    "end_date": "Full Load"
                }
            
            # Get latest run's end_date to find incremental data
            latest_scan = self.get_latest_scan(table_name)
            
            if latest_scan:
                # Previous run exists - find ONLY NEW records after latest_end
                latest_end = latest_scan.get('end_date')
                col_type = self._get_column_type(table_name, incremental_column)
                
                # Query to find NEW records (where incremental column > latest max)
                query = f"""
                SELECT
                    MIN(CAST({incremental_column} AS STRING)) as min_value,
                    MAX(CAST({incremental_column} AS STRING)) as max_value,
                    COUNT(*) as record_count
                FROM `{self.project_id}.{self.dataset}.{table_name}`
                WHERE {incremental_column} > CAST(@latest_end AS {col_type})
                """
                
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("latest_end", "STRING", latest_end)
                    ]
                )
                
                results = list(self.bq_client.query(query, job_config=job_config).result())
                
                if results:
                    row = results[0]
                    min_val = row['min_value']
                    max_val = row['max_value']
                    
                    # If new data found, return the NEW incremental range
                    if min_val is not None and max_val is not None:
                        return {
                            "start_date": str(min_val),
                            "end_date": str(max_val)
                        }
                    else:
                        # No new data found
                        return {
                            "start_date": "",
                            "end_date": ""
                        }
            else:
                # First run - no previous scan exists, get ALL data currently in table
                query = f"""
                SELECT
                    MIN(CAST({incremental_column} AS STRING)) as min_value,
                    MAX(CAST({incremental_column} AS STRING)) as max_value,
                    COUNT(*) as record_count
                FROM `{self.project_id}.{self.dataset}.{table_name}`
                """
                
                results = list(self.bq_client.query(query).result())
                
                if results:
                    row = results[0]
                    min_val = row['min_value']
                    max_val = row['max_value']
                    
                    if min_val is not None and max_val is not None:
                        return {
                            "start_date": str(min_val),
                            "end_date": str(max_val)
                        }
            
            return {
                "start_date": "",
                "end_date": ""
            }
            
        except Exception as e:
            print(f"Error getting incremental range for {table_name}: {str(e)}")
            return {
                "start_date": "",
                "end_date": ""
            }
    
    def _get_column_type(self, table_name, column_name):
        """Get the data type of a column to use in WHERE clause comparison"""
        try:
            query = f"""
            SELECT data_type
            FROM `{self.project_id}.{self.dataset}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = @table_name AND column_name = @column_name
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("table_name", "STRING", table_name),
                    bigquery.ScalarQueryParameter("column_name", "STRING", column_name)
                ]
            )
            
            results = list(self.bq_client.query(query, job_config=job_config).result())
            
            if results:
                col_type = results[0]['data_type']
                # Map BigQuery types to simple names
                if 'DATE' in col_type.upper():
                    return 'DATE'
                elif 'TIMESTAMP' in col_type.upper():
                    return 'TIMESTAMP'
                elif 'STRING' in col_type.upper():
                    return 'STRING'
                elif 'INT' in col_type.upper():
                    return 'INT64'
                return col_type
            
            return 'STRING'  # Default fallback
            
        except Exception as e:
            print(f"Error getting column type: {str(e)}")
            return 'STRING'
    
    def record_backup_entry(self, run_id, table_name):
        """Record a backup entry for a table scan"""
        try:
            # Get incremental range
            incremental_info = self.get_incremental_range(table_name)
            
            # Check if this is a new incremental load (for non-full-load tables)
            incremental_column = self.get_incremental_column(table_name)
            
            # If no incremental column (full load), always record
            if incremental_column is None:
                pass
            else:
                # Check if there's actually new data
                if not incremental_info.get("start_date") or incremental_info.get("start_date") == "":
                    return {
                        "status": "skipped",
                        "message": f"No new data for {table_name} - skipping backup entry"
                    }
            
            # Build backup record
            backup_record = {
                "run_id": run_id,
                "table_name": table_name,
                "start_date": incremental_info.get("start_date", ""),
                "end_date": incremental_info.get("end_date", "")
            }
            
            # Insert to backup table
            errors = self.bq_client.insert_rows_json(
                self.backup_table,
                [backup_record]
            )
            
            if errors:
                print(f"Error inserting backup record for {table_name}: {errors}")
                return {
                    "status": "error",
                    "message": f"Failed to backup {table_name}",
                    "errors": errors
                }
            
            print(f"✅ Backup recorded for {table_name}: {backup_record}")
            return {
                "status": "success",
                "message": f"Backup recorded for {table_name}",
                "record": backup_record
            }
            
        except Exception as e:
            print(f"Error recording backup entry for {table_name}: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to backup {table_name}",
                "error": str(e)
            }
    
    def record_backup_for_multiple_tables(self, run_id, table_names):
        """Record backup entries for multiple tables"""
        results = []
        
        for table_name in table_names:
            result = self.record_backup_entry(run_id, table_name)
            results.append({
                "table_name": table_name,
                "result": result
            })
        
        return {
            "run_id": run_id,
            "status": "completed",
            "backup_results": results
        }
    
    def auto_backup_on_run(self, table_names=None):
        """
        Automatically record backup for specified tables
        Call this method when user clicks "Run All Check"
        Generates unique run_id automatically
        
        Args:
            table_names: List of table names to backup. If None, backups only tables in TABLE_INCREMENTAL_CONFIG
        """
        if table_names is None:
            # Only backup tables that are configured in TABLE_INCREMENTAL_CONFIG
            table_names = list(TABLE_INCREMENTAL_CONFIG.keys())
        
        run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"Auto-backup started: {run_id}")
        print(f"Tables to backup: {table_names}")
        result = self.record_backup_for_multiple_tables(run_id, table_names)
        
        return result
    
    def get_latest_scan(self, table_name):
        """Get latest scan info for a table"""
        try:
            query = f"""
            WITH ranked_scans AS (
                SELECT 
                    *,
                    ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY run_id DESC) as rn
                FROM `{self.backup_table}`
                WHERE table_name = @table_name
            )
            SELECT *
            FROM ranked_scans
            WHERE rn = 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("table_name", "STRING", table_name)
                ]
            )
            
            results = list(self.bq_client.query(query, job_config=job_config).result())
            
            if results:
                row = results[0]
                return {k: v for k, v in row.items() if k != 'rn'}
            
            return None
            
        except Exception as e:
            print(f"Error fetching latest scan for {table_name}: {str(e)}")
            return None
    
    def get_previous_scan(self, table_name):
        """Get the second-most-recent scan for comparison (for anomaly detection)"""
        try:
            # Get the second most recent scan (rn=2) for comparison purposes
            query = f"""
            WITH ranked_scans AS (
                SELECT 
                    *,
                    ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY run_id DESC) as rn
                FROM `{self.backup_table}`
                WHERE table_name = @table_name
            )
            SELECT *
            FROM ranked_scans
            WHERE rn = 2
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("table_name", "STRING", table_name)
                ]
            )
            
            results = list(self.bq_client.query(query, job_config=job_config).result())
            
            if results:
                row = results[0]
                return {k: v for k, v in row.items() if k != 'rn'}
            
            return None
            
        except Exception as e:
            print(f"Error fetching previous scan for {table_name}: {str(e)}")
            return None

    def get_all_scans(self, table_name):
        """Get all historical scans for a table"""
        try:
            query = f"""
            SELECT 
                *
            FROM `{self.backup_table}`
            WHERE table_name = @table_name
            ORDER BY run_id DESC
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("table_name", "STRING", table_name)
                ]
            )
            
            results = list(self.bq_client.query(query, job_config=job_config).result())
            
            if results:
                return {
                    "table_name": table_name,
                    "scan_count": len(results),
                    "scans": [dict(row) for row in results]
                }
            
            return {
                "table_name": table_name,
                "scan_count": 0,
                "scans": []
            }
            
        except Exception as e:
            print(f"Error fetching all scans for {table_name}: {str(e)}")
            return {
                "table_name": table_name,
                "error": str(e)
            }
