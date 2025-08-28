"""
Run script for the Telegram Finance Bot
Initializes database and then launches the main application
"""

import asyncio
import logging
import sys
from pathlib import Path
from db import init_db
from main import main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def startup():
    """Startup sequence: initialize database, then start bot"""
    try:
        logger.info("=== Telegram Finance Bot Startup ===")
        
        # Ensure data directory exists
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        logger.info("Data directory ensured")
        
        # Initialize database
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized successfully")
        
        # Start the main application
        logger.info("Starting bot application...")
        await main()
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(startup())