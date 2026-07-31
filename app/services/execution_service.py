import time
import uuid
from datetime import datetime

from app.adapters.bq_adapter import BigQueryAdapter
from app.utils.config import PROJECT_ID, TARGET_DATASET


class ExecutionService:

    def __init__(self):

        self.bq = BigQueryAdapter(PROJECT_ID)
        self.target_dataset = TARGET_DATASET

    def run_checks(self, table_name):
            # Handle "Run all checks" - if table_name is None, get only configured tables
            if table_name is None:
                from app.services.backup import TABLE_INCREMENTAL_CONFIG
                print("[run_checks] Running checks for ALL configured tables...")
                # Only process tables that are in TABLE_INCREMENTAL_CONFIG
                all_tables = list(TABLE_INCREMENTAL_CONFIG.keys())
                print(f"[run_checks] Found {len(all_tables)} configured tables: {all_tables}")
                
                all_results = []
                for table in all_tables:
                    print(f"[run_checks] Running checks for table: {table}")
                    try:
                        result = self.run_checks(table)  # Recursively call for each table
                        all_results.append(result)
                    except Exception as e:
                        print(f"[run_checks] Error processing table {table}: {str(e)}")
                        all_results.append({"table": table, "status": "failed", "error": str(e)})
                
                # Return combined results
                print(f"[run_checks] All tables processed. Total: {len(all_results)}")
                return {
                    "status": "completed",
                    "tables_processed": len(all_tables),
                    "results": all_results
                }
            
            # Original single-table logic (only executes if table_name is not None)
            run_id = str(uuid.uuid4())

            rules = self.bq.get_registered_rules(
                self.target_dataset,
                table_name
            )

            print("RULES FETCHED")
            print(rules)
            print(len(rules))

            total_rules = len(rules)

            failed_rules = 0
            completed = 0
            
            # Capture start time BEFORE loop begins
            scan_started_at = datetime.utcnow().isoformat()

            print("ENTERING LOOP")

            for rule in rules:

                try:

                    print("RUNNING RULE")
                    print(rule)

                    start_time = time.time()

                    result = self.bq.execute_rule_sql(
                        rule.compiled_sql
                    )

                    execution_time_ms = int(
                        (
                            time.time() -
                            start_time
                        ) * 1000
                    )

                    total_records = result.get(
                        "total_records",
                        0
                    )

                    failed_records = result.get(
                        "failed_records",
                        0
                    )

                    passed_records = (
                        total_records -
                        failed_records
                    )

                    pass_percentage = (
                        (
                            passed_records /
                            total_records
                        ) * 100
                    ) if total_records > 0 else 0

                    self.bq.insert_watchtower_result(
                        self.target_dataset,
                        {

                            "execution_ts":
                                datetime.utcnow().isoformat(),

                            "run_id":
                                run_id,

                            "table_name":
                                rule.table_name,

                            "column_name":
                                rule.column_name,

                            "rule_name":
                                rule.rule_name,

                            "total_records":
                                total_records,

                            "passed_records":
                                passed_records,

                            "failed_records":
                                failed_records,

                            "pass_percentage":
                                pass_percentage,

                            "execution_time_ms":
                                execution_time_ms,

                            "execution_status":
                                "SUCCESS",

                            "dq_status":
                                (
                                    "FAIL"
                                    if failed_records > 0
                                    else "PASS"
                                )
                        }
                    )

                    completed += 1

                    print("INSERT SUCCESS")

                except Exception as e:

                    failed_rules += 1

                    print("RULE FAILED")
                    print(str(e))

                    continue

            # BACKUP MUST BE RECORDED BEFORE EXECUTING ANOMALIES
            # So anomalies can fetch the correct latest/previous dates
            print("RECORDING BACKUP FOR TABLE")
            from app.services.backup import BackupService
            backup_service_internal = BackupService()
            backup_result = backup_service_internal.record_backup_entry(run_id, table_name)
            print(f"✅ Backup recorded: {backup_result}")

            # NOW execute anomalies after backup is recorded
            print("EXECUTING ANOMALIES")
            self.execute_anomalies(table_name, run_id)

            print("EXECUTION COMPLETED")

            # Capture the completed timestamp
            completed_at = datetime.utcnow().isoformat()

            # Create execution run record with final values (after all rules executed)
            self.bq.create_execution_run(
                self.target_dataset,
                {
                    "run_id": run_id,
                    "table_name": table_name,
                    "total_rules": total_rules,
                    "completed_rules": completed,
                    "status": "SUCCESS",
                    "started_at": scan_started_at,
                    "completed_at": completed_at
                }
            )

            return {
                "run_id": run_id,
                "status": "started",
                "total_rules": total_rules,
                "completed_rules": completed,
                "failed_rules": failed_rules,
                "completed_at": completed_at
            }

    def execute_anomalies(self, table_name, run_id):
        """Execute all registered anomalies for a table and store results"""
        try:
            from app.services.backup import BackupService
            
            # Get registered anomalies
            anomalies = self.bq.get_registered_anomalies(
                self.target_dataset,
                table_name
            )
            
            print(f"ANOMALIES FETCHED: {len(anomalies)}")
            
            if not anomalies:
                print("No anomalies to execute")
                return
            
            # Get latest and previous scan dates from backup table
            backup_service = BackupService()
            latest_scan = backup_service.get_latest_scan(table_name)
            previous_scan = backup_service.get_previous_scan(table_name)
            
            # If no scans exist, skip anomaly execution
            if not latest_scan:
                print(f"No backup records for {table_name} - skipping anomaly execution")
                return
            
            # Get date ranges
            current_start = latest_scan.get('start_date')
            current_end = latest_scan.get('end_date')
            previous_start = previous_scan.get('start_date') if previous_scan else current_start
            previous_end = previous_scan.get('end_date') if previous_scan else current_end
            
            print(f"Date ranges - Previous: {previous_start} to {previous_end}, Current: {current_start} to {current_end}")
            
            # Execute each anomaly's compiled_sql
            for anomaly in anomalies:
                try:
                    print(f"EXECUTING ANOMALY: {anomaly.get('anomaly_name')}")
                    
                    # Get compiled_sql with placeholders
                    compiled_sql_template = anomaly.get("compiled_sql")
                    
                    print(f"Template SQL (first 200 chars): {compiled_sql_template[:200]}")
                    print(f"Previous dates: {previous_start} to {previous_end}")
                    print(f"Current dates: {current_start} to {current_end}")
                    
                    # Replace placeholders with actual dates
                    compiled_sql = compiled_sql_template.replace(
                        "{previous_start}", previous_start
                    ).replace(
                        "{previous_end}", previous_end
                    ).replace(
                        "{current_start}", current_start
                    ).replace(
                        "{current_end}", current_end
                    )
                    
                    print(f"Replaced placeholders with dates")
                    print(f"Final SQL (first 300 chars): {compiled_sql[:300]}")
                    
                    start_time = time.time()
                    
                    # Execute compiled_sql with replaced dates
                    results = self.bq.execute_anomaly_sql(compiled_sql)
                    
                    execution_time_ms = int(
                        (time.time() - start_time) * 1000
                    )
                    
                    # Insert results into watchtower
                    if results and len(results) > 0:
                        for row in results:
                            self.bq.insert_anomaly_watchtower_result(
                                self.target_dataset,
                                {
                                    "execution_ts": row.get("execution_ts"),
                                    "run_id": run_id,
                                    "table_name": row.get("table_name"),
                                    "column_name": row.get("column_name"),
                                    "anomaly_name": row.get("anomaly_name"),
                                    "anomaly_category": anomaly.get("anomaly_category"),
                                    "previous_records_count": row.get("previous_records_count"),
                                    "latest_records_count": row.get("current_records_count"),
                                    "previous_value": row.get("previous_value"),
                                    "latest_value": row.get("current_value"),
                                    "absolute_diff": row.get("absolute_diff"),
                                    "change_pct": row.get("change_pct"),
                                    "execution_time_ms": execution_time_ms
                                }
                            )
                    
                except Exception as e:
                    print(f"❌ ANOMALY EXECUTION FAILED: {str(e)}")
                    continue
        
        except Exception as e:
            print(f"❌ ANOMALY EXECUTION ERROR: {str(e)}")


    def get_status(self, run_id):

        return self.bq.get_execution_status(
            self.target_dataset,
            run_id
        )

    def get_active_anomalies(self, table_name):
        """Fetch ONLY ONE latest record per column+anomaly combination - deduplicated on frontend too"""
        try:
            # For each unique column+anomaly pair, get the record with the MAX execution_ts
            query = f"""
            SELECT
                table_name,
                column_name,
                anomaly_name,
                anomaly_category,
                previous_records_count,
                latest_records_count,
                previous_value,
                latest_value,
                absolute_diff,
                change_pct,
                execution_ts,
                run_id
            FROM `{PROJECT_ID}.{self.target_dataset}.dq_anomaly_watchtower_results`
            WHERE table_name = '{table_name}'
            QUALIFY ROW_NUMBER() OVER (PARTITION BY column_name, anomaly_name ORDER BY execution_ts DESC) = 1
            ORDER BY column_name, anomaly_name
            """
            
            print(f"[get_active_anomalies] Fetching ONE latest record per column+anomaly for table: {table_name}")
            results = self.bq.run_query(query)
            results_list = [dict(row) for row in results]
            
            # Deduplicate on backend as safety measure
            seen = {}
            dedup_results = []
            for row in results_list:
                key = (row.get('column_name'), row.get('anomaly_name'))
                if key not in seen:
                    seen[key] = True
                    dedup_results.append(row)
                    print(f"[get_active_anomalies] Adding - {row.get('column_name')} + {row.get('anomaly_name')} = {row.get('change_pct')}% (ts: {row.get('execution_ts')})")
                else:
                    print(f"[get_active_anomalies] SKIPPING DUPLICATE - {row.get('column_name')} + {row.get('anomaly_name')}")
            
            print(f"[get_active_anomalies] Returning {len(dedup_results)} unique records (after dedup)")
            return dedup_results
        except Exception as e:
            print(f"[ERROR get_active_anomalies] {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def debug_get_all_anomalies(self):
        """Debug: Fetch ALL anomalies from dq_anomaly_watchtower_results (no filtering)"""
        try:
            query = f"""
            SELECT
                table_name,
                column_name,
                anomaly_name,
                anomaly_category,
                previous_records_count,
                latest_records_count,
                previous_value,
                latest_value,
                absolute_diff,
                change_pct,
                execution_ts,
                run_id
            FROM
                `{PROJECT_ID}.{self.target_dataset}.dq_anomaly_watchtower_results`
            ORDER BY
                execution_ts DESC
            LIMIT 100
            """
            
            print(f"[DEBUG] Fetching ALL anomalies (no filtering)...")
            results = self.bq.run_query(query)
            results_list = [dict(row) for row in results]
            
            print(f"[DEBUG] Total records found: {len(results_list)}")
            for i, row in enumerate(results_list[:5]):
                print(f"[DEBUG] Record {i}: {row}")
            
            return {
                "total_count": len(results_list),
                "data": results_list
            }
        except Exception as e:
            print(f"[ERROR debug_get_all_anomalies] {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "traceback": traceback.format_exc()}