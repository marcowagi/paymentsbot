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

# Admin Configuration - Super Admins from .env
ADMINS_STR = os.getenv("ADMINS", "")
ADMINS = [int(admin_id.strip()) for admin_id in ADMINS_STR.split(",") if admin_id.strip().isdigit()]

# Run Mode Configuration
RUN_MODE = os.getenv("RUN_MODE", "polling")  # polling or webhook
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8000"))

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/db.sqlite3")

# Localization Configuration
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ar")
SUPPORTED_LANGUAGES = os.getenv("SUPPORTED_LANGUAGES", "ar,en").split(",")

# Currency Configuration
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "SAR")

# Customer ID Configuration
CUSTOMER_ID_PREFIX = os.getenv("CUSTOMER_ID_PREFIX", "C")
CUSTOMER_ID_YEAR_FORMAT = os.getenv("CUSTOMER_ID_YEAR_FORMAT", "2025")

# Broadcast Configuration
BROADCAST_RATE_LIMIT = int(os.getenv("BROADCAST_RATE_LIMIT", "28"))
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
UPLOADS_DIR = DATA_DIR / "uploads"
ATTACHMENTS_DIR = DATA_DIR / "attachments"

# Ensure directories exist
for directory in [DATA_DIR, REPORTS_DIR, BACKUPS_DIR, UPLOADS_DIR, ATTACHMENTS_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

# File Upload Configuration
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default
ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,pdf").split(",")

# Support Configuration - Legacy support for old format
SUPPORT_CHANNELS_STR = os.getenv("SUPPORT_CHANNELS", "")
SUPPORT_CHANNELS = [channel.strip() for channel in SUPPORT_CHANNELS_STR.split(",") if channel.strip()]