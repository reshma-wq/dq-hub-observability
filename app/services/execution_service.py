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
            # Handle "Run all checks" - if table_name is None, get all tables
            if table_name is None:
                print("[run_checks] Running checks for ALL tables...")
                # Get all tables from the dataset
                all_tables = self.bq.get_dataset_tables(self.target_dataset)
                print(f"[run_checks] Found {len(all_tables)} tables: {all_tables}")
                
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

            self.bq.create_execution_run(
                self.target_dataset,
                {
                    "run_id": run_id,
                    "table_name": table_name,
                    "total_rules": total_rules,
                    "completed_rules": 0,
                    "status": "RUNNING",
                    "started_at": datetime.utcnow().isoformat(),
                    "completed_at": None
                }
            )

            failed_rules = 0
            completed = 0

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

            print("EXECUTION COMPLETED")

            return {
                "run_id": run_id,
                "status": "started",
                "total_rules": total_rules,
                "completed_rules": completed,
                "failed_rules": failed_rules
            }

    def get_status(self, run_id):

        return self.bq.get_execution_status(
            self.target_dataset,
            run_id
        )