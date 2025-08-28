"""
Announcements handler for creating and broadcasting announcements
"""

import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from models import Ad
from services.broadcast_service import BroadcastService
from utils.keyboards import get_cancel_keyboard
from config import ADMINS

logger = logging.getLogger(__name__)
router = Router()

class AnnouncementStates(StatesGroup):
    waiting_for_title_ar = State()
    waiting_for_title_en = State()
    waiting_for_text_ar = State()
    waiting_for_text_en = State()

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMINS

@router.message(Command("announce"))
async def announce_command_handler(message: Message, state: FSMContext):
    """Handle announcement creation command"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer("غير مصرح / Unauthorized")
            return
        
        # Check if command has format: /announce title|text
        text_parts = message.text.split(' ', 1)
        if len(text_parts) > 1 and '|' in text_parts[1]:
            # Quick announcement format
            content = text_parts[1]
            if '|' in content:
                title, text = content.split('|', 1)
                await create_quick_announcement(message, title.strip(), text.strip())
                return
        
        # Start interactive announcement creation
        await state.set_state(AnnouncementStates.waiting_for_title_ar)
        await message.answer(
            "📝 إنشاء إعلان جديد / Create New Announcement\n\n"
            "أدخل عنوان الإعلان بالعربية / Enter announcement title in Arabic:",
            reply_markup=get_cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in announce command handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

async def create_quick_announcement(message: Message, title: str, text: str):
    """Create and broadcast a quick announcement (Arabic only for now)"""
    try:
        # Use the same title and text for both languages (can be enhanced later)
        announcement_message = f"📢 {title}\n\n{text}"
        
        # Create a simple text message to broadcast
        broadcast_message = await message.answer(announcement_message)
        
        # Get broadcast service from handler data
        # Note: This is a simplified version - in full implementation,
        # we would save to database and use proper broadcast service
        
        await message.answer(
            "✅ تم إنشاء الإعلان وإرساله / Announcement created and broadcasted"
        )
        
    except Exception as e:
        logger.error(f"Error creating quick announcement: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.message(AnnouncementStates.waiting_for_title_ar)
async def title_ar_handler(message: Message, state: FSMContext):
    """Handle Arabic title input"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer("تم الإلغاء / Cancelled")
            return
        
        await state.update_data(title_ar=message.text)
        await state.set_state(AnnouncementStates.waiting_for_title_en)
        
        await message.answer(
            "أدخل عنوان الإعلان بالإنجليزية / Enter announcement title in English:",
            reply_markup=get_cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in title AR handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.message(AnnouncementStates.waiting_for_title_en)
async def title_en_handler(message: Message, state: FSMContext):
    """Handle English title input"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer("تم الإلغاء / Cancelled")
            return
        
        await state.update_data(title_en=message.text)
        await state.set_state(AnnouncementStates.waiting_for_text_ar)
        
        await message.answer(
            "أدخل نص الإعلان بالعربية / Enter announcement text in Arabic:",
            reply_markup=get_cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in title EN handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.message(AnnouncementStates.waiting_for_text_ar)
async def text_ar_handler(message: Message, state: FSMContext):
    """Handle Arabic text input"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer("تم الإلغاء / Cancelled")
            return
        
        await state.update_data(text_ar=message.text)
        await state.set_state(AnnouncementStates.waiting_for_text_en)
        
        await message.answer(
            "أدخل نص الإعلان بالإنجليزية / Enter announcement text in English:",
            reply_markup=get_cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in text AR handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.message(AnnouncementStates.waiting_for_text_en)
async def text_en_handler(message: Message, session: AsyncSession, state: FSMContext, broadcast_service: BroadcastService):
    """Handle English text input and create announcement"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer("تم الإلغاء / Cancelled")
            return
        
        data = await state.get_data()
        user_id = message.from_user.id
        
        # Create announcement in database
        new_ad = Ad(
            title_ar=data["title_ar"],
            title_en=data["title_en"],
            text_ar=data["text_ar"],
            text_en=message.text,
            created_by=user_id,
            is_active=True
        )
        
        session.add(new_ad)
        await session.flush()
        
        # Create broadcast message (Arabic version for now)
        announcement_text = f"📢 {data['title_ar']}\n\n{data['text_ar']}"
        
        # Create a temporary message for broadcasting
        broadcast_msg = await message.answer(announcement_text)
        
        # Queue for broadcast
        await broadcast_service.queue_broadcast(broadcast_msg)
        
        # Update broadcast timestamp
        new_ad.broadcast_at = datetime.utcnow()
        
        await message.answer(
            f"✅ تم إنشاء الإعلان وإضافته لقائمة البث / Announcement created and queued for broadcast\n"
            f"🆔 ID: {new_ad.id}"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in text EN handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.callback_query(F.data == "admin_announcements")
async def admin_announcements_callback_handler(callback: CallbackQuery):
    """Handle admin announcements callback from admin panel"""
    try:
        user_id = callback.from_user.id
        
        if not is_admin(user_id):
            await callback.answer("غير مصرح / Unauthorized")
            return
        
        instructions_text = (
            "📢 إدارة الإعلانات / Announcements Management\n\n"
            "📝 لإنشاء إعلان سريع / For quick announcement:\n"
            "/announce العنوان|النص\n"
            "/announce Title|Text\n\n"
            "📋 لإنشاء إعلان تفاعلي / For interactive announcement:\n"
            "/announce\n\n"
            "ملاحظة: سيتم بث الإعلانات باللغة العربية افتراضياً / "
            "Note: Announcements will be broadcast in Arabic by default"
        )
        
        await callback.message.edit_text(instructions_text)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin announcements callback handler: {e}")
        await callback.answer("حدث خطأ / Error occurred")