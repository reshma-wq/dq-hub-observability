from google.cloud import bigquery
import re

# from app.utils.config import TARGET_DATASET
from app.utils.config import (
    TARGET_DATASET,
    DQ_HUB_DATASET
)

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

    def run_query(self, query: str):
        """
        Execute a BigQuery query and return results
        """
        try:
            results = self.client.query(query).result()
            return list(results)
        except Exception as e:
            print(f"[ERROR run_query] {str(e)}")
            raise

    # def get_registered_rules(self,dataset_name: str,table_name: str):
    #     query = f"""
    #         SELECT *
    #         FROM
    #         `{self.project_id}.{dataset_name}.dq_rules_registry`
    #         WHERE
    #         table_name = @table
    #     """

    #     job_config = bigquery.QueryJobConfig(
    #         query_parameters=[
    #             bigquery.ScalarQueryParameter(
    #                 "table",
    #                 "STRING",
    #                 table_name
    #             )
    #         ]
    #     )

    #     results = self.client.query(
    #         query,
    #         job_config=job_config
    #     ).result()

    #     return list(results)

    def get_registered_rules(
        self,
        dataset_name: str,
        table_name: str = None):

        if table_name:

            query = f"""
                SELECT *
                FROM `{self.project_id}.{dataset_name}.dq_rules_registry`
                WHERE table_name = @table
                AND active_flag = 'Y'
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter(
                        "table",
                        "STRING",
                        table_name
                    )
                ]
            )

            results = self.client.query(
                query,
                job_config=job_config
            ).result()

        else:

            query = f"""
                SELECT *
                FROM `{self.project_id}.{dataset_name}.dq_rules_registry`
                WHERE active_flag = 'Y'
            """

            results = self.client.query(
                query
            ).result()

        return list(results)

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
    
    def register_anomaly(self, dataset, anomaly):
        """Register an anomaly in dq_anomaly_registry table"""
        print("INSERTING ANOMALY")
        print(anomaly)
        table_id = f"{self.project_id}.{dataset}.dq_anomaly_registry"
        rows = [anomaly]
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

    def qualify_table_references(self, sql):

        pattern = r'FROM\\s+([a-zA-Z_][a-zA-Z0-9_]*)'

        matches = re.findall(
            pattern,
            sql,
            flags=re.IGNORECASE
        )

        for table_name in matches:

            if "." not in table_name and "`" not in table_name:

                qualified_table = (
                    f"`{self.project_id}."
                    f"{TARGET_DATASET}."
                    f"{table_name}`"
                )

                sql = re.sub(

                    rf'FROM\\s+{table_name}\\b',

                    f"FROM {qualified_table}",

                    sql,

                    flags=re.IGNORECASE
                )

        return sql

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

    def insert_watchtower_result(self,dataset,result_record):

        table_id = (
            f"{self.project_id}."
            f"{dataset}."
            f"dq_watchtower_results"
        )

        rows = [result_record]

        print("INSERTING:")
        print(result_record)

        errors = self.client.insert_rows_json(
            table_id,
            rows
        )

        print("BQ ERRORS:")
        print(errors)

        if errors:
            raise Exception(errors)

        print("INSERT SUCCESS")

    def get_registered_anomalies(self, dataset, table_name):
        """Fetch all active registered anomalies for a table"""
        query = f"""
        SELECT 
          table_name,
          column_name,
          anomaly_name,
          anomaly_category,
          compiled_sql,
          active_flag
        FROM `{self.project_id}.{dataset}.dq_anomaly_registry`
        WHERE table_name = '{table_name}'
        AND active_flag = 'Y'
        """
        
        results = self.client.query(query).result()
        anomalies = []
        
        for row in results:
            anomalies.append({
                "table_name": row.table_name,
                "column_name": row.column_name,
                "anomaly_name": row.anomaly_name,
                "anomaly_category": row.anomaly_category,
                "compiled_sql": row.compiled_sql,
                "active_flag": row.active_flag
            })
        
        return anomalies

    def execute_anomaly_sql(self, compiled_sql):
        """Execute anomaly compiled_sql and return results"""
        try:
            from decimal import Decimal
            
            results = self.client.query(compiled_sql).result()
            rows = []
            
            def convert_to_json_serializable(value):
                """Convert BigQuery types to JSON-serializable Python types"""
                if value is None:
                    return None
                if isinstance(value, Decimal):
                    # Convert Decimal to float (from COUNT, SUM, etc.)
                    return float(value)
                if isinstance(value, (int, str, bool)):
                    return value
                if isinstance(value, float):
                    return value
                if hasattr(value, 'isoformat'):
                    # datetime, date, timestamp types
                    return value.isoformat()
                # Fallback: convert to string
                return str(value)
            
            for row in results:
                rows.append({
                    "execution_ts": convert_to_json_serializable(row.execution_ts),
                    "table_name": convert_to_json_serializable(row.table_name),
                    "column_name": convert_to_json_serializable(row.column_name),
                    "anomaly_name": convert_to_json_serializable(row.anomaly_name),
                    "previous_records_count": convert_to_json_serializable(getattr(row, "previous_records_count", None)),
                    "current_records_count": convert_to_json_serializable(getattr(row, "current_records_count", None)),
                    "previous_value": convert_to_json_serializable(row.previous_value),
                    "current_value": convert_to_json_serializable(row.current_value),
                    "absolute_diff": convert_to_json_serializable(row.absolute_diff),
                    "change_pct": convert_to_json_serializable(row.change_pct)
                })
            
            return rows
        except Exception as e:
            print(f"Error executing anomaly SQL: {str(e)}")
            raise

    def insert_anomaly_watchtower_result(self, dataset, result_record):
        """Insert anomaly execution result into watchtower table"""
        table_id = (
            f"{self.project_id}."
            f"{dataset}."
            f"dq_anomaly_watchtower_results"
        )

        rows = [result_record]

        print("INSERTING ANOMALY RESULT:")
        print(result_record)

        errors = self.client.insert_rows_json(
            table_id,
            rows
        )

        if errors:
            raise Exception(errors)

        print("ANOMALY INSERT SUCCESS")

    def execute_rule_sql(self, sql):

        sql = self.qualify_table_references(
            sql
        )

        print("FINAL SQL")
        print(sql)

        query_job = self.client.query(
            sql
        )

        results = list(
            query_job.result()
        )

        if not results:

            return {
                "total_records": 0,
                "failed_records": 0
            }

        row = results[0]

        return {
            "total_records":
                row["total_records"],

            "failed_records":
                row["failed_records"]
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

        results = list(
            self.client.query(query).result()
        )

        tables = {}

        for index, row in enumerate(results):

            table_name = row["table_name"]

            if table_name not in tables:

                tables[table_name] = {
                    "table_name": table_name,
                    "rules": [],
                    "last_scan": str(row["execution_ts"]),
                    "rows":
                        (row["passed_records"] or 0) +(row["failed_records"] or 0),
                    "columns":
                        self.get_table_columns(dataset,table_name)
                }

            tables[table_name]["rules"].append({

                "id":
                    f"rule_{index}",

                "column":
                    row["column_name"],

                "name":
                    row["rule_name"],

                "description":
                    row["rule_name"],

                "status":
                    "failing"
                    if row["dq_status"] == "FAIL"
                    else "passing",

                "violations":
                    row["failed_records"] or 0
            })

        return list(
            tables.values()
        )

    def get_table_columns(self,dataset,table_name):

        table_ref = (
            f"{self.project_id}."
            f"{dataset}."
            f"{table_name}"
        )

        table = self.client.get_table(
            table_ref
        )

        return [
            field.name
            for field in table.schema
        ]

    def get_dashboard_summary(self,dataset):

            latest_results = self.get_latest_results(
                dataset
            )
            all_tables =self.get_dataset_tables(dataset)

            open_incidents = 0

            total_rules = 0

            passing_rules = 0

            # Get last execution timestamp from dq_execution_runs table
            try:
                query = f"""
                    SELECT CAST(MAX(completed_at) as STRING) as latest_completed_at
                    FROM `{self.project_id}.{dataset}.dq_execution_runs`
                    WHERE status = 'SUCCESS' AND completed_at IS NOT NULL
                """
                query_job = self.client.query(query)
                results = list(query_job.result())
                latest_scan = results[0]["latest_completed_at"] if results and results[0]["latest_completed_at"] else None
            except Exception as e:
                latest_scan = None

            for table in latest_results:

                rules = table.get(
                    "rules",
                    []
                )

                total_rules += len(
                    rules
                )

                for rule in rules:

                    if (
                        rule["status"]
                        == "failing"
                    ):

                        open_incidents += 1

                    else:

                        passing_rules += 1

                if not table.get(
                    "columns"
                ):

                    table["columns"] = (
                        self.get_table_columns(
                            dataset,
                            table["table_name"]
                        )
                    )

            system_health = (
                round(
                    (
                        passing_rules /
                        total_rules
                    ) * 100
                )
                if total_rules > 0
                else 0
            )

            return {

                "system_health":
                    system_health,

                "tables_monitored":
                    len(
                        latest_results
                    ),

                "open_incidents":
                    open_incidents,

                "last_scan":
                    latest_scan,

                "tables": [

                    next(

                        (
                            t for t in latest_results
                            if t["table_name"] == table_name
                        ),

                        {

                            "table_name":
                                table_name,

                            "rules":
                                [],

                            "last_scan":
                                None,

                            "rows":
                                0,

                            "columns":
                                []
                        }
                    )

                    for table_name in all_tables
                ]
            }

    def get_table_details(self,dataset,table_name):
        query = f"""
        SELECT
            rule_name,
            column_name,
            dq_status,
            failed_records
        FROM
            `{self.project_id}.{dataset}.dq_watchtower_results`
        WHERE
            table_name = '{table_name}'
        QUALIFY ROW_NUMBER() OVER(
            PARTITION BY rule_name
            ORDER BY execution_ts DESC
        ) = 1
        """

        results = list(
            self.client.query(query).result()
        )

        rules = []

        for index, row in enumerate(results):

            rules.append({

                "id":
                    f"rule_{index}",

                "column":
                    row.column_name,

                "name":
                    row.rule_name,

                "description":
                    row.rule_name,

                "status":
                    "failing"
                    if row.dq_status == "FAIL"
                    else "passing",

                "violations":
                    row.failed_records or 0
            })

        return {

            "table_name":
                table_name,

            "total_rules":
                len(rules),

            "rules":
                rules
        }


    # def get_dataset_tables(self,dataset):
    #     query = f"""
    #         SELECT
    #             table_name
    #         FROM
    #             `dq-universal-framework.{dataset}.INFORMATION_SCHEMA.TABLES`
    #         """

    #     results = self.client.query(
    #         query
    #     ).result()

    #     tables = []

    #     for row in results:

    #         tables.append(
    #             row["table_name"]
    #         )

    #     return tables

    def get_dataset_tables(self, dataset):

        query = f"""
            SELECT
                table_name
            FROM
                `{self.project_id}.{dataset}.INFORMATION_SCHEMA.TABLES`
            """

        results = self.client.query(
            query
        ).result()

        tables = []

        for row in results:

            table_name = row["table_name"]

            if table_name.startswith(
                "dq_"
            ):

                continue

            tables.append(
                table_name
            )

        return tables

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

    
    def insert_knowledge_record(
        self,
        record
    ):

        table_id = (
            f"{self.project_id}."
            f"{DQ_HUB_DATASET}."
            f"enterprise_knowledge_hub"
        )

        print("TABLE ID")
        print(table_id)

        print("RECORD")
        print(record)

        errors = self.client.insert_rows_json(
            table_id,
            [record]
        )

        print("INSERT ERRORS")
        print(errors)

        if errors:
            raise Exception(errors)

        print("INSERT SUCCESS")


    def get_knowledge_context(
            self,
            table_name
        ):

            query = f"""
                SELECT *
                FROM
                `{self.project_id}.{DQ_HUB_DATASET}.enterprise_knowledge_hub`
                WHERE
                    table_name = @table_name
                    AND active_flag = TRUE
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter(
                        "table_name",
                        "STRING",
                        table_name
                    )
                ]
            )

            results = list(
                self.client.query(
                    query,
                    job_config=job_config
                ).result()
            )

            if not results:
                return None

            return dict(
                results[0].items()
            )
    

    def get_column_samples(
        self,
        dataset_name,
        table_name
    ):

        samples = {}

        table = self.client.get_table(
            f"{self.project_id}.{dataset_name}.{table_name}"
        )

        for field in table.schema:

            if field.field_type != "STRING":
                continue

            query = f"""
            SELECT DISTINCT
                `{field.name}`
            FROM
                `{self.project_id}.{dataset_name}.{table_name}`
            WHERE
                `{field.name}` IS NOT NULL
            LIMIT 10
            """

            try:

                results = self.client.query(
                    query
                ).result()

                values = [
                    str(row[field.name])
                    for row in results
                ]

                samples[field.name] = values

            except Exception as ex:

                print(
                    f"Sample extraction failed for {field.name}"
                )

                print(ex)

        return samples

    def get_numeric_profiles(
            self,
            dataset_name,
            table_name
        ):

            profiles = {}

            table = self.client.get_table(
                f"{self.project_id}.{dataset_name}.{table_name}"
            )

            numeric_types = [
                "INTEGER",
                "INT64",
                "NUMERIC",
                "FLOAT",
                "FLOAT64"
            ]

            for field in table.schema:

                if field.field_type not in numeric_types:
                    continue

                query = f"""
                SELECT
                    MIN({field.name}) AS min_value,
                    MAX({field.name}) AS max_value,
                    AVG({field.name}) AS avg_value
                FROM
                    `{self.project_id}.{dataset_name}.{table_name}`
                """

                try:

                    result = list(
                        self.client.query(
                            query
                        ).result()
                    )[0]

                    profiles[field.name] = {

                        "min":
                            float(
                                result["min_value"]
                            )
                            if result["min_value"] is not None
                            else None,

                        "max":
                            float(
                                result["max_value"]
                            )
                            if result["max_value"] is not None
                            else None,

                        "avg":
                            float(
                                result["avg_value"]
                            )
                            if result["avg_value"] is not None
                            else None
                    }

                except Exception as ex:

                    print(
                        f"Numeric profiling failed for {field.name}"
                    )

                    print(ex)

            return profiles

    def get_existing_knowledge_hub_tables(
            self
        ):

            query = f"""
            SELECT DISTINCT
                table_name
            FROM
                `{self.project_id}.{DQ_HUB_DATASET}.enterprise_knowledge_hub`
            WHERE
                active_flag = TRUE
            """

            results = self.client.query(
                query
            ).result()

            return {
                row["table_name"]
                for row in results
            }

            