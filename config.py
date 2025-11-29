import os
from pathlib import Path

# Absolute path to project root
BASE_DIR = Path(__file__).resolve().parent

# Define where photos live
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Define Base URL (In prod, read from env var)
BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")