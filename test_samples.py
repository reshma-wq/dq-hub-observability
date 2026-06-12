from app.adapters.bq_adapter import BigQueryAdapter
from app.utils.config import (
    PROJECT_ID,
    TARGET_DATASET
)

bq = BigQueryAdapter(
    PROJECT_ID
)

samples = bq.get_column_samples(
    TARGET_DATASET,
    "marketing_campaigns"
)

print(samples)