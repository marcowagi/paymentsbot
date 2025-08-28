"""
Complaints handler for user complaints system with Guest Mode support
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Complaint, ComplaintStatus
from utils.i18n import _
from utils.keyboards import get_cancel_keyboard, get_main_menu_keyboard
from utils.states import ComplaintStates
from utils.auth import is_guest_mode, create_audit_log
from config import ADMINS

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text.in_(["📩 شكوى", "📩 Complaint"]))
async def complaint_start_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle complaint initiation with guest mode check"""
    try:
        user_id = message.from_user.id
        
        # Check if user is in guest mode
        if await is_guest_mode(session, user_id):
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            lang = user.language if user else "ar"
            
            # Offer registration
            register_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("register_now", lang), callback_data="register")]
            ])
            
            await message.answer(
                _("guest_restriction", lang),
                reply_markup=register_keyboard
            )
            return
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("please_start"))
            return
        
        await state.set_state(ComplaintStates.waiting_for_text)
        
        await message.answer(
            _("complaint_text", user.language),
            reply_markup=get_cancel_keyboard(user.language)
        )
        
    except Exception as e:
        logger.error(f"Error in complaint start handler: {e}")
        await message.answer(_("error"))

@router.message(ComplaintStates.waiting_for_text)
async def complaint_text_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle complaint text input"""
    try:
        user_id = message.from_user.id
        complaint_text = message.text.strip()
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("please_start"))
            return
        
        # Handle cancel
        if complaint_text in ["❌ إلغاء", "❌ Cancel"]:
            await state.clear()
            await message.answer(
                _("cancelled", user.language),
                reply_markup=get_main_menu_keyboard(user.language, user.is_registered)
            )
            return
        
        # Validate complaint text
        if len(complaint_text) < 10:
            await message.answer(
                "الشكوى قصيرة جداً. يرجى كتابة تفاصيل أكثر." if user.language == "ar" else "Complaint is too short. Please provide more details.",
                reply_markup=get_cancel_keyboard(user.language)
            )
            return
        
        # Create complaint
        new_complaint = Complaint(
            user_id=user.id,
            text=complaint_text,
            status=ComplaintStatus.pending
        )
        
        session.add(new_complaint)
        await session.commit()
        
        # Create audit log
        await create_audit_log(
            session, user_id, "create_complaint", "complaint", new_complaint.id,
            before=None,
            after={"text": complaint_text[:100] + "..." if len(complaint_text) > 100 else complaint_text, "status": ComplaintStatus.pending.value}
        )
        
        await state.clear()
        
        await message.answer(
            _("complaint_submitted", user.language, complaint_id=new_complaint.id),
            reply_markup=get_main_menu_keyboard(user.language, user.is_registered)
        )
        
        # Notify admins
        await notify_admins_new_complaint(message.bot, new_complaint, user)
        
    except Exception as e:
        logger.error(f"Error in complaint text handler: {e}")
        await message.answer(_("error"))

async def notify_admins_new_complaint(bot, complaint: Complaint, user: User):
    """Notify admins about new complaint"""
    try:
        complaint_preview = complaint.text[:200] + "..." if len(complaint.text) > 200 else complaint.text
        
        notification_text = (
            f"💬 شكوى جديدة / New Complaint\n\n"
            f"👤 المستخدم / User: {user.name} ({user.customer_code})\n"
            f"🆔 رقم الشكوى / Complaint ID: {complaint.id}\n"
            f"⏰ التاريخ / Date: {complaint.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"📝 النص / Text:\n{complaint_preview}"
        )
        
        for admin_id in ADMINS:
            try:
                await bot.send_message(admin_id, notification_text)
            except Exception as e:
                logger.warning(f"Failed to notify admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error notifying admins: {e}")
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