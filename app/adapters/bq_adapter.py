from google.cloud import bigquery

class BigQueryAdapter:
    def __init__(self, project_id: str):
        """
        Initializes the BigQuery Client.
        """
        self.project_id = project_id
        self.client = bigquery.Client(project=project_id)

    def get_table_schema(self, dataset_name: str, table_name: str) -> str:
        """
        Fetches the structural schema of a target table to feed to Gemini.
        """
        table_ref = self.client.dataset(dataset_name).table(table_name)
        table = self.client.get_table(table_ref)
        
        schema_summary = []
        for field in table.schema:
            schema_summary.append(f"{field.name} ({field.field_type}) - Nullable: {field.is_nullable}")
            
        return "\n".join(schema_summary)

    def get_registered_rules(self, dataset_name: str, table_name: str) -> str:
        """
        Safely retrieves the current active YAML rule configuration string 
        for a given table using parameterized filtering.
        Returns None if no record exists at all.
        """
        query = f"""
            SELECT yaml_config 
            FROM `{self.project_id}.{dataset_name}.dq_rules_registry` 
            WHERE table_name = @table
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("table", "STRING", table_name)
            ]
        )
        
        query_job = self.client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        if results:
            return results[0].yaml_config
        return None  # Explicitly return None if no record exists yet

    def register_rule(self, dataset, rule):
        print("INSERTING RULE")
        print(rule)
        table_id = f"{self.project_id}.{dataset}.dq_rules_registry"
        rows = [rule]
        errors = self.client.insert_rows_json(
            table_id,
            rows
        )
        if errors:
            raise Exception(errors)
    
    def get_active_rules(self, dataset, table_name):
        query = f"""SELECT * FROM `{self.project_id}.{dataset}.dq_rules_registry` WHERE table_name = '{table_name}' AND active_flag = 'Y'"""

        return list(
            self.client.query(query).result()
        )

    def create_execution_run(self, dataset, run_record):

        table_id = f"{self.project_id}.{dataset}.dq_execution_runs"

        rows = [run_record]
        
        errors = self.client.insert_rows_json(
            table_id,
            rows
        )

        if errors:
            raise Exception(errors)

    def execute_dq_scan(self, generated_sql: str) -> list:
        """
        Executes the raw analytical compiled validation SQL block straight 
        inside the BigQuery computing engine layer.
        """
        query_job = self.client.query(generated_sql)
        return list(query_job.result())

    def insert_watchtower_result(self, dataset, result_record):
        table_id = f"{self.project_id}.{dataset}.dq_watchtower_results"

        rows = [result_record]

        errors = self.client.insert_rows_json(
            table_id,
            rows
        )

        if errors:
            raise Exception(errors)

    def execute_rule_sql(self, sql):

        query_job = self.client.query(sql)

        results = list(query_job.result())

        if not results:

            return {
                "total_records": 0,
                "failed_records": 0
            }

        row = results[0]

        return {
            "total_records": row["total_records"],
            "failed_records": row["failed_records"]
        }    

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

    def get_latest_results(self, dataset):
        query = f"""
            SELECT *
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (
                            PARTITION BY table_name, rule_name
                            ORDER BY execution_ts DESC
                    ) AS rn
                FROM `{self.project_id}.{dataset}.dq_watchtower_results`
            )
            WHERE rn = 1
            """

        results = list(self.client.query(query).result())

        response = []

        for row in results:

            response.append({
                "table_name": row["table_name"],
                "column_name": row["column_name"],
                "rule_name": row["rule_name"],
                "failed_records": row["failed_records"],
                "passed_records": row["passed_records"],
                "pass_percentage": row["pass_percentage"],
                "dq_status": row["dq_status"],
                "execution_ts": str(row["execution_ts"])
            })

        return response

    def get_dashboard_summary(self, dataset):
        query = f"""
            SELECT
                ROUND(AVG(pass_percentage), 2) AS system_health,
                COUNT(DISTINCT table_name) AS tables_monitored,
                COUNTIF(dq_status = 'FAIL') AS open_incidents,
                MAX(execution_ts) AS last_scan
            FROM (
                SELECT *,
                ROW_NUMBER() OVER (
                PARTITION BY table_name, rule_name
                ORDER BY execution_ts DESC
                ) AS rn
                FROM `{self.project_id}.{dataset}.dq_watchtower_results`
            )
            WHERE rn = 1
            """

        results = list(self.client.query(query).result())

        if not results:
            return {}

        row = results[0]

        return {
            "system_health": row["system_health"],
            "tables_monitored": row["tables_monitored"],
            "open_incidents": row["open_incidents"],
            "last_scan": str(row["last_scan"])
        }

    def save_results_to_bq(self, results, results_table_path: str, full_target_table_name: str):
        """
        Updates the Watchtower historical records dataset, ensuring historical 
        uniqueness through SCD (Slowly Changing Dimension) snapshot adjustments.
        """
        if not results:
            return
            
        demote_query = f"""
            UPDATE `{self.project_id}.{results_table_path}`
            SET is_latest = 'N'
            WHERE table_name = @full_table_name AND is_latest = 'Y'
        """
        demote_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("full_table_name", "STRING", full_target_table_name)
            ]
        )
        self.client.query(demote_query, job_config=demote_config).result()
        
        rows_to_insert = []
        for row in results:
            rows_to_insert.append({
                "execution_ts": str(row.execution_ts),
                "table_name": str(row.table_name),
                "column_name": str(row.column_name),
                "rule_name": str(row.rule_name),
                "failed_count": int(row.failed_count),
                "is_latest": "Y"
            })
            
        table_ref = self.client.get_table(f"`{self.project_id}.{results_table_path}`".replace("`", ""))
        errors = self.client.insert_rows_json(table_ref, rows_to_insert)
        
        if errors:
            raise Exception(f"Failed to stream audit snapshots into Watchtower log: {errors}")