"""
Start handler for user registration and main menu with Guest Mode support
"""

import logging
import random
import string
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User
from utils.i18n import _
from utils.keyboards import get_main_menu_keyboard, get_registration_keyboard
from utils.auth import is_guest_mode, create_audit_log, is_super_admin
from config import CUSTOMER_ID_PREFIX, CUSTOMER_ID_YEAR_FORMAT, DEFAULT_LANGUAGE, DEFAULT_CURRENCY, ADMINS

logger = logging.getLogger(__name__)
router = Router()

def generate_customer_code() -> str:
    """Generate unique customer code"""
    year = CUSTOMER_ID_YEAR_FORMAT
    random_part = ''.join(random.choices(string.digits, k=6))
    return f"{CUSTOMER_ID_PREFIX}{year}{random_part}"

@router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession):
    """Handle /start command - registration or welcome back with Guest Mode support"""
    try:
        user_id = message.from_user.id
        
        # Check if user exists
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Existing user - welcome back
            if user.is_blocked:
                await message.answer(_("account_blocked", user.language))
                return
                
            await message.answer(
                _("welcome_back", user.language, name=user.name or message.from_user.full_name),
                reply_markup=get_main_menu_keyboard(user.language, user.is_registered)
            )
        else:
            # New user - offer registration or guest mode
            await message.answer(
                _("welcome_new_user", DEFAULT_LANGUAGE),
                reply_markup=get_registration_keyboard(DEFAULT_LANGUAGE)
            )
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer(_("error", DEFAULT_LANGUAGE))

@router.callback_query(F.data == "register")
async def register_user(callback: CallbackQuery, session: AsyncSession):
    """Handle user registration"""
    try:
        user_id = callback.from_user.id
        
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            if existing_user.is_registered:
                await callback.answer(_("already_registered", existing_user.language))
                return
            else:
                # Update existing guest user to registered
                existing_user.is_registered = True
                existing_user.name = callback.from_user.full_name
                await session.commit()
                
                await callback.message.edit_text(
                    _("registration_complete", existing_user.language, code=existing_user.customer_code),
                    reply_markup=None
                )
                await callback.message.answer(
                    _("welcome_registered", existing_user.language),
                    reply_markup=get_main_menu_keyboard(existing_user.language, True)
                )
                return
        
        # Create new registered user
        customer_code = generate_customer_code()
        
        # Ensure unique customer code
        while True:
            existing = await session.execute(
                select(User).where(User.customer_code == customer_code)
            )
            if not existing.scalar_one_or_none():
                break
            customer_code = generate_customer_code()
        
        # Check if user is super admin
        is_admin = await is_super_admin(user_id)
        
        new_user = User(
            telegram_id=user_id,
            customer_code=customer_code,
            name=callback.from_user.full_name,
            language=DEFAULT_LANGUAGE,
            currency=DEFAULT_CURRENCY,
            is_registered=True,
            is_admin=is_admin
        )
        
        session.add(new_user)
        await session.commit()
        
        # Create audit log for user creation
        await create_audit_log(
            session, user_id, "create_user", "user", new_user.id,
            before=None,
            after={"telegram_id": user_id, "customer_code": customer_code, "registered": True}
        )
        
        await callback.message.edit_text(
            _("registration_complete", DEFAULT_LANGUAGE, code=customer_code),
            reply_markup=None
        )
        await callback.message.answer(
            _("welcome_registered", DEFAULT_LANGUAGE),
            reply_markup=get_main_menu_keyboard(DEFAULT_LANGUAGE, True)
        )
        
    except Exception as e:
        logger.error(f"Error in register_user: {e}")
        await callback.answer(_("error", DEFAULT_LANGUAGE))

@router.callback_query(F.data == "guest_mode")
async def guest_mode(callback: CallbackQuery, session: AsyncSession):
    """Handle guest mode entry"""
    try:
        user_id = callback.from_user.id
        
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create guest user
            customer_code = generate_customer_code()
            
            # Ensure unique customer code
            while True:
                existing = await session.execute(
                    select(User).where(User.customer_code == customer_code)
                )
                if not existing.scalar_one_or_none():
                    break
                customer_code = generate_customer_code()
            
            user = User(
                telegram_id=user_id,
                customer_code=customer_code,
                name=callback.from_user.full_name,
                language=DEFAULT_LANGUAGE,
                currency=DEFAULT_CURRENCY,
                is_registered=False  # Guest mode
            )
            
            session.add(user)
            await session.commit()
        
        await callback.message.edit_text(
            _("guest_mode_welcome", user.language),
            reply_markup=None
        )
        await callback.message.answer(
            _("guest_mode_info", user.language),
            reply_markup=get_main_menu_keyboard(user.language, False)  # Guest menu
        )
        
    except Exception as e:
        logger.error(f"Error in guest_mode: {e}")
        await callback.answer(_("error", DEFAULT_LANGUAGE))

@router.message(F.text.in_(["👤 حسابي", "👤 My Account"]))
async def my_account_handler(message: Message, session: AsyncSession):
    """Handle My Account button"""
    try:
        user_id = message.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("please_start", DEFAULT_LANGUAGE))
            return
        
        # Show account information
        account_text = _("account_info", user.language,
                        name=user.name or "غير محدد / Not specified",
                        customer_code=user.customer_code,
                        language=user.language.upper(),
                        currency=user.currency,
                        status=_("registered", user.language) if user.is_registered else _("guest", user.language))
        
        # Add registration option for guests
        keyboard = None
        if not user.is_registered:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("register_now", user.language), callback_data="register")]
            ])
        
        await message.answer(account_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in my account handler: {e}")
        await message.answer(_("error", DEFAULT_LANGUAGE))

@router.message(F.text.in_(["♻️ إعادة تعيين", "♻️ Reset"]))
async def reset_handler(message: Message, session: AsyncSession):
    """Handle Reset button"""
    try:
        user_id = message.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("please_start", DEFAULT_LANGUAGE))
            return
        
        await message.answer(
            _("reset_complete", user.language),
            reply_markup=get_main_menu_keyboard(user.language, user.is_registered)
        )
        
    except Exception as e:
        logger.error(f"Error in reset handler: {e}")
        await message.answer(_("error", DEFAULT_LANGUAGE))