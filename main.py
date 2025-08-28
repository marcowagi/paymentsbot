"""
Main Aiogram v3 application for the Telegram Finance Bot
Handles bot initialization and startup with support for both polling and webhook modes
"""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from config import BOT_TOKEN, RUN_MODE, WEBHOOK_URL, WEBHOOK_SECRET_TOKEN, WEBHOOK_PORT
from db import SessionMaker, init_db
from services.broadcast_service import BroadcastService
from middleware import SessionMiddleware
from handlers import setup_handlers
from utils.auth import ensure_default_roles

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

async def on_startup():
    """Initialize database and default data"""
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Initialize default roles
        async with SessionMaker() as session:
            await ensure_default_roles(session)
        logger.info("Default roles ensured")
        
    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")
        raise

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
        
        # Initialize startup tasks
        await on_startup()
        
        # Start broadcast worker
        asyncio.create_task(broadcast_service.start_worker())
        logger.info("Broadcast service worker started")
        
        if RUN_MODE.lower() == "webhook":
            # Webhook mode
            if not WEBHOOK_URL:
                raise ValueError("WEBHOOK_URL is required for webhook mode")
                
            logger.info(f"Starting in webhook mode on port {WEBHOOK_PORT}")
            
            # Set webhook
            await bot.set_webhook(
                url=WEBHOOK_URL,
                secret_token=WEBHOOK_SECRET_TOKEN if WEBHOOK_SECRET_TOKEN else None,
                drop_pending_updates=True
            )
            logger.info(f"Webhook set to {WEBHOOK_URL}")
            
            # Create aiohttp application
            app = web.Application()
            
            # Setup webhook handler
            webhook_requests_handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
                secret_token=WEBHOOK_SECRET_TOKEN if WEBHOOK_SECRET_TOKEN else None,
            )
            webhook_requests_handler.register(app, path="/webhook")
            
            # Setup application
            setup_application(app, dp, bot=bot)
            
            # Start server
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host="0.0.0.0", port=WEBHOOK_PORT)
            await site.start()
            
            logger.info("Bot started successfully in webhook mode. Press Ctrl+C to stop.")
            
            # Keep running
            try:
                await asyncio.Future()  # Run forever
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
            finally:
                await runner.cleanup()
                
        else:
            # Polling mode
            logger.info("Starting in polling mode")
            
            # Delete webhook to ensure polling
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted, switching to polling")
            
            # Start polling
            logger.info("Bot started successfully. Press Ctrl+C to stop.")
            await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if 'bot' in locals():
            await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())