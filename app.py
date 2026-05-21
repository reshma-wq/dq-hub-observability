from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google.cloud import bigquery
import yaml
import uvicorn

app = FastAPI(title="Data Quality Hub Observability API")

# Enable CORS so your HTML frontend can seamlessly communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID = "dq-universal-framework"
TARGET_DATASET = "thd_bronze"

@app.get("/api/v1/summary")
def get_global_summary():
    """Queries Watchtower table to feed the top KPI cards on the Overview page."""
    client = bigquery.Client(project=PROJECT_ID)
    query = f"SELECT * FROM `{PROJECT_ID}.{TARGET_DATASET}.dq_watchtower_results` WHERE is_latest = 'Y'"
    df = client.query(query).to_dataframe()
    
    if df.empty:
        return {"health_index": 100, "total_tables": 0, "active_incidents": 0, "rows_affected": 0}
        
    total_rules = len(df)
    failed_rules_df = df[df['failed_count'] > 0]
    failed_count = len(failed_rules_df)
    
    health_index = ((total_rules - failed_count) / total_rules) * 100
    
    return {
        "health_index": round(health_index, 1),
        "total_tables": int(df['table_name'].nunique()),
        "active_incidents": int(failed_count),
        "rows_affected": int(df['failed_count'].sum())
    }

@app.get("/api/v1/table/{table_id}")
def get_table_rules_and_results(table_id: str):
    """Fetches active registered rules (YAML) and joins them with recent scan anomalies."""
    client = bigquery.Client(project=PROJECT_ID)
    
    # 1. Fetch live rules committed by the Streamlit app
    rules_query = f"SELECT yaml_config FROM `{PROJECT_ID}.{TARGET_DATASET}.dq_rules_registry` WHERE table_name = @table LIMIT 1"
    job_cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("table", "STRING", table_id)])
    rules_res = list(client.query(rules_query, job_config=job_cfg).result())
    
    # 2. Fetch latest watchtower metrics execution run
    watch_query = f"SELECT * FROM `{PROJECT_ID}.{TARGET_DATASET}.dq_watchtower_results` WHERE table_name LIKE @table_pattern AND is_latest = 'Y'"
    job_cfg_w = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("table_pattern", "STRING", f"%{table_id}")])
    watch_res = client.query(watch_query, job_config=job_cfg_w).to_dataframe()
    
    rules_list = []
    if rules_res:
        try:
            parsed_yaml = yaml.safe_load(rules_res[0].yaml_config)
            if isinstance(parsed_yaml, list):
                for index, r in enumerate(parsed_yaml):
                    # Match validation rule anomalies dynamically
                    match = watch_res[watch_res['rule_name'] == r.get('rule_name')]
                    violations = int(match['failed_count'].iloc[0]) if not match.empty else 0
                    
                    status = "passing"
                    if violations > 0:
                        status = "failing"
                        
                    rules_list.append({
                        "id": f"rule_{index}",
                        "column": r.get("column_name", "unknown"),
                        "name": r.get("rule_name", "unnamed"),
                        "status": status,
                        "violations": violations,
                        "description": r.get("description", ""),
                        "sql": f"SELECT * FROM {TARGET_DATASET}.{table_id} WHERE {r.get('sql_condition', '1=1')}"
                    })
        except Exception:
            pass
            
    return {"table_id": table_id, "rules": rules_list}

# Mount your frontend files to serve them directly from the API port
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)