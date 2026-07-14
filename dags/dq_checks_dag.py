"""
dq_checks_dag.py
----------------
Airflow DAG for Cloud Composer that runs DQ checks.

Triggered by "Run all checks" button in dq-hub-observability dashboard.
Manual trigger only - executes /execution/run-all API endpoint.

For Cloud Composer bucket structure:
- DAG is at: gs://bucket/dags/dq_checks_dag.py
- Observability app is at: gs://bucket/dags/dq-hub-observability/
- Composer mounts bucket at: /home/airflow/gcs
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
import requests

default_args = {
    "owner": "data-team",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

def trigger_dq_checks():
    """Call the DQ observability API to run all checks."""
    try:
        # API endpoint - adjust URL based on your observability app deployment
        api_url = "https://dq-hub-871650912439.us-central1.run.app/execution/run-all"
        
        response = requests.post(api_url, timeout=600)
        
        if response.status_code != 200:
            raise Exception(f"DQ checks failed: {response.text}")
        
        result = response.json()
        print(f"DQ checks completed: {result}")
        return result
    except Exception as e:
        print(f"Error triggering DQ checks: {e}")
        raise

with DAG(
    dag_id="dq_run_all_checks",
    default_args=default_args,
    description="Runs all DQ checks via observability dashboard (MANUAL TRIGGER ONLY)",
    schedule_interval=None,   # No schedule - manual trigger only via "Run all checks" button
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["dq", "observability", "checks", "manual-trigger"],
) as dag:

    run_dq_checks = PythonOperator(
        task_id="run_dq_checks",
        python_callable=trigger_dq_checks,
        doc="Executes /execution/run-all to check all DQ rules across monitored tables",
    )

    run_dq_checks