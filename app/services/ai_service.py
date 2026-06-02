import json
import vertexai

from vertexai.generative_models import GenerativeModel

from app.adapters.bq_adapter import BigQueryAdapter
from app.utils.config import (
    PROJECT_ID,
    LOCATION,
    TARGET_DATASET
)

# # Initialize Vertex AI
# vertexai.init(
#     project=PROJECT_ID,
#     location=LOCATION
# )

# # Gemini model
# model = GenerativeModel("gemini-2.5-flash")


class AIService:

    def __init__(self):

        self.bq = BigQueryAdapter(
            PROJECT_ID
        )

        vertexai.init(
            project=PROJECT_ID,
            location=LOCATION
        )

        self.model = GenerativeModel(
            "gemini-2.5-flash"
        )

    def generate_rules(self, table_name):

        # Fetch schema dynamically from BigQuery
        schema = self.bq.get_table_schema(
            TARGET_DATASET,
            table_name
        )
        full_table_name = (f"{PROJECT_ID}."f"{TARGET_DATASET}."f"{table_name}")

        # Enterprise-grade AI prompt
        prompt = f"""
You are an expert Enterprise Data Quality Architect.

Analyze the following BigQuery table schema carefully.

BIGQUERY TABLE:
`{full_table_name}`

SCHEMA:
{schema}

Your responsibility is to generate ALL POSSIBLE enterprise-grade Data Quality rules applicable for this table.

You must intelligently infer rules based on:
- column names
- data types
- nullable fields
- timestamps
- ids
- measures
- dimensions
- business semantics
- naming conventions

Generate EVERY meaningful rule possible for EVERY column.

Possible rule categories include:
- not null validation
- uniqueness validation
- duplicate detection
- regex validation
- completeness checks
- allowed values checks
- range checks
- positive value checks
- freshness checks
- timestamp validation
- future date validation
- empty string checks
- referential integrity checks
- standardization checks
- consistency checks
- datatype validations
- business rule validations
- threshold validations

CRITICAL BIGQUERY SQL RULES:

- ALWAYS use fully-qualified BigQuery table names
- NEVER use unqualified table names
- ALWAYS reference tables using:
  `project.dataset.table`

Wrong example:
FROM table_name

Correct example:
FROM `{full_table_name}`

This rule applies to:
- main queries
- subqueries
- nested SELECT statements
- EXISTS clauses
- JOINs
- CTEs
- all SQL references

BIGQUERY EXECUTION CONSTRAINTS:

You are generating SQL specifically for Google BigQuery.

STRICTLY FOLLOW THESE RULES:

1. NEVER generate correlated subqueries

2. NEVER generate EXISTS clauses referencing outer query columns

3. NEVER generate recursive CTEs

4. NEVER generate CROSS JOIN unless explicitly required

5. NEVER generate cartesian products

6. NEVER generate nested queries referencing parent aliases

7. ALWAYS generate BigQuery-compatible SQL only

8. Prefer:
   - COUNT(DISTINCT)
   - GROUP BY
   - QUALIFY
   - SAFE_CAST
   - aggregation-based validations

9. For uniqueness validations:
   ALWAYS use:
   COUNT(*) != COUNT(DISTINCT column_name)

10. DO NOT use EXISTS-based uniqueness checks

11. All SQL must be optimized for large-scale distributed execution

12. Generated SQL must minimize full table scans where possible

13. SQL must be production-safe and execution-safe for BigQuery


GOOD EXAMPLES:

UNIQUENESS CHECK:

sql_condition:
COUNT(*) != COUNT(DISTINCT customer_id)

BAD EXAMPLE:
EXISTS (
  SELECT 1
  FROM table t2
  WHERE t2.id = table.id
)

NOT NULL CHECK:

sql_condition:
email IS NULL

POSITIVE VALUE CHECK:

sql_condition:
amount < 0

FUTURE DATE CHECK:

sql_condition:
created_at > CURRENT_TIMESTAMP()


IMPORTANT:
- Generate ALL applicable rules
- Do NOT limit number of rules
- Do NOT skip columns
- Generate multiple rules per column if applicable
- sql_condition must ONLY contain SQL boolean condition
- sql_condition may contain nested subqueries if needed
- all table references inside sql_condition must use fully-qualified BigQuery table names
- Do NOT generate full SELECT query
- rule_name must be enterprise-friendly
- description must explain business intent
- Avoid duplicate rules
- Avoid generic useless rules

Return ONLY valid JSON array.

Expected format:
[
  {{
    "rule_name": "",
    "column_name": "",
    "description": "",
    "sql_condition": ""
  }}
]

Do NOT return markdown.
Do NOT explain anything.
Return raw JSON only.
"""

        # Generate AI response
        response = self.model.generate_content(
            prompt
        )

        raw_text = response.text.strip()

        # Clean markdown if Gemini returns it

        raw_text = raw_text.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        )

        # Convert to Python JSON

        try:

            rules = json.loads(
                raw_text
            )

        except Exception:

            print(
                "RAW GEMINI RESPONSE"
            )

            print(raw_text)

            raise

        # Validate generated SQL

        for rule in rules:

            sql_condition = rule.get(
                "sql_condition",
                ""
            )

            if (
                "FROM " in sql_condition.upper()
                and full_table_name not in sql_condition
            ):

                raise Exception(
                    f"Invalid SQL generated for rule: "
                    f"{rule.get('rule_name')}"
                )

        return rules