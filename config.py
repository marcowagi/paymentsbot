"""
Configuration module for the Telegram Finance Bot
Loads environment variables and provides configuration settings
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Admin Configuration
ADMINS_STR = os.getenv("ADMINS", "")
ADMINS = [int(admin_id.strip()) for admin_id in ADMINS_STR.split(",") if admin_id.strip().isdigit()]

# Support Configuration
SUPPORT_CHANNELS_STR = os.getenv("SUPPORT_CHANNELS", "")
SUPPORT_CHANNELS = [channel.strip() for channel in SUPPORT_CHANNELS_STR.split(",") if channel.strip()]

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/db.sqlite3")

# Ensure data directory exists
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Localization Configuration
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ar")

# Customer ID Configuration
CUSTOMER_ID_PREFIX = os.getenv("CUSTOMER_ID_PREFIX", "C")
CUSTOMER_ID_YEAR_FORMAT = os.getenv("CUSTOMER_ID_YEAR_FORMAT", "2025")

# Broadcast Configuration
BROADCAST_RATE_LIMIT = int(os.getenv("BROADCAST_RATE_LIMIT", "30"))
BROADCAST_CHUNK_SIZE = int(os.getenv("BROADCAST_CHUNK_SIZE", "100"))
BROADCAST_RETRY_ATTEMPTS = int(os.getenv("BROADCAST_RETRY_ATTEMPTS", "3"))
BROADCAST_RETRY_DELAY = int(os.getenv("BROADCAST_RETRY_DELAY", "5"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Path Configuration
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TRANSLATIONS_DIR = BASE_DIR / "translations"
REPORTS_DIR = DATA_DIR / "reports"
BACKUPS_DIR = DATA_DIR / "backups"

# Ensure directories exist
for directory in [DATA_DIR, REPORTS_DIR, BACKUPS_DIR]:
    directory.mkdir(exist_ok=True, parents=True)