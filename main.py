"""
Main Aiogram v3 application for the Telegram Finance Bot
Handles bot initialization and startup
"""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from db import SessionMaker, init_db
from services.broadcast_service import BroadcastService
from middleware import SessionMiddleware
from handlers import setup_handlers

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

async def main():
    """Main application entry point"""
    try:
        logger.info("Starting Telegram Finance Bot...")
        
        # Initialize bot and dispatcher
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        
        # Initialize broadcast service
        broadcast_service = BroadcastService(bot)
        
        # Setup middleware
        session_middleware = SessionMiddleware(SessionMaker, broadcast_service)
        dp.message.middleware(session_middleware)
        dp.callback_query.middleware(session_middleware)
        
        # Setup handlers
        router = setup_handlers()
        dp.include_router(router)
        
        # Delete webhook to ensure polling
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted, switching to polling")
        
        # Start broadcast worker
        asyncio.create_task(broadcast_service.start_worker())
        logger.info("Broadcast service worker started")
        
        # Start polling
        logger.info("Bot started successfully. Press Ctrl+C to stop.")
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())