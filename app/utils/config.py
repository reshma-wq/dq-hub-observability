from dotenv import load_dotenv
import os
from google.cloud import secretmanager

load_dotenv()

def get_secret(secret_id):
    """Fetch secret from GCP Secret Manager"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        import google.auth
        _, project_id = google.auth.default()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"ERROR: Could not fetch {secret_id} from Secret Manager: {str(e)}")
        raise

# Fetch all secrets from GCP Secret Manager
PROJECT_ID = get_secret("PROJECT_ID")
LOCATION = get_secret("LOCATION")
TARGET_DATASET = get_secret("TARGET_DATASET")
DQ_HUB_DATASET = get_secret("DQ_HUB_DATASET")
EMAIL_SENDER = get_secret("EMAIL_SENDER")
EMAIL_PASSWORD = get_secret("EMAIL_PASSWORD")
EMAIL_RECIPIENT = get_secret("EMAIL_RECIPIENT")

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "publishers/google/models/gemini-3.5-flash"
)