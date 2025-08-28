"""
User settings handler for language change, support, and reset
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User
from utils.i18n import _
from utils.keyboards import get_language_keyboard, get_main_menu_keyboard
from config import SUPPORT_CHANNELS
from db import init_db

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text.in_(["تغيير اللغة", "Change Language"]))
async def change_language_handler(message: Message, session: AsyncSession):
    """Handle language change request"""
    try:
        await message.answer(
            "اختر اللغة / Choose Language:",
            reply_markup=get_language_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in change language handler: {e}")
        await message.answer(_("error"))

@router.callback_query(F.data.startswith("lang_"))
async def language_callback_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Handle language selection callback"""
    try:
        lang_code = callback.data.split("_")[1]
        user_id = callback.from_user.id
        
        # Update user language in database
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.language = lang_code
            await session.flush()
            
            await callback.message.edit_text(
                _("language_changed", lang_code)
            )
            
            # Send new main menu with updated language
            await callback.message.answer(
                _("main_menu", lang_code),
                reply_markup=get_main_menu_keyboard(lang_code)
            )
        else:
            await callback.message.edit_text(_("error"))
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in language callback handler: {e}")
        await callback.answer(_("error"))

@router.message(F.text.in_(["الدعم", "Support"]))
async def support_handler(message: Message, session: AsyncSession):
    """Handle support request"""
    try:
        user_id = message.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        lang = user.language if user else "ar"
        
        if SUPPORT_CHANNELS:
            support_text = _("support_info", lang) if lang == "ar" else "For support, please contact:"
            for channel in SUPPORT_CHANNELS:
                support_text += f"\n{channel}"
        else:
            support_text = _("support_unavailable", lang) if lang == "ar" else "Support channels not configured"
        
        await message.answer(support_text)
        
    except Exception as e:
        logger.error(f"Error in support handler: {e}")
        await message.answer(_("error"))

@router.message(F.text.in_(["إعادة التعيين", "Reset"]))
async def reset_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle reset request - clear FSM state and check DB health"""
    try:
        user_id = message.from_user.id
        
        # Clear FSM state
        await state.clear()
        
        # Get user for language
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        lang = user.language if user else "ar"
        
        # Perform basic DB health check
        try:
            # Try to reinitialize database (will create tables if missing)
            await init_db()
            
            reset_text = _("reset_complete", lang)
            
        except Exception as db_error:
            logger.error(f"Database health check failed: {db_error}")
            reset_text = _("reset_error", lang) if lang == "ar" else f"Reset completed with database issues: {db_error}"
        
        await message.answer(
            reset_text,
            reply_markup=get_main_menu_keyboard(lang)
        )
        
    except Exception as e:
        logger.error(f"Error in reset handler: {e}")
        await message.answer(_("error"))