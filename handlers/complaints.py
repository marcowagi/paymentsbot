"""
Complaints handler for user complaints system
"""

import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Complaint
from utils.i18n import _
from utils.keyboards import get_cancel_keyboard, get_main_menu_keyboard
from config import ADMINS

logger = logging.getLogger(__name__)
router = Router()

class ComplaintStates(StatesGroup):
    waiting_for_complaint = State()

@router.message(F.text.in_(["شكوى", "Complaint", "تقديم شكوى", "Submit Complaint"]))
async def complaint_start_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle complaint initiation"""
    try:
        user_id = message.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("error"))
            return
        
        await state.set_state(ComplaintStates.waiting_for_complaint)
        await state.update_data(user_lang=user.language)
        
        await message.answer(
            _("complaint_text", user.language),
            reply_markup=get_cancel_keyboard(user.language)
        )
        
    except Exception as e:
        logger.error(f"Error in complaint start handler: {e}")
        await message.answer(_("error"))

@router.message(ComplaintStates.waiting_for_complaint)
async def complaint_text_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle complaint text input"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer(
                _("cancelled"),
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        user_id = message.from_user.id
        data = await state.get_data()
        user_lang = data.get("user_lang", "ar")
        
        # Get user
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("error"))
            return
        
        # Create complaint
        new_complaint = Complaint(
            user_id=user.id,
            message=message.text,
            status="pending"
        )
        
        session.add(new_complaint)
        await session.flush()
        
        await message.answer(
            _("complaint_submitted", user_lang),
            reply_markup=get_main_menu_keyboard(user_lang)
        )
        
        # Notify admins
        await notify_admins_new_complaint(message.bot, new_complaint, user)
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in complaint text handler: {e}")
        await message.answer(_("error"))

async def notify_admins_new_complaint(bot, complaint: Complaint, user: User):
    """Notify admins about new complaint"""
    try:
        notification_text = (
            f"📢 شكوى جديدة / New Complaint\n\n"
            f"👤 User: {user.name} ({user.customer_code})\n"
            f"📝 Message: {complaint.message}\n"
            f"🆔 Complaint ID: {complaint.id}\n"
            f"⏰ Time: {complaint.created_at}"
        )
        
        for admin_id in ADMINS:
            try:
                await bot.send_message(admin_id, notification_text)
            except Exception as e:
                logger.warning(f"Failed to notify admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error notifying admins about complaint: {e}")