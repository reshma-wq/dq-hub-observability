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

Examples:

spend > budget

clicks > impressions

conversions > clicks

start_date > end_date

Business rules are mandatory whenever business meaning exists.

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