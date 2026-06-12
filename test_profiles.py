from app.adapters.bq_adapter import BigQueryAdapter
from app.utils.config import (
    PROJECT_ID,
    TARGET_DATASET
)

bq = BigQueryAdapter(
    PROJECT_ID
)

profiles = bq.get_numeric_profiles(
    TARGET_DATASET,
    "marketing_campaigns"
)

print(profiles)