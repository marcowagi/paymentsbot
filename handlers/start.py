"""
Start handler for user registration and main menu
"""

import logging
import random
import string
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User
from utils.i18n import _
from utils.keyboards import get_main_menu_keyboard
from config import CUSTOMER_ID_PREFIX, CUSTOMER_ID_YEAR_FORMAT, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)
router = Router()

def generate_customer_code() -> str:
    """Generate unique customer code"""
    year = CUSTOMER_ID_YEAR_FORMAT
    random_part = ''.join(random.choices(string.digits, k=6))
    return f"{CUSTOMER_ID_PREFIX}{year}{random_part}"

@router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession):
    """Handle /start command - registration or welcome back"""
    try:
        user_id = message.from_user.id
        
        # Check if user exists
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Existing user - welcome back
            await message.answer(
                _("welcome", user.language),
                reply_markup=get_main_menu_keyboard(user.language)
            )
        else:
            # New user - create with default settings
            customer_code = generate_customer_code()
            
            # Ensure unique customer code
            while True:
                existing = await session.execute(
                    select(User).where(User.customer_code == customer_code)
                )
                if not existing.scalar_one_or_none():
                    break
                customer_code = generate_customer_code()
            
            new_user = User(
                telegram_id=user_id,
                customer_code=customer_code,
                name=message.from_user.full_name,
                language=DEFAULT_LANGUAGE,
                is_registered=False
            )
            
            session.add(new_user)
            await session.flush()  # Get the ID
            
            await message.answer(
                _("welcome", DEFAULT_LANGUAGE),
                reply_markup=get_main_menu_keyboard(DEFAULT_LANGUAGE)
            )
            
            await message.answer(
                _("customer_code", DEFAULT_LANGUAGE, code=customer_code)
            )
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer(_("error", DEFAULT_LANGUAGE))

@router.message(F.text.in_(["حسابي", "My Account"]))
async def my_account_handler(message: Message, session: AsyncSession):
    """Handle My Account button"""
    try:
        user_id = message.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("error", DEFAULT_LANGUAGE))
            return
        
        # Show account information
        account_text = _("account_info", user.language,
                        name=user.name or "غير محدد / Not specified",
                        phone=user.phone or "غير محدد / Not specified",
                        customer_code=user.customer_code)
        
        await message.answer(account_text)
        
    except Exception as e:
        logger.error(f"Error in my account handler: {e}")
        await message.answer(_("error", DEFAULT_LANGUAGE))

@router.message(F.text.in_(["إيداع", "Deposit"]))
async def deposit_button_handler(message: Message):
    """Handle Deposit button - redirect to finance handler"""
    # This will be handled by finance.py
    pass

@router.message(F.text.in_(["سحب", "Withdraw"]))
async def withdraw_button_handler(message: Message):
    """Handle Withdraw button - redirect to finance handler"""
    # This will be handled by finance.py
    pass