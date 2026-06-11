#!/usr/bin/env python3
"""
Script to clear all DQ data from BigQuery (rules, results, and execution runs)
"""

from google.cloud import bigquery
from app.utils.config import PROJECT_ID, TARGET_DATASET
import time

def clear_all_data():
    """Clears all DQ data from BigQuery tables"""
    
    client = bigquery.Client(project=PROJECT_ID)
    
    tables_to_clear = [
        "dq_rules_registry",
        "dq_watchtower_results", 
        "dq_execution_runs"
    ]
    
    print(f"Clearing data from dataset: {TARGET_DATASET}")
    print(f"Project: {PROJECT_ID}\n")
    
    for table_name in tables_to_clear:
        table_id = f"{PROJECT_ID}.{TARGET_DATASET}.{table_name}"
        
        try:
            # Check if table exists
            table = client.get_table(table_id)
            print(f"✓ Found table: {table_name}")
            
            # Try TRUNCATE TABLE first (better for streaming buffer)
            try:
                query = f"TRUNCATE TABLE `{table_id}`"
                job = client.query(query)
                job.result()
                print(f"  ✓ Truncated {table_name}")
                continue
            except:
                pass
            
            # Fallback to DELETE with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    query = f"DELETE FROM `{table_id}` WHERE 1=1"
                    job = client.query(query)
                    job.result()
                    
                    print(f"  ✓ Cleared all data from {table_name}")
                    break
                    
                except Exception as e:
                    if "streaming buffer" in str(e) and attempt < max_retries - 1:
                        print(f"  ⏳ Streaming buffer detected, waiting 10 seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(10)
                    else:
                        raise
            
        except Exception as e:
            print(f"  ✗ Error clearing {table_name}: {str(e)}")
    
    print("\n✓ Data cleanup complete!")

if __name__ == "__main__":
    clear_all_data()
