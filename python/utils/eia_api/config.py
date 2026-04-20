"""Shared configuration for EIA API endpoints."""

import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / "python" / ".env")

# API Configuration
API_KEY = os.getenv("EIA_API_KEY")
BASE_URL = "https://api.eia.gov/v2"

# File paths
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "eia.db"

# API request settings
BATCH_SIZE = 5000
REQUEST_TIMEOUT = 60