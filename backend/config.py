
from pathlib import Path
import os
from dotenv import load_dotenv

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
