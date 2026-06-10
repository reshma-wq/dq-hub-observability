from app.adapters.bq_adapter import BigQueryAdapter
from app.utils.config import PROJECT_ID, TARGET_DATASET
import logging

logger = logging.getLogger(__name__)


class DashboardService:

    def __init__(self):
        try:
            self.bq = BigQueryAdapter(PROJECT_ID)
            self.target_dataset = TARGET_DATASET
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery: {str(e)}")
            raise

    def get_summary(self):
        try:
            return self.bq.get_dashboard_summary(
                self.target_dataset
            )
        except Exception as e:
            logger.error(f"Dashboard summary error: {str(e)}")
            # Return empty response instead of crashing
            return {
                "system_health": 0,
                "tables_monitored": 0,
                "open_incidents": 0,
                "last_scan": None,
                "tables": [],
                "error": str(e)
            }

    def get_latest_results(self):
        try:
            return self.bq.get_latest_results(
                self.target_dataset
            )
        except Exception as e:
            logger.error(f"Latest results error: {str(e)}")
            return []

    def get_table_details(self, table_name):
        try:
            return self.bq.get_table_details(
                self.target_dataset,
                table_name
            )
        except Exception as e:
            logger.error(f"Table details error for {table_name}: {str(e)}")
            return {"error": str(e), "table_name": table_name}