-- =====================================================
-- CREATE DQ HUB DATASET
-- =====================================================

CREATE SCHEMA IF NOT EXISTS `dq-universal-framework.dq_hub`;

-- =====================================================
-- ENTERPRISE KNOWLEDGE HUB
-- =====================================================

CREATE TABLE IF NOT EXISTS
`dq-universal-framework.dq_hub.enterprise_knowledge_hub`
(
project_id STRING,
dataset_name STRING,

```
id STRING,

asset_level STRING,
asset_type STRING,

domain STRING,

asset_name STRING,
table_name STRING,
parent_asset STRING,

description STRING,

business_definition STRING,
business_purpose STRING,
business_value STRING,
business_impact STRING,
consumer_groups STRING,

data_type STRING,

schema_json STRING,
sample_values STRING,

row_count INT64,
column_count INT64,

primary_keys STRING,

source_system STRING,
refresh_frequency STRING,

last_profiled_ts TIMESTAMP,

owner STRING,
steward STRING,

criticality STRING,

tags STRING,

related_asset STRING,
relationship_type STRING,

policy_rule STRING,

ai_context_priority INT64,

metadata_json STRING,

created_by STRING,
created_ts TIMESTAMP,
updated_ts TIMESTAMP,

active_flag BOOL
```

);

-- =====================================================
-- DQ RULES REGISTRY
-- =====================================================

CREATE TABLE IF NOT EXISTS
`dq-universal-framework.dq_hub.dq_rules_registry`
(
rule_id STRING,

```
project_id STRING,
dataset_name STRING,

table_name STRING,
column_name STRING,

rule_name STRING,
rule_category STRING,
rule_source STRING,

rule_description STRING,

sql_condition STRING,
compiled_sql STRING,

severity STRING,

created_by STRING,

created_ts TIMESTAMP,
updated_ts TIMESTAMP,

active_flag BOOL
```

);

-- =====================================================
-- DQ EXECUTION RUNS
-- =====================================================

CREATE TABLE IF NOT EXISTS
`dq-universal-framework.dq_hub.dq_execution_runs`
(
run_id STRING,

```
project_id STRING,
dataset_name STRING,

table_name STRING,

execution_type STRING,

total_rules INT64,
completed_rules INT64,
failed_rules INT64,

status STRING,

started_at TIMESTAMP,
completed_at TIMESTAMP,

created_ts TIMESTAMP
```

);

-- =====================================================
-- DQ WATCHTOWER RESULTS
-- =====================================================

CREATE TABLE IF NOT EXISTS
`dq-universal-framework.dq_hub.dq_watchtower_results`
(
report_date DATE,

```
execution_ts TIMESTAMP,

run_id STRING,

project_id STRING,
dataset_name STRING,

table_name STRING,
column_name STRING,

rule_name STRING,
rule_category STRING,

total_records INT64,
passed_records INT64,
failed_records INT64,

pass_percentage FLOAT64,

execution_time_ms INT64,

execution_status STRING,
dq_status STRING,

created_ts TIMESTAMP
```

);
