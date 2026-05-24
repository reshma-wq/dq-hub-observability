from app.adapters.bq_adapter import BigQueryAdapter
from app.utils.config import PROJECT_ID, TARGET_DATASET


class DashboardService:

    def __init__(self):

        self.bq = BigQueryAdapter(PROJECT_ID)

    def get_summary(self):

        return self.bq.get_dashboard_summary(
            TARGET_DATASET
        )

    def get_latest_results(self):

        return self.bq.get_latest_results(
            TARGET_DATASET
        )

    def get_table_details(self,table_name):
        return self.bq.get_table_details(
            "thd_bronze",
            table_name
        )