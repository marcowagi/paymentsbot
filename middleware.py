"""
Session middleware for the Telegram Finance Bot
Provides database session and broadcast service to handlers
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession
from db import SessionMaker
from services.broadcast_service import BroadcastService

logger = logging.getLogger(__name__)

class SessionMiddleware(BaseMiddleware):
    """Middleware that provides database session and services to handlers"""
    
    def __init__(self, session_maker, broadcast_service: BroadcastService):
        self.session_maker = session_maker
        self.broadcast_service = broadcast_service
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            # Create database session
            async with self.session_maker() as session:
                # Add session and services to handler data
                data["session"] = session
                data["broadcast_service"] = self.broadcast_service
                
                # Call the handler
                result = await handler(event, data)
                
                # Commit the session
                await session.commit()
                return result
                
        except Exception as e:
            logger.error(f"Session middleware error: {e}")
            # Rollback on error
            if "session" in data:
                await data["session"].rollback()
            raise