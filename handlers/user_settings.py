"""
User settings handler for language change, currency change, support, and reset with Guest Mode support
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, SupportChannel
from utils.i18n import _
from utils.keyboards import get_language_keyboard, get_currency_keyboard, get_main_menu_keyboard
from utils.auth import is_guest_mode, create_audit_log
from config import SUPPORT_CHANNELS, SUPPORTED_LANGUAGES
from db import init_db

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text.in_(["🌐 تغيير اللغة", "🌐 Change Language"]))
async def change_language_handler(message: Message, session: AsyncSession):
    """Handle language change request"""
    try:
        user_id = message.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        lang = user.language if user else "ar"
        
        await message.answer(
            _("select_language", lang),
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
        
        # Validate language
        if lang_code not in SUPPORTED_LANGUAGES:
            await callback.answer(_("error"))
            return
        
        # Update user language in database
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            old_language = user.language
            user.language = lang_code
            await session.commit()
            
            # Create audit log
            await create_audit_log(
                session, user_id, "change_language", "user", user.id,
                before={"language": old_language},
                after={"language": lang_code}
            )
            
            await callback.message.edit_text(
                _("language_changed", lang_code)
            )
            
            # Send new main menu with updated language
            await callback.message.answer(
                _("main_menu", lang_code),
                reply_markup=get_main_menu_keyboard(lang_code, user.is_registered)
            )
        else:
            await callback.message.edit_text(_("error"))
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in language callback handler: {e}")
        await callback.answer(_("error"))

@router.message(F.text.in_(["🔄 تغيير العملة", "🔄 Change Currency"]))
async def change_currency_handler(message: Message, session: AsyncSession):
    """Handle currency change request"""
    try:
        user_id = message.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("please_start"))
            return
            
        await message.answer(
            _("select_currency", user.language),
            reply_markup=get_currency_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in change currency handler: {e}")
        await message.answer(_("error"))

@router.callback_query(F.data.startswith("currency_"))
async def currency_callback_handler(callback: CallbackQuery, session: AsyncSession):
    """Handle currency selection callback"""
    try:
        currency_code = callback.data.split("_")[1]
        user_id = callback.from_user.id
        
        # Update user currency in database
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            old_currency = user.currency
            user.currency = currency_code
            await session.commit()
            
            # Create audit log
            await create_audit_log(
                session, user_id, "change_currency", "user", user.id,
                before={"currency": old_currency},
                after={"currency": currency_code}
            )
            
            await callback.message.edit_text(
                _("currency_changed", user.language)
            )
        else:
            await callback.message.edit_text(_("error"))
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in currency callback handler: {e}")
        await callback.answer(_("error"))

@router.message(F.text.in_(["🆘 دعم", "🆘 Support"]))
async def support_handler(message: Message, session: AsyncSession):
    """Handle support request"""
    try:
        user_id = message.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        lang = user.language if user else "ar"
        
        # Get support channels from database first, fallback to config
        db_channels_result = await session.execute(
            select(SupportChannel).where(SupportChannel.is_active == True)
        )
        db_channels = db_channels_result.scalars().all()
        
        support_text = _("support_info", lang)
        
        if db_channels:
            for channel in db_channels:
                if channel.kind.value == "telegram":
                    support_text += f"\n📱 Telegram: {channel.value}"
                elif channel.kind.value == "whatsapp":
                    support_text += f"\n📞 WhatsApp: {channel.value}"
                elif channel.kind.value == "email":
                    support_text += f"\n📧 Email: {channel.value}"
                elif channel.kind.value == "website":
                    support_text += f"\n🌐 Website: {channel.value}"
        elif SUPPORT_CHANNELS:
            # Fallback to config
            for channel in SUPPORT_CHANNELS:
                support_text += f"\n{channel}"
        else:
            support_text = "Support channels not configured" if lang == "en" else "قنوات الدعم غير مكونة"
        
        await message.answer(support_text)
        
    except Exception as e:
        logger.error(f"Error in support handler: {e}")
        await message.answer(_("error"))

@router.message(F.text.in_(["♻️ إعادة تعيين", "♻️ Reset"]))
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
            reset_text = f"Reset completed with database issues: {db_error}" if lang == "en" else f"تم إعادة التعيين مع مشاكل في قاعدة البيانات: {db_error}"
        
        await message.answer(
            reset_text,
            reply_markup=get_main_menu_keyboard(lang, user.is_registered if user else False)
        )
        
    except Exception as e:
        logger.error(f"Error in reset handler: {e}")
        await message.answer(_("error"))