"""
Broadcast service for sending messages to multiple users with rate limiting
"""

import asyncio
import logging
from typing import List, Optional
from aiogram import Bot
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User
from config import BROADCAST_RATE_LIMIT, BROADCAST_CHUNK_SIZE, BROADCAST_RETRY_ATTEMPTS, BROADCAST_RETRY_DELAY

logger = logging.getLogger(__name__)

class BroadcastService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_broadcasting = False
        self.broadcast_queue = asyncio.Queue()
        
    async def start_worker(self):
        """Start the broadcast worker"""
        while True:
            try:
                broadcast_data = await self.broadcast_queue.get()
                await self._process_broadcast(broadcast_data)
                self.broadcast_queue.task_done()
            except Exception as e:
                logger.error(f"Broadcast worker error: {e}")
                await asyncio.sleep(1)
    
    async def queue_broadcast(self, message: Message, user_ids: Optional[List[int]] = None):
        """Queue a broadcast message"""
        broadcast_data = {
            'message': message,
            'user_ids': user_ids,
            'timestamp': asyncio.get_event_loop().time()
        }
        await self.broadcast_queue.put(broadcast_data)
        logger.info(f"Queued broadcast message for {len(user_ids) if user_ids else 'all'} users")
    
    async def _process_broadcast(self, broadcast_data: dict):
        """Process a broadcast message"""
        message = broadcast_data['message']
        user_ids = broadcast_data['user_ids']
        
        try:
            self.is_broadcasting = True
            
            if user_ids is None:
                # Broadcast to all users - get from database
                async with AsyncSession() as session:
                    result = await session.execute(
                        select(User.telegram_id).where(User.is_registered == True)
                    )
                    user_ids = [row[0] for row in result.fetchall()]
            
            if not user_ids:
                logger.warning("No users to broadcast to")
                return
            
            logger.info(f"Starting broadcast to {len(user_ids)} users")
            
            # Process in chunks to avoid overwhelming the API
            success_count = 0
            failed_count = 0
            
            for i in range(0, len(user_ids), BROADCAST_CHUNK_SIZE):
                chunk = user_ids[i:i + BROADCAST_CHUNK_SIZE]
                chunk_success, chunk_failed = await self._broadcast_chunk(message, chunk)
                success_count += chunk_success
                failed_count += chunk_failed
                
                # Rate limiting between chunks
                if i + BROADCAST_CHUNK_SIZE < len(user_ids):
                    await asyncio.sleep(BROADCAST_RATE_LIMIT)
            
            logger.info(f"Broadcast completed: {success_count} success, {failed_count} failed")
            
        except Exception as e:
            logger.error(f"Broadcast processing error: {e}")
        finally:
            self.is_broadcasting = False
    
    async def _broadcast_chunk(self, message: Message, user_ids: List[int]) -> tuple[int, int]:
        """Broadcast to a chunk of users"""
        success_count = 0
        failed_count = 0
        
        # Create tasks for concurrent sending
        tasks = []
        for user_id in user_ids:
            task = self._send_message_to_user(message, user_id)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
            else:
                success_count += 1
        
        return success_count, failed_count
    
    async def _send_message_to_user(self, message: Message, user_id: int) -> bool:
        """Send message to a single user with retry logic"""
        for attempt in range(BROADCAST_RETRY_ATTEMPTS):
            try:
                if message.text:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=message.text,
                        parse_mode=message.parse_mode,
                        reply_markup=message.reply_markup
                    )
                elif message.photo:
                    await self.bot.send_photo(
                        chat_id=user_id,
                        photo=message.photo[-1].file_id,
                        caption=message.caption,
                        parse_mode=message.parse_mode,
                        reply_markup=message.reply_markup
                    )
                elif message.video:
                    await self.bot.send_video(
                        chat_id=user_id,
                        video=message.video.file_id,
                        caption=message.caption,
                        parse_mode=message.parse_mode,
                        reply_markup=message.reply_markup
                    )
                elif message.document:
                    await self.bot.send_document(
                        chat_id=user_id,
                        document=message.document.file_id,
                        caption=message.caption,
                        parse_mode=message.parse_mode,
                        reply_markup=message.reply_markup
                    )
                else:
                    # Copy the message as-is
                    await message.copy_to(chat_id=user_id)
                
                return True
                
            except Exception as e:
                logger.warning(f"Failed to send message to user {user_id} (attempt {attempt + 1}): {e}")
                if attempt < BROADCAST_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(BROADCAST_RETRY_DELAY * (attempt + 1))
        
        return False
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.broadcast_queue.qsize()
    
    def is_busy(self) -> bool:
        """Check if broadcasting is in progress"""
        return self.is_broadcasting or not self.broadcast_queue.empty()