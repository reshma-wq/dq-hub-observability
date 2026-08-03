import json
from google import genai
from datetime import datetime
import uuid

from app.adapters.bq_adapter import BigQueryAdapter
from app.utils.config import (
    PROJECT_ID,
    LOCATION,
    TARGET_DATASET,
    MODEL_NAME
)
from google.cloud import bigquery

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

        self.client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global"
        )

        print(
            f"Using model: {MODEL_NAME}"
        )

    def _get_column_type(self, table_name, column_name):
        """Get the original data type of a column from BigQuery schema"""
        try:
            bq_client = bigquery.Client(project=PROJECT_ID)
            table = bq_client.get_table(f"{PROJECT_ID}.{TARGET_DATASET}.{table_name}")
            
            for field in table.schema:
                if field.name == column_name:
                    # Map BigQuery types to CAST types
                    field_type = field.field_type.upper()
                    if 'DATE' in field_type:
                        return 'DATE'
                    elif 'TIMESTAMP' in field_type:
                        return 'TIMESTAMP'
                    elif 'STRING' in field_type:
                        return 'STRING'
                    elif 'INT' in field_type:
                        return 'INT64'
                    elif 'FLOAT' in field_type or 'NUMERIC' in field_type:
                        return 'FLOAT64'
                    return field_type
            
            return 'STRING'  # Default fallback
        except Exception as e:
            print(f"Error getting column type for {table_name}.{column_name}: {str(e)}")
            return 'STRING'

    def generate_rules(self, table_name):

        # Fetch schema dynamically from BigQuery
        schema = self.bq.get_table_schema(
            TARGET_DATASET,
            table_name
        )
        knowledge_context = (
            self.bq.get_knowledge_context(
                table_name
            )
        )

        knowledge_json = json.dumps(
            knowledge_context,
            indent=2,
            default=str
        )

        print("KNOWLEDGE CONTEXT")
        print(knowledge_json)
        full_table_name = (f"{PROJECT_ID}."f"{TARGET_DATASET}."f"{table_name}")

        # Enterprise-grade AI prompt
        prompt = f"""
You are a world-class Enterprise Data Governance, Data Quality, Metadata Management, Data Stewardship, and Data Product Management Expert.

You act as:

- Chief Data Officer (CDO)
- Enterprise Data Governance Council
- Enterprise Data Steward
- Data Quality Architect
- Metadata Management Expert
- Business Domain Expert
- Data Product Owner

Your responsibility is to generate enterprise-grade Data Quality controls that ensure:

- Trusted Data
- Governed Data
- Business-Aligned Data
- AI-Ready Data
- Regulatory-Compliant Data
- High-Quality Data Products

==================================================
BIGQUERY TABLE
==================================================

{full_table_name}

==================================================
SCHEMA
==================================================

{schema}

==================================================
ENTERPRISE KNOWLEDGE HUB
==================================================

{knowledge_json}

==================================================

KNOWLEDGE HUB USAGE
==================================================

The Enterprise Knowledge Hub is the primary source of truth.

Use:

- Business definitions
- Business purpose
- Business value
- Business impact
- Consumer groups
- Criticality
- Column business definitions
- Data quality expectations
- Sample values
- Numeric profiles

to understand:

- What the data means
- Why it exists
- Who consumes it
- What business decisions depend on it
- What governance controls should exist

Prefer Knowledge Hub context over assumptions.

==================================================
RULE PRIORITY HIERARCHY
==================================================

Generate rules using this priority order.

PRIORITY 1 — GOVERNANCE RULES

Governance rules are mandatory.

These rules must ALWAYS be generated.

Examples:

customer_id IS NULL

transaction_id IS NULL

product_id IS NULL

campaign_id IS NULL

quantity < 0

sale_price < 0

amount < 0

budget < 0

spend < 0

annual_income < 0

created_ts > CURRENT_TIMESTAMP()

updated_ts > CURRENT_TIMESTAMP()

start_date > end_date

Governance rules must NEVER be replaced by profiling rules.

--------------------------------------------------

PRIORITY 2 — BUSINESS RULES

MANDATORY: Generate business rules for EVERY logical relationship.

When these column patterns exist, ALWAYS generate these business rules:

SPEND + BUDGET Pattern:
If columns contain: spend, budget, cost, amount
→ MUST generate: spend > budget, spend > 0, budget > 0

FUNNEL Pattern:
If columns contain: impressions, clicks, conversions
→ MUST generate: clicks > impressions, conversions > clicks, impressions > 0, clicks >= 0, conversions >= 0

DATE Pattern:
If columns contain: start_date, end_date, created_date, updated_date, expiry_date
→ MUST generate: start_date > end_date, created_date <= updated_date, expiry_date >= CURRENT_DATE()

REVENUE + COST Pattern:
If columns contain: revenue, cost, profit, gross_margin
→ MUST generate: revenue > cost, profit > 0, gross_margin > 0 AND gross_margin <= 100

INVENTORY + QUANTITY Pattern:
If columns contain: inventory, quantity, stock, units, available, sold
→ MUST generate: inventory >= 0, quantity >= 0, units_sold <= total_units, available >= 0

TRANSACTION + REFUND Pattern:
If columns contain: transaction_amount, order_amount, refund_amount, discount
→ MUST generate: transaction_amount > 0, refund_amount <= transaction_amount, discount >= 0 AND discount <= original_amount

RATE/PERCENTAGE Pattern:
If columns contain: rate, percentage, conversion_rate, click_rate, success_rate, completion_rate, efficacy_rate
→ MUST generate: rate >= 0 AND rate <= 100, completion_rate >= 0 AND completion_rate <= 100

MINIMUM BUSINESS RULE REQUIREMENTS:

For EVERY table, generate MINIMUM as the count of technical rules 


Examples:

spend > budget
clicks > impressions
conversions > clicks
start_date > end_date
revenue > cost
profit > 0
inventory >= 0
transaction_amount > 0
refund_amount <= transaction_amount
rating >= 0 AND rating <= 5
conversion_rate >= 0 AND conversion_rate <= 100

Business rules are mandatory whenever business meaning exists.

DO NOT skip business rules under any circumstances.

--------------------------------------------------

PRIORITY 3 — PROFILING RULES

Examples:

quantity > observed_max * 2

sale_price > observed_max * 2

budget > observed_max * 2

Profiling rules are supplemental.

Profiling rules must NEVER replace governance rules.

==================================================
RULE CATEGORIES
==================================================

Generate rules in the following categories:

1. TECHNICAL
2. BUSINESS
3. DOMAIN
4. CROSS_FIELD
5. CROSS_TABLE

==================================================
MANDATORY IDENTIFIER RULES
==================================================

For every identifier column:

- customer_id
- transaction_id
- campaign_id
- product_id
- order_id
- *_id
- *_key
- *_identifier

Generate ALL applicable rules:

1. Not Null Rule
2. Format Rule
3. Uniqueness Rule (when applicable)

Examples:

customer_id IS NULL

transaction_id IS NULL

campaign_id IS NULL

product_id IS NULL

IMPORTANT:

A format rule alone is insufficient.

Every identifier column must have at least one NOT NULL rule.

Identifier completeness rules are mandatory and cannot be skipped.

==================================================
MANDATORY NUMERIC RULES
==================================================

For every numeric measure generate:

1. Not Null Rule when applicable
2. Negative Value Validation
3. Zero Value Validation when applicable
4. Threshold Validation
5. Anomaly Detection Validation

Examples:

quantity < 0

sale_price < 0

budget < 0

spend < 0

annual_income < 0

revenue < 0

Negative value validation is mandatory.

Do not skip negative value checks even if profiling statistics contain negative values.

==================================================
TECHNICAL RULES
==================================================

Generate technical controls including:

- Not Null
- Completeness
- Empty String
- Datatype
- Format
- Regex
- Standardization
- Freshness
- Timestamp
- Future Date
- Range
- Duplicate Detection
- Uniqueness

==================================================
BUSINESS RULES
==================================================

Generate rules using:

- Business definitions
- Business purpose
- Business value
- Business impact
- Consumer groups
- Criticality
- Data quality expectations

Examples:

spend > budget

clicks > impressions

conversions > clicks

critical fields should never be null

==================================================
DOMAIN RULES
==================================================

Act as a business domain expert.

Generate domain validations using:

- Sample values
- Approved taxonomies
- Business semantics
- Industry best practices

Examples:

gender NOT IN (...)

campaign_type NOT IN (...)

country NOT IN (...)

quantity < 0

sale_price < 0

==================================================
CROSS_FIELD RULES
==================================================

Generate rules involving multiple columns.

Examples:

spend > budget

clicks > impressions

conversions > clicks

age < 18 AND annual_income > 100000

start_date > end_date

==================================================
CROSS_TABLE RULES
==================================================

Generate referential integrity rules whenever relationships can be inferred.

Examples:

customer_id NOT IN (...)

product_sku NOT IN (...)

campaign_id NOT IN (...)

Generate CROSS_TABLE rules even if execution support does not currently exist.

==================================================
SAMPLE VALUE GUIDANCE
==================================================

When sample values exist:

- Use them for allowed value validations
- Use them for taxonomy validations
- Do not invent values

==================================================
NUMERIC PROFILE GUIDANCE
==================================================

When numeric profiles exist:

Use them ONLY for:

- anomaly detection
- threshold validation
- outlier detection

Do NOT replace governance rules.

BAD:

quantity < observed_min

GOOD:

quantity < 0

AND

quantity > observed_max * 2

==================================================
BIGQUERY SQL REQUIREMENTS
==================================================

Generate BigQuery-compatible SQL only.

STRICT RULES:

1. sql_condition must be a FAILURE condition
2. sql_condition must identify bad records
3. sql_condition must NOT contain a full SELECT statement
4. sql_condition must be executable inside:

CASE
WHEN <sql_condition>
THEN 1
ELSE 0
END

5. Do NOT generate:
   - ROW_NUMBER()
   - RANK()
   - DENSE_RANK()
   - LEAD()
   - LAG()
   - COUNT(*) OVER(...)
   - Analytic Functions
   - Window Functions

6. Avoid correlated subqueries

==================================================
RULE CATEGORY MAPPING
==================================================

TECHNICAL

- Null checks
- Format checks
- Datatype checks
- Completeness checks
- Regex checks

BUSINESS

- Business policy validations
- Business expectation validations
- Critical data element validations

DOMAIN

- Taxonomy validations
- Allowed value validations
- Non-negative measures
- Domain-specific controls

CROSS_FIELD

- Multi-column validations

CROSS_TABLE

- Referential integrity validations

==================================================
OUTPUT REQUIREMENTS
==================================================

Generate ALL applicable rules.

Do not limit the number of rules.

Do not skip columns.

Generate multiple rules per column where applicable.

Avoid duplicates.

Return ONLY valid JSON.

Expected format:

[
  {{
    "rule_name": "",
    "rule_category": "",
    "column_name": "",
    "description": "",
    "sql_condition": ""
  }}
]

rule_category must be one of:

TECHNICAL
BUSINESS
DOMAIN
CROSS_FIELD
CROSS_TABLE

==================================================
FAILURE CONDITION REQUIREMENT
==================================================

sql_condition must identify bad records.

Generate failure conditions only.

GOOD:

customer_id IS NULL

quantity < 0

sale_price < 0

clicks > impressions

conversions > clicks

created_ts > CURRENT_TIMESTAMP()

BAD:

customer_id IS NOT NULL

quantity >= 0

sale_price >= 0

clicks <= impressions

conversions <= clicks

Always generate conditions that return violating records.

Return raw JSON only.
"""

