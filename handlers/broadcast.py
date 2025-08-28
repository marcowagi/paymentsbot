"""
Broadcast handler for admin message broadcasting
"""

import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from services.broadcast_service import BroadcastService
from config import ADMINS

logger = logging.getLogger(__name__)
router = Router()

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMINS

@router.message(Command("broadcast"))
async def broadcast_command_handler(message: Message, broadcast_service: BroadcastService):
    """Handle broadcast command - must be a reply to a message"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer("غير مصرح / Unauthorized")
            return
        
        if not message.reply_to_message:
            await message.answer(
                "يجب أن يكون هذا الأمر رداً على رسالة لبثها / "
                "This command must be a reply to a message to broadcast it"
            )
            return
        
        # Check if broadcast service is busy
        if broadcast_service.is_busy():
            await message.answer(
                f"⏳ جاري البث... العدد في الانتظار: {broadcast_service.get_queue_size()}\n"
                f"⏳ Broadcasting in progress... Queue size: {broadcast_service.get_queue_size()}"
            )
            return
        
        # Queue the message for broadcast
        await broadcast_service.queue_broadcast(message.reply_to_message)
        
        await message.answer(
            "✅ تم إضافة الرسالة إلى قائمة البث / Message queued for broadcast"
        )
        
    except Exception as e:
        logger.error(f"Error in broadcast command handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_callback_handler(callback, broadcast_service: BroadcastService):
    """Handle admin broadcast callback from admin panel"""
    try:
        user_id = callback.from_user.id
        
        if not is_admin(user_id):
            await callback.answer("غير مصرح / Unauthorized")
            return
        
        # Show broadcast status
        if broadcast_service.is_busy():
            status_text = (
                f"⏳ جاري البث / Broadcasting in progress\n"
                f"📊 العدد في الانتظار / Queue size: {broadcast_service.get_queue_size()}"
            )
        else:
            status_text = (
                "✅ نظام البث جاهز / Broadcast system ready\n\n"
                "📝 لبث رسالة، قم بالرد عليها بالأمر / To broadcast a message, reply to it with:\n"
                "/broadcast"
            )
        
        await callback.message.edit_text(status_text)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin broadcast callback handler: {e}")
        await callback.answer("حدث خطأ / Error occurred")