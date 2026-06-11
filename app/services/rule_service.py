from datetime import datetime

from app.adapters.bq_adapter import BigQueryAdapter
from app.utils.config import PROJECT_ID, TARGET_DATASET


# Template rule SQL patterns
# Maps rule_type to WHERE clause condition
TEMPLATE_SQL_PATTERNS = {
    'not_null': '{column} IS NULL',
    'unique': 'COUNT(*) != COUNT(DISTINCT {column})',
    'in_values': '{column} NOT IN ({placeholder})',
    'between': '{column} NOT BETWEEN {min_val} AND {max_val}',
    'positive': '{column} <= 0 OR {column} IS NULL',
    'pattern': 'NOT REGEXP_CONTAINS({column}, r\'{placeholder}\')',
}

# Placeholder configuration for template rules
# Defines which rules need placeholders and how many
TEMPLATE_PLACEHOLDERS = {
    'not_null': [],
    'unique': [],
    'positive': [],
    'in_values': [
        {
            'key': 'placeholder',
            'label': 'Allowed Values',
            'description': 'Comma-separated list of allowed values',
            'example': "'value1', 'value2', 'value3'"
        }
    ],
    'between': [
        {
            'key': 'min_val',
            'label': 'Minimum Value',
            'description': 'Lower bound for range check',
            'example': '0'
        },
        {
            'key': 'max_val',
            'label': 'Maximum Value',
            'description': 'Upper bound for range check',
            'example': '100'
        }
    ],
    'pattern': [
        {
            'key': 'placeholder',
            'label': 'Regex Pattern',
            'description': 'Regular expression pattern to match',
            'example': '^[A-Z][a-z]+$'
        }
    ],
}


