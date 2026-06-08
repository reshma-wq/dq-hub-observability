from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
TARGET_DATASET = os.getenv("TARGET_DATASET")

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "publishers/google/models/gemini-3.5-flash"
)