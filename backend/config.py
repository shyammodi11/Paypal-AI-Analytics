
from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# Ensure UTF-8 output encoding across Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Project root
PROJECT_DIR = Path(__file__).resolve().parents[1]

# Load environment variables from project root
load_dotenv(PROJECT_DIR / ".env")

# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

# PayPal Sandbox configuration
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_BASE_URL = os.getenv(
    "PAYPAL_BASE_URL",
    "https://api-m.sandbox.paypal.com"
)

# Data directories
DATA_DIR = PROJECT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CHECKPOINT_DIR = PROCESSED_DATA_DIR / "checkpoints"

# Consolidated review dataset
CLASSIFIED_REVIEWS_FILE = (
    PROCESSED_DATA_DIR / "classified_reviews_stage1.csv"
)

# SQLite database
DATABASE_PATH = (
    PROCESSED_DATA_DIR / "paypal_sentinel.db"
)

# Ensure required directories exist
for directory in [
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    CHECKPOINT_DIR
]:
    directory.mkdir(parents=True, exist_ok=True)
