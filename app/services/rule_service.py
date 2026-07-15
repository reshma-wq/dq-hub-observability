from datetime import datetime

from app.adapters.bq_adapter import BigQueryAdapter
from app.utils.config import PROJECT_ID, TARGET_DATASET


class RuleService:

    def __init__(self):
        self.bq = BigQueryAdapter(PROJECT_ID)

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

        errors = self.client.insert_rows_json(
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

        self.client.query(query).result()

    def complete_execution_run(self,dataset,run_id):
        query = f"""
                UPDATE `{self.project_id}.{dataset}.dq_execution_runs`
            SET
                status = 'SUCCESS',
                completed_at = CURRENT_TIMESTAMP()
                WHERE run_id = '{run_id}'
            """

        self.client.query(query).result()   

    def get_execution_status(self,dataset,run_id):
        query = f"""
            SELECT *
            FROM `{self.project_id}.{dataset}.dq_execution_runs`
            WHERE run_id = '{run_id}'
            """

        results = list(
            self.client.query(query).result()
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