class RuleService:

    def __init__(self):
        self.bq = BigQueryAdapter(PROJECT_ID)
        self.project_id = PROJECT_ID
        self.target_dataset = TARGET_DATASET

    def get_rules(self, dataset, table_name):
        """
        Fetches all registered rules for a table from BigQuery.
        
        Args:
            dataset (str): Dataset name
            table_name (str): Table name
            
        Returns:
            list: List of rule records
        """
        try:
            return self.bq.get_registered_rules(dataset, table_name)
        except Exception as e:
            print(f"Error fetching rules: {str(e)}")
            return []

    def get_template_info(self, rule_type):
        """
        Gets placeholder information for a template rule type.
        
        Args:
            rule_type (str): Template rule type
            
        Returns:
            dict: {rule_type, placeholders, sql_pattern}
        """
        if rule_type not in TEMPLATE_SQL_PATTERNS:
            return None
        
        return {
            "rule_type": rule_type,
            "sql_pattern": TEMPLATE_SQL_PATTERNS[rule_type],
            "placeholders": TEMPLATE_PLACEHOLDERS.get(rule_type, [])
        }

    def compile_sql(self, table_name, rule):

        return f"""
        SELECT
            CURRENT_TIMESTAMP() AS execution_ts,
            '{table_name}' AS table_name,
            '{rule.column_name}' AS column_name,
            '{rule.rule_name}' AS rule_name,
            COUNT(*) AS total_records,
            SUM(
                CASE
                    WHEN {rule.sql_condition}
                    THEN 1
                    ELSE 0
                END
            ) AS failed_records
        FROM `{self.project_id}.{self.target_dataset}.{table_name}`
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

    def create_template_rule(self, table_name, column_name, rule_type, description, placeholder_values=None):
        """
        Creates a template-based rule and saves it to BigQuery registry.
        
        Args:
            table_name (str): Target table name
            column_name (str): Column to validate
            rule_type (str): Type of template rule (not_null, unique, positive, etc.)
            description (str): Human-readable description of the rule
            placeholder_values (dict): Dictionary of placeholder values {key: value}
            
        Returns:
            dict: {status, rule_id, message}
        """
        try:
            # Validate rule type exists
            if rule_type not in TEMPLATE_SQL_PATTERNS:
                return {
                    "status": "error",
                    "message": f"Invalid rule type: {rule_type}"
                }
            
            # Generate rule name from description
            rule_name = description.strip().lower().replace(' ', '_').replace('-', '_')[:50] or f"{column_name}_{rule_type}"
            
            # Get the SQL pattern for this rule type
            sql_pattern = TEMPLATE_SQL_PATTERNS[rule_type]
            
            # Build the sql_condition (the WHERE clause part)
            # Use placeholder values if provided
            if placeholder_values is None:
                placeholder_values = {}
            
            format_kwargs = {
                'column': column_name,
                'placeholder': placeholder_values.get('placeholder', '<value>'),
                'min_val': placeholder_values.get('min_val', '<min>'),
                'max_val': placeholder_values.get('max_val', '<max>')
            }
            
            try:
                sql_condition = sql_pattern.format(**format_kwargs)
            except KeyError:
                # If pattern doesn't have placeholders, use as-is with just column substitution
                sql_condition = sql_pattern.format(column=column_name)
            
            # Create a mock rule object for compile_sql
            class MockRule:
                pass
            
            mock_rule = MockRule()
            mock_rule.column_name = column_name
            mock_rule.rule_name = rule_name
            mock_rule.sql_condition = sql_condition
            
            # Compile full SQL for execution
            compiled_sql = self.compile_sql(table_name, mock_rule)
            
            # Create registry record with correct data types
            # created_at is datetime object - BigQuery will auto-convert to TIMESTAMP
            created_timestamp = datetime.utcnow()
            
            registry_record = {
                "table_name": table_name,
                "column_name": column_name,
                "rule_name": rule_name,
                "description": description,
                "sql_condition": sql_condition,
                "compiled_sql": compiled_sql,
                "created_at": created_timestamp,
                "active_flag": "Y"
            }
            
            # Save to BigQuery
            self.bq.register_rule(self.target_dataset, registry_record)
            
            return {
                "status": "success",
                "rule_id": f"{table_name}_{column_name}_{rule_type}_{int(datetime.utcnow().timestamp())}",
                "message": f"Template rule '{rule_name}' created successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create rule: {str(e)}"
            }

    def create_custom_sql_rule(self, table_name, column_name, rule_name, description, sql_condition):
        """
        Creates a custom SQL rule and saves it to BigQuery registry.
        Inverts the user's PASSING condition to a FAILING condition.
        
        Args:
            table_name (str): Target table name
            column_name (str): Column associated with rule
            rule_name (str): Rule name (user-provided)
            description (str): Human-readable description
            sql_condition (str): SQL condition for PASSING records (user writes this)
            
        Returns:
            dict: {status, rule_id, message}
            
        Example:
            User input: "salary IS NOT NULL"
            Backend stores: "NOT (salary IS NOT NULL)"
            This way, the condition evaluates to TRUE for FAILING records
        """
        try:
            # Invert the SQL condition: wrap in NOT(...)
            # This converts user's PASSING condition to FAILING condition
            inverted_condition = f"NOT ({sql_condition})"
            
            # Create a mock rule object for compile_sql
            class MockRule:
                pass
            
            mock_rule = MockRule()
            mock_rule.column_name = column_name
            mock_rule.rule_name = rule_name
            mock_rule.sql_condition = inverted_condition
            
            # Compile full SQL for execution
            compiled_sql = self.compile_sql(table_name, mock_rule)
            
            # Create registry record
            registry_record = {
                "table_name": table_name,
                "column_name": column_name,
                "rule_name": rule_name,
                "description": description,
                "sql_condition": inverted_condition,  # Store inverted condition
                "compiled_sql": compiled_sql,
                "created_at": datetime.utcnow(),
                "active_flag": "Y"
            }
            
            # Save to BigQuery
            self.bq.register_rule(self.target_dataset, registry_record)
            
            return {
                "status": "success",
                "rule_id": f"{table_name}_{column_name}_custom_{int(datetime.utcnow().timestamp())}",
                "message": f"Custom SQL rule '{rule_name}' created successfully"
            }
            
        except Exception as e:
            print(f"Error creating custom SQL rule: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to create rule: {str(e)}"
            }

    def register_rules(self, table_name, rules):
        """
        Registers multiple rules (from AI suggestions) to BigQuery.
        
        Args:
            table_name (str): Target table name
            rules (List[Rule]): List of Rule objects from RuleRegistrationRequest
            
        Returns:
            dict: {status, rules_registered, failed_rules}
        """
        try:
            print("REGISTERING RULES")
            print(f"Table: {table_name}, Number of rules: {len(rules)}")

            registered_count = 0
            failed_rules = []

            for rule in rules:
                try:
                    print(f"Processing rule: {rule.rule_name}")

                    compiled_sql = self.compile_sql(table_name, rule)

                    registry_record = {
                        "table_name": table_name,
                        "column_name": rule.column_name,
                        "rule_name": rule.rule_name,
                        "description": rule.description,
                        "sql_condition": rule.sql_condition,
                        "compiled_sql": compiled_sql,
                        "created_at": datetime.utcnow(),
                        "active_flag": "Y"
                    }

                    self.bq.register_rule(
                        self.target_dataset,
                        registry_record
                    )
                    print(f"Rule registered: {rule.rule_name}")
                    registered_count += 1
                    
                except Exception as rule_error:
                    print(f"Failed to register rule {rule.rule_name}: {str(rule_error)}")
                    failed_rules.append({
                        "rule_name": rule.rule_name,
                        "error": str(rule_error)
                    })

            if registered_count == 0:
                return {
                    "status": "error",
                    "message": f"Failed to register any rules: {failed_rules}",
                    "failed_rules": failed_rules
                }
            
            return {
                "status": "success",
                "rules_registered": registered_count,
                "failed_rules": failed_rules if failed_rules else []
            }
            
        except Exception as e:
            print(f"Error registering rules: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to register rules: {str(e)}"
            }