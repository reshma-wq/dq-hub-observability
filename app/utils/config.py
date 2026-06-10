from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")
TARGET_DATASET = os.getenv("TARGET_DATASET")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Validate required configs
if not PROJECT_ID:
    raise ValueError("PROJECT_ID is not set in environment variables")
if not TARGET_DATASET:
    raise ValueError("TARGET_DATASET is not set in environment variables")
if not GOOGLE_APPLICATION_CREDENTIALS:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is not set in environment variables")