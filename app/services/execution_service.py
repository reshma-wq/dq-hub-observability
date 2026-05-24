import time
import uuid
from datetime import datetime

from app.adapters.bq_adapter import BigQueryAdapter
from app.utils.config import PROJECT_ID, TARGET_DATASET


class ExecutionService:

    def __init__(self):

        self.bq = BigQueryAdapter(PROJECT_ID)
        TARGET_DATASET = "thd_bronze"

    def run_checks(self, table_name):

        run_id = str(uuid.uuid4())

        #rules = self.bq.get_registered_rules(dataset,table_name)
        rules = self.bq.get_registered_rules(TARGET_DATASET,table_name)
        print("RULES FETCHED")
        print(rules)
        print(len(rules))

        total_rules = len(rules)

        self.bq.create_execution_run(
            TARGET_DATASET,
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

        completed = 0

        print("ENTERING LOOP")
        for rule in rules:
            print("RUNNING RULE")
            print(rule)

            start_time = time.time()

            result = self.bq.execute_rule_sql(
                rule.compiled_sql
            )

            execution_time_ms = int(
                (time.time() - start_time) * 1000
            )

            total_records = result["total_records"]

            failed_records = result["failed_records"]

            passed_records = (
                total_records -
                failed_records
            )

            pass_percentage = (
                passed_records /
                total_records
            ) * 100 if total_records > 0 else 0

            print("INSERT FUNCTION CALLING")
            self.bq.insert_watchtower_result(
                TARGET_DATASET,
                {
                    "execution_ts":
                        datetime.utcnow().isoformat(),

                    "run_id":
                        run_id,

                    "table_name":
                        table_name,

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
                        "FAIL" if failed_records > 0 else "PASS"
                }
            )

            completed += 1

            # self.bq.update_execution_progress(
            #     TARGET_DATASET,
            #     run_id,
            #     completed
            # )

        # self.bq.complete_execution_run(
        #     TARGET_DATASET,
        #     run_id
        # )

        return {
            "run_id": run_id,
            "status": "started"
        }

    def get_status(self, run_id):

        return self.bq.get_execution_status(
            TARGET_DATASET,
            run_id
        )