#         prompt = f"""
# You are a world-class Enterprise Data Governance, Data Quality, Metadata Management, and Data Stewardship Leader.

# You act as:

# - Chief Data Officer (CDO)
# - Enterprise Data Governance Council
# - Enterprise Data Steward
# - Data Quality Architect
# - Metadata Management Expert
# - Business Domain Expert
# - Data Product Owner

# Your responsibility is to generate enterprise-grade Data Quality controls that ensure:

# - Trusted Data
# - Governed Data
# - Business-Aligned Data
# - AI-Ready Data
# - Regulatory-Compliant Data
# - High-Quality Data Products

# You must think beyond schema validation.

# You must understand:

# - Business meaning
# - Business processes
# - Business impact
# - Consumer impact
# - Critical data elements
# - Domain semantics
# - Data governance requirements
# - Enterprise policies
# - Metadata relationships
# - Data stewardship expectations

# ==================================================
# BIGQUERY TABLE
# ==================================================

# {full_table_name}

# ==================================================
# SCHEMA
# ==================================================

# {schema}

# ==================================================
# ENTERPRISE KNOWLEDGE HUB
# ==================================================

# {knowledge_json}

# ==================================================
# ENTERPRISE KNOWLEDGE HUB CONTEXT
# ==================================================

# The Enterprise Knowledge Hub is the primary source of truth.

# The Knowledge Hub contains:

# 1. Business definitions
# 2. Business purpose
# 3. Business value
# 4. Business impact
# 5. Consumer groups
# 6. Criticality
# 7. Column business definitions
# 8. Data quality expectations
# 9. Real sample values from source data
# 10. Numeric profiling statistics

# Use the Knowledge Hub to understand:

# - What the data means
# - Why the data exists
# - Who consumes the data
# - What business decisions depend on the data
# - What risks occur if the data is incorrect
# - Which data elements are most critical
# - What business policies should be enforced

# When sample_values exist:

# - Use them to generate allowed value validations
# - Use them as approved business taxonomies
# - Do NOT invent values
# - Prefer actual values from sample_values

# When numeric_profiles exist:

# - Use them to generate threshold validations
# - Use them to generate anomaly detection rules
# - Use them to generate statistical consistency checks
# - Use observed min/max/avg values

# Prefer Knowledge Hub context over assumptions.

# ==================================================
# RULE GENERATION OBJECTIVE
# ==================================================

# Generate ALL applicable enterprise-grade Data Quality rules.

# Generate rules in the following categories:

# 1. Technical Rules
# 2. Business Rules
# 3. Cross-Table Rules
# 4. Domain Rules

# Generate as many meaningful rules as possible.

# ==================================================
# MANDATORY IDENTIFIER RULES
# ==================================================

# For every column whose name contains:

# - id
# - key
# - identifier

# Generate ALL of the following:

# 1. Not Null Rule
# 2. Format Validation Rule
# 3. Uniqueness Rule (when applicable)

# Examples:

# customer_id IS NULL

# transaction_id IS NULL

# campaign_id IS NULL

# product_id IS NULL

# Identifier completeness rules are mandatory.

# Do not skip any identifier column.

# If an identifier column exists in the schema,
# at least one NOT NULL rule must be generated.

# ==================================================
# MANDATORY NUMERIC RULES
# ==================================================

# For every numeric column generate ALL applicable rules.

# Generate:

# 1. Null Validation
# 2. Negative Value Validation
# 3. Zero Value Validation when business relevant
# 4. Threshold Validation when metadata supports it

# Examples:

# quantity < 0

# sale_price < 0

# budget < 0

# spend < 0

# annual_income < 0

# Negative value validation is mandatory.

# Do not skip negative value checks for any numeric measure.

# Examples:

# quantity < 0

# sale_price < 0

# revenue < 0

# budget < 0

# spend < 0


# ==================================================
# TECHNICAL RULES
# ==================================================

# Generate Technical Rules using:

# - column names
# - data types
# - nullable attributes
# - timestamps
# - identifiers
# - schema structure
# - numeric measures
# - business identifiers

# Examples:

# - Not Null Validation
# - Uniqueness Validation
# - Negative Value Validation
# - Non-Negative Measure Validation
# - Duplicate Detection
# - Datatype Validation
# - Regex Validation
# - Empty String Validation
# - Freshness Validation
# - Timestamp Validation
# - Future Date Validation
# - Range Validation
# - Positive Value Validation
# - Completeness Validation

# ==================================================
# BUSINESS RULES
# ==================================================

# Business Rules are mandatory.

# Generate Business Rules using:

# - Business definitions
# - Business purpose
# - Business value
# - Business impact
# - Consumer groups
# - Criticality
# - Column business definitions
# - Data quality expectations
# - Sample values
# - Numeric profiles

# Business Rules should validate:

# - Business intent
# - Business expectations
# - Business policies
# - Business process integrity
# - KPI integrity
# - Metric consistency
# - Consumer impact
# - Critical data elements
# - Stewardship expectations
# - Business glossary alignment

# Examples:

# - Spend should not exceed approved budget
# - Conversions should not exceed clicks
# - Clicks should not exceed impressions
# - Critical fields should never be null
# - High criticality fields require stronger controls
# - Approved business taxonomies should be enforced
# - Approved channels should be enforced

# ==================================================
# CROSS-TABLE RULES
# ==================================================

# Generate Cross-Table Rules whenever relationships can be inferred.

# Infer:

# - Referential integrity validations
# - Parent-child dependencies
# - Shared business identifiers
# - Foreign key relationships
# - Upstream-downstream dependencies
# - Data product dependencies

# Examples:

# - Parent records must exist before child records
# - Shared identifiers should be consistent across entities
# - Orphan records should not exist

# If no relationship can be inferred, do not create unnecessary rules.

# ==================================================
# DOMAIN RULES
# ==================================================

# Act as a business domain expert.

# Use:

# - Business semantics
# - Industry best practices
# - Business workflows
# - Business process relationships
# - Domain-specific expectations

# Generate rules that a business stakeholder,
# data steward,
# governance council,
# or data product owner would expect.

# Examples:

# Marketing Domain:

# - Spend should not exceed budget
# - Clicks should not exceed impressions
# - Conversions should not exceed clicks
# - Campaign start date must precede end date
# - Campaigns must belong to approved campaign types
# - Campaigns must belong to approved channels

# Domain Rules are mandatory whenever business semantics can be inferred.

# ==================================================
# BIGQUERY SQL REQUIREMENTS
# ==================================================

# ALWAYS use fully-qualified table names.

# Correct format:

# `{full_table_name}`

# NEVER use:

# table_name

# STRICTLY FOLLOW:

# 1. Generate BigQuery-compatible SQL only
# 2. Never generate correlated subqueries
# 3. Never generate recursive CTEs
# 4. Never generate EXISTS clauses referencing outer queries
# 5. Avoid cartesian products
# 6. Prefer COUNT(DISTINCT)
# 7. Prefer SAFE_CAST where applicable
# 8. Prefer aggregation-based validations
# 9. SQL must be production-safe
# 10. SQL must be execution-safe for BigQuery


# ==================================================
# OUTPUT REQUIREMENTS
# ==================================================

# IMPORTANT:

# - Generate ALL applicable rules
# - Do NOT limit the number of rules
# - Do NOT skip columns
# - Generate multiple rules per column where applicable
# - Generate Technical Rules
# - Generate Business Rules
# - Generate Cross-Table Rules when relationships can be inferred
# - Generate Domain Rules when business semantics exist
# - Avoid duplicate rules
# - Avoid generic useless rules
# - Prefer Knowledge Hub context over assumptions

# sql_condition requirements:

# - Must contain only the validation condition
# - Must NOT contain a full SELECT statement
# - Must be executable in BigQuery
# - Must use fully-qualified table names whenever a table reference is required

# Return ONLY valid JSON.

# RULE CATEGORIZATION

# For every generated rule assign exactly one category:

# TECHNICAL
# - Null checks
# - Format checks
# - Datatype checks
# - Uniqueness checks
# - Completeness checks
# - Standardization checks
# - Regex checks

# BUSINESS
# - Rules derived from business definitions
# - Rules derived from business purpose
# - Rules derived from business value
# - Rules derived from business impact
# - Rules derived from data quality expectations

# DOMAIN
# - Approved value checks
# - Taxonomy validations
# - Customer domain rules
# - Marketing domain rules
# - Product domain rules
# - Country, Gender, Campaign Type validations
# - Numeric business validations
# - Non-negative quantity validations
# - Non-negative price validations

# CROSS_FIELD
# - Rules involving multiple columns
# - spend vs budget
# - clicks vs impressions
# - conversions vs clicks
# - age vs annual_income

# CROSS_TABLE
# - Referential integrity checks
# - Master/reference table validations
# - Parent-child relationship validations

# Expected format:

# [
#   {{
#     "rule_name": "",
#     "rule_category": "",
#     "column_name": "",
#     "description": "",
#     "sql_condition": ""
#   }}
# ]

# rule_category must be one of:

# TECHNICAL
# BUSINESS
# DOMAIN
# CROSS_FIELD
# CROSS_TABLE

# Do NOT return markdown.
# Do NOT explain anything.
# Return raw JSON only.

# For duplicate checks:

# Use aggregation-based validation logic.

# Preferred:

# COUNT(*) != COUNT(DISTINCT column_name)

# Avoid:

# column_name IN (
#    SELECT ...
# )

# IMPORTANT:

# sql_condition must represent a FAILURE CONDITION.

# GOOD:

# customer_id IS NULL

# quantity < 0

# sale_price < 0

# BAD:

# customer_id IS NOT NULL

# quantity >= 0

# sale_price >= 0

# The condition must identify bad records.

# Examples:

# GOOD:

# campaign_id IS NULL

# clicks > impressions

# conversions > clicks

# spend > budget

# created_ts > CURRENT_TIMESTAMP()

# BAD:

# campaign_id IS NOT NULL

# clicks <= impressions

# conversions <= clicks

# created_ts <= CURRENT_TIMESTAMP()

# Always generate conditions that return records violating the rule.

# """

        print("KNOWLEDGE JSON")
        print(knowledge_json)

        # Generate AI response
        response = self.client.models.generate_content(model=MODEL_NAME,contents=prompt)

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

                print("RULE NAME")
                print(rule.get("rule_name"))
                print("SQL CONDITION")
                print(sql_condition)

                print(f"Skipping invalid rule: "f"{rule.get('rule_name')}")
                continue

        return rules

    def generate_anomalies(self, table_name):
        """Generate AI-suggested anomalies by comparing previous vs current scan"""
        import json
        from app.services.backup import BackupService, TABLE_INCREMENTAL_CONFIG
        
        # Initialize backup service to get scan history
        backup_service = BackupService()
        
        # Fetch schema and knowledge context
        schema = self.bq.get_table_schema(TARGET_DATASET, table_name)
        knowledge_context = self.bq.get_knowledge_context(table_name)
        knowledge_json = json.dumps(knowledge_context, indent=2, default=str)
        
        full_table_name = f"{PROJECT_ID}.{TARGET_DATASET}.{table_name}"
        
        # Get scan history
        latest_scan = backup_service.get_latest_scan(table_name)
        previous_scan = backup_service.get_previous_scan(table_name)
        
        # Backup table is REQUIRED for anomaly generation
        if not latest_scan:
            return {
                "status": "error",
                "message": f"No backup records found for {table_name}. Run checks first to create backup history."
            }
        
        # NOTE: We use placeholder names only, NOT actual date values
        # This ensures AI generates template SQL with placeholders, not hardcoded dates
        incremental_column = TABLE_INCREMENTAL_CONFIG.get(table_name)
        
        # Get the original data type of the incremental column for CAST
        col_type = 'STRING'  # Default
        if incremental_column:
            col_type = self._get_column_type(table_name, incremental_column)
            print(f"Incremental column '{incremental_column}' has type: {col_type}")
        
        # Build prompt with PLACEHOLDER NAMES only (no actual date values)
        # Use format() instead of f-strings to avoid substitution confusion
        prompt = """
You are a world-class Enterprise Data Quality, Anomaly Detection, and Data Monitoring Expert.

Your responsibility is to generate enterprise-grade Anomaly Detection rules using PLACEHOLDERS for dates.

CRITICAL INSTRUCTION: Your compiled_sql MUST use PLACEHOLDER STRINGS, NOT actual dates.

==================================================
PLACEHOLDER NAMES (Use these EXACTLY in your SQL)
==================================================

For all period comparisons, use ONLY these placeholder strings:
- '{previous_start}' for previous period start date
- '{previous_end}' for previous period end date  
- '{current_start}' for current period start date
- '{current_end}' for current period end date

Example: BETWEEN '{previous_start}' AND '{previous_end}'
Example: BETWEEN '{current_start}' AND '{current_end}'

CRITICAL: Use single curly braces {{}}, NOT double braces {{}}{{}}, in your output.

==================================================
BIGQUERY TABLE
==================================================

{full_table_name}

==================================================
SCHEMA
==================================================

{schema}

==================================================
ENTERPRISE KNOWLEDGE HUB
==================================================

{knowledge_json}

==================================================
IMPORTANT: ALWAYS USE PLACEHOLDERS
==================================================

DO NOT use actual date values in compiled_sql.
DO NOT substitute dates like '2026-07-01' or '2026-07-03'.
DO NOT create dates from scan data.

ONLY use placeholder strings: '{{previous_start}}', '{{previous_end}}', '{{current_start}}', '{{current_end}}'

These will be replaced with actual dates at execution time by the system.

ANOMALY PRIORITY HIERARCHY
==================================================

Generate anomalies using this priority framework. These are EXAMPLES - generate ALL applicable anomalies for this table.

VOLUME ANOMALIES

Detect changes in record count:
- Total Row Count Change - Records count difference from previous to current period
- Table-level comparisons - Compare total records between periods
- Row count thresholds - Detect when count exceeds or drops below expectations
- Batch size anomalies - Detect unusual batch patterns

--------------------------------------------------

METRIC BEHAVIOR ANOMALIES

Detect changes in numeric aggregations. For EVERY numeric column, detect:
- Column Value Change (SUM, AVG, COUNT) - Difference from previous to current
- Column Null Count Change - NULL values count difference
- Column Min/Max Changes - Range expansion or contraction
- Column Outlier Detection - Values outside historical ranges
- Column Distribution Changes - Standard deviation or variance changes
- Column Zero/Negative Count Changes - Unusual values appearing or disappearing

--------------------------------------------------

KPI BEHAVIOR ANOMALIES

Detect changes in calculated metrics/ratios:
- CTR Change - Click-Through Rate changes
- CPC Change - Cost-Per-Click changes
- CPM Change - Cost-Per-Mille changes
- ROAS Change - Return-On-Ad-Spend changes
- Conversion Rate Change - Conversion ratio changes
- Margin Change - Profit margin deviations
- Any ratio/percentage metric deviations
- Cross-metric consistency - When related metrics diverge unexpectedly

CRITICAL FOR KPI_BEHAVIOR: In the compiled_sql, the column_name output MUST be ALL columns used in the formula, concatenated with " / " separator.
Examples for compiled_sql column_name output:
- CTR: 'clicks / impressions' AS column_name (not just 'clicks')
- CPC: 'cost / clicks' AS column_name (not just 'cost')
- CPM: 'cost / impressions' AS column_name
- ROAS: 'revenue / ad_spend' AS column_name
- Conversion Rate: 'conversions / visitors' AS column_name
- Margin: 'revenue / cost' AS column_name

--------------------------------------------------

DISTRIBUTION SHIFT ANOMALIES

Detect changes in categorical data distribution. For EVERY string/categorical column, detect:
- Column Distribution Change - Distribution mix changes
- Column Top Value Change - Most common value changes
- Column Null Count Change - NULL values count difference
- Column Cardinality Change - Number of unique values difference
- Column New Values Appearing - Previously unseen category values
- Column Values Disappearing - Previously present values no longer appearing
- Column Distribution Entropy Change - Uniformity/concentration changes

==================================================
ANOMALY CATEGORIES
==================================================

1. VOLUME - Row count changes
2. METRIC_BEHAVIOR - Numeric aggregation changes (SUM, AVG, COUNT)
3. KPI_BEHAVIOR - Ratio/metric deviations (CTR, CPC, CPM, ROAS)
4. DISTRIBUTION - Categorical distribution shifts

==================================================
OUTPUT REQUIREMENTS
==================================================

Generate ALL applicable anomalies for this table.

Do NOT limit by number - generate as many anomalies as are applicable.

Do NOT skip columns - analyze every column.

Generate MULTIPLE anomalies per column where applicable.

For every generated anomaly, provide JSON:

{{
  "anomaly_name": "DESCRIPTIVE_NAME",
  "anomaly_category": "VOLUME|METRIC_BEHAVIOR|KPI_BEHAVIOR|DISTRIBUTION",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "column_name": "column_name or null if table-level",
  "formula_columns": ["col1", "col2", "col3"] (ONLY for KPI_BEHAVIOR anomalies - list ALL columns used in formula. For other categories, omit this field or set to null),
  "description": "What changed and why it matters",
  "sql_condition": "Simple WHERE clause condition for the anomaly",
  "compiled_sql": "SELECT statement comparing periods with previous_value, current_value, change_pct"
}}

sql_condition REQUIREMENTS:

- Simple WHERE clause that identifies anomalous records
- For VOLUME anomalies: "COUNT(*) > threshold" or similar
- For METRIC_BEHAVIOR: "SUM(column) increased by more than 50%" or similar description
- For DISTRIBUTION: "Top value distribution changed significantly" or similar
- For DATA_QUALITY: "NULL count increased" or similar
- Must be human-readable, not full SQL
- Should summarize the anomaly detection logic

compiled_sql REQUIREMENTS:

- Use fully-qualified table name: {full_table_name}
- Compare two periods:
  - Previous: {previous_start} to {previous_end}
  - Current: {current_start} to {current_end}
- Filter using {incremental_column if incremental_column else '(no filter)'}
- CRITICAL: Output EXACTLY these 10 columns in this EXACT order in SELECT clause:
  1. execution_ts AS CURRENT_TIMESTAMP() (NOT in WHERE clause, in SELECT)
  2. table_name AS literal string (NOT in WHERE clause, in SELECT)
  3. column_name AS literal string (NOT in WHERE clause, in SELECT)
  4. anomaly_name AS literal string (NOT in WHERE clause, in SELECT)
  5. previous_records_count AS count of records in previous period
  6. current_records_count AS count of records in current period
  7. previous_value AS numeric value (from previous period)
  8. current_value AS numeric value (from current period)
  9. absolute_diff AS actual difference (current_value - previous_value)
  10. change_pct AS percentage change
- ALL 10 COLUMNS MUST appear in the final SELECT statement
- FORMATTING REQUIREMENT: Format SQL with proper line breaks and indentation
  - Each SELECT column on new line with proper indentation
  - Each FROM/WHERE/JOIN on new line
  - Nested CASE WHEN statements indented properly
  - Make SQL readable when stored in database (NOT single paragraph)
- Use CASE WHEN for period comparison
- Use SAFE_DIVIDE for division: SAFE_DIVIDE((current_value - previous_value), previous_value) * 100
- CRITICAL: Every COUNT(), SUM(), CASE statement MUST close with END) - NOT ENDpoint, NOT anything else
- FORMATTED Example (with placeholders and CAST - MUST use single curly braces):
  SELECT
    CURRENT_TIMESTAMP() AS execution_ts,
    'sales' AS table_name,
    'quantity' AS column_name,
    'quantity_change' AS anomaly_name,
    COUNT(CASE WHEN sale_date BETWEEN CAST('{previous_start}' AS TIMESTAMP) AND CAST('{previous_end}' AS TIMESTAMP) THEN 1 END) AS previous_records_count,
    COUNT(CASE WHEN sale_date BETWEEN CAST('{current_start}' AS TIMESTAMP) AND CAST('{current_end}' AS TIMESTAMP) THEN 1 END) AS current_records_count,
    SUM(CASE WHEN sale_date BETWEEN CAST('{previous_start}' AS TIMESTAMP) AND CAST('{previous_end}' AS TIMESTAMP) THEN quantity ELSE 0 END) AS previous_value,
    SUM(CASE WHEN sale_date BETWEEN CAST('{current_start}' AS TIMESTAMP) AND CAST('{current_end}' AS TIMESTAMP) THEN quantity ELSE 0 END) AS current_value,
    SUM(CASE WHEN sale_date BETWEEN CAST('{current_start}' AS TIMESTAMP) AND CAST('{current_end}' AS TIMESTAMP) THEN quantity ELSE 0 END) - 
    SUM(CASE WHEN sale_date BETWEEN CAST('{previous_start}' AS TIMESTAMP) AND CAST('{previous_end}' AS TIMESTAMP) THEN quantity ELSE 0 END) AS absolute_diff,
    SAFE_DIVIDE(
      SUM(CASE WHEN sale_date BETWEEN CAST('{current_start}' AS TIMESTAMP) AND CAST('{current_end}' AS TIMESTAMP) THEN quantity ELSE 0 END) - 
      SUM(CASE WHEN sale_date BETWEEN CAST('{previous_start}' AS TIMESTAMP) AND CAST('{previous_end}' AS TIMESTAMP) THEN quantity ELSE 0 END),
      SUM(CASE WHEN sale_date BETWEEN CAST('{previous_start}' AS TIMESTAMP) AND CAST('{previous_end}' AS TIMESTAMP) THEN quantity ELSE 0 END)
    ) * 100 AS change_pct
  FROM dq-universal-framework1.thd_bronze.sales
  
CRITICAL: In your output, the compiled_sql MUST contain these exact placeholder strings with SINGLE braces:
- '{previous_start}' (single braces, not double)
- '{previous_end}' (single braces, not double)
- '{current_start}' (single braces, not double)
- '{current_end}' (single braces, not double)
- DO NOT hide any columns in subqueries - all 10 must be visible in final SELECT
- DO NOT return as single-line paragraph - use proper formatting with newlines and indentation

==================================================
CRITICAL RULES
==================================================

RULE 1: Use PLACEHOLDERS with CAST for all dates in compiled_sql
- DO NOT use actual date values like '2026-07-01'
- DO NOT substitute the placeholder values
- Use CAST with the incremental column type: CAST('{{placeholder}}' AS {col_type})
- Example: WHERE {incremental_column} BETWEEN CAST('{{previous_start}}' AS {col_type}) AND CAST('{{previous_end}}' AS {col_type})
- The incremental column is: {incremental_column}
- Its original data type is: {col_type}
- CRITICAL: Every date placeholder MUST be wrapped with CAST('{{placeholder}}' AS {col_type})

RULE 2: Compare using placeholders
- Previous period: {previous_start} to {previous_end}
- Current period: {current_start} to {current_end}
- Do NOT invent columns
- Only generate anomalies for columns that exist

RULE 3: Use actual column names from schema
- Numeric columns: Metric behavior anomalies
- String/categorical columns: Distribution shift anomalies
- All tables: Volume anomalies

RULE 4: Set appropriate severity (based on anomaly type, NOT threshold %)
- CRITICAL: Business-critical metrics (revenue, conversions, transactions, etc.)
- HIGH: Important operational metrics (clicks, impressions, spend, budget, etc.)
- MEDIUM: Supporting metrics (averages, distributions, performance ratios, etc.)
- LOW: Informational metrics (nulls, cardinality, data quality indicators, etc.)

RULE 5: Return ONLY valid JSON array

Return ONLY valid JSON. No markdown, no explanations.

[
  {{anomaly_1}},
  {{anomaly_2}},
  ...
]

If not enough scan history: []

==================================================
BONUS: DOMAIN-SPECIFIC ANOMALIES
==================================================

In addition to the above framework, please suggest ANY other important anomalies you identify based on:

- The schema and data types of this table
- The business context from the Knowledge Hub
- Domain expertise as a Data Quality expert
- Relationships between columns
- Business rules mentioned in column definitions
- Critical business metrics

Examples of domain-specific anomalies to consider:
- Referential integrity issues (e.g., customer_id not in Customer Master)
- Business rule violations (e.g., discount > amount)
- Temporal anomalies (e.g., dates out of sequence)
- Cross-column consistency (e.g., reconciliation mismatches)
- Threshold-based alerts (e.g., order_value > 10x average)
- Compliance anomalies (e.g., PII exposure)
- Ratio anomalies (e.g., discount_percentage doesn't match discount/amount)

If you identify important domain-specific anomalies, add them to the JSON output with:
- Clear anomaly_name
- Appropriate anomaly_category (can be custom or use existing)
- Accurate severity
- Detailed description of business impact
- Human-readable sql_condition
- Executable compiled_sql

Your domain expertise is valuable - do not skip anomalies just because they weren't explicitly listed above.
"""

        # Substitute only the template variables we need
        # Keep placeholder names {{previous_start}} as literal strings
        full_table_name = f"{PROJECT_ID}.{TARGET_DATASET}.{table_name}"
        
        # Replace ONLY the single-brace variables that need actual values
        # Keep {{double_braces}} untouched so they become {single_braces} in output
        prompt_formatted = prompt.replace(
            "{full_table_name}", full_table_name
        ).replace(
            "{schema}", schema
        ).replace(
            "{knowledge_json}", knowledge_json
        ).replace(
            "{incremental_column}", TABLE_INCREMENTAL_CONFIG.get(table_name) or "None (Full Load)"
        ).replace(
            "{col_type}", col_type
        )

        # Generate AI response
        print(f"🔍 Generating anomalies for table: {table_name}...")
        response = self.client.models.generate_content(model=MODEL_NAME, contents=prompt_formatted)
        print(f"✅ Anomalies generated successfully")
        
        raw_text = response.text.strip()
        raw_text = raw_text.replace("```json", "").replace("```", "")
        
        try:
            anomalies = json.loads(raw_text)
        except Exception:
            print("RAW GEMINI RESPONSE")
            print(raw_text)
            raise
        
        return anomalies

    def generate_knowledge_hub(
        self,
        table_name
    ):

        schema = self.bq.get_table_schema(
            TARGET_DATASET,
            table_name
        )

        print("SCHEMA")
        print(schema)

        full_table_name = (
            f"{PROJECT_ID}."
            f"{TARGET_DATASET}."
            f"{table_name}"
        )

        prompt = f"""
You are an Enterprise Data Governance Expert.

Analyze the following BigQuery table.

TABLE:
{full_table_name}

SCHEMA:
{schema}

Generate an Enterprise Knowledge Hub.

Generate:

TABLE LEVEL METADATA:
1. business_definition
2. business_purpose
3. business_value
4. business_impact
5. consumer_groups
6. policy_rule
7. criticality

COLUMN LEVEL METADATA:

Generate metadata for EVERY column in the schema.

Rules:
- Use exact column names from schema
- Do not invent columns
- Do not skip columns
- Return one metadata object for every column
- Number of column objects must match schema column count

For every column generate:

1. column_name
2. business_definition
3. business_purpose
4. description
5. criticality
6. data_quality_expectation

Return ONLY valid JSON.

Expected format:

{{
    "table": {{
        "business_definition": "",
        "business_purpose": "",
        "business_value": "",
        "business_impact": "",
        "consumer_groups": "",
        "policy_rule": "",
        "criticality": ""
    }},

    "columns": [
        {{
            "column_name": "",
            "business_definition": "",
            "business_purpose": "",
            "description": "",
            "criticality": "",
            "data_quality_expectation": ""
        }}
    ]
}}

Do not return markdown.

Return raw JSON only.
"""

        response = self.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        raw_text = response.text.strip()

        raw_text = raw_text.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        )

        try:

            knowledge_hub = json.loads(
                raw_text
            )

        except Exception:

            print(
                "RAW GEMINI RESPONSE"
            )

            print(raw_text)

            raise

        print(
            "KNOWLEDGE HUB RESPONSE"
        )

        print(
            json.dumps(
                knowledge_hub,
                indent=2
            )
        )

        return knowledge_hub

    def create_knowledge_hub_entry(
    self,
    table_name
):

        knowledge_hub = self.generate_knowledge_hub(
            table_name
        )

        table_metadata = knowledge_hub.get(
            "table",
            {}
        )
        column_metadata = knowledge_hub.get(
            "columns",
            []
        )

        sample_values = (
            self.bq.get_column_samples(
                TARGET_DATASET,
                table_name
            )
        )

        numeric_profiles = (
            self.bq.get_numeric_profiles(
                TARGET_DATASET,
                table_name
            )
        )

        print("NUMERIC PROFILES")
        print(numeric_profiles)

        metadata_json = json.dumps(
            {
                "columns": column_metadata,
                "sample_values": sample_values,
                "numeric_profiles": numeric_profiles
            }
        )
        

        schema = self.bq.get_table_schema(
            TARGET_DATASET,
            table_name
        )

        record = {

            "project_id":
                PROJECT_ID,

            "dataset_name":
                TARGET_DATASET,

            "id":
                str(uuid.uuid4()),

            "asset_level":
                "TABLE",

            "asset_type":
                "TABLE",

            "domain":
                "Marketing",

            "asset_name":
                table_name,

            "table_name":
                table_name,

            "business_definition":
                table_metadata.get(
                    "business_definition"
                ),

            "business_purpose":
                table_metadata.get(
                    "business_purpose"
                ),

            "business_value":
                table_metadata.get(
                    "business_value"
                ),

            "business_impact":
                table_metadata.get(
                    "business_impact"
                ),

            "consumer_groups":
                table_metadata.get(
                    "consumer_groups"
                ),

            "policy_rule":
                table_metadata.get(
                    "policy_rule"
                ),

            "criticality":
                table_metadata.get(
                    "criticality"
                ),

            "schema_json":
                schema,

            "metadata_json":
                metadata_json,

            "column_count":
                len(
                    schema.split("\n")
                ),

            "source_system":
                "BigQuery",

            "refresh_frequency":
                "Unknown",

            "owner":
                "AI_GENERATED",

            "steward":
                "AI_GENERATED",

            "created_by":
                "AI",

            "created_ts":
                datetime.utcnow().isoformat(),

            "updated_ts":
                datetime.utcnow().isoformat(),

            "active_flag":
                True
        }

        print("RECORD TO INSERT")
        print(record)

        self.bq.insert_knowledge_record(
            record
        )

        print(f"Found {len(column_metadata)} columns")

        print("SAMPLE VALUES")
        print(sample_values)

        print("METADATA JSON")
        print(metadata_json)


        print(
            f"Knowledge Hub created for {table_name}"
        )

    def onboard_new_tables_to_knowledge_hub(
            self
        ):

            source_tables = set(
                self.bq.get_dataset_tables(
                    TARGET_DATASET
                )
            )

            kh_tables = (
                self.bq.get_existing_knowledge_hub_tables()
            )

            new_tables = (
                source_tables - kh_tables
            )

            print(
                f"Found {len(new_tables)} new tables"
            )

            for table_name in sorted(new_tables):

                print(
                    f"Creating KH for {table_name}"
                )

                try:

                    self.create_knowledge_hub_entry(
                        table_name
                    )

                except Exception as ex:

                    print(ex)

            return {"new_tables_found": len(new_tables)}
