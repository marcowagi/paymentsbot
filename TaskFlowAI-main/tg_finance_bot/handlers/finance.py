"""
Finance handler for deposit and withdrawal requests
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Company, PaymentMethod, Request
from utils.i18n import _
from utils.keyboards import get_companies_keyboard, get_payment_methods_keyboard, get_cancel_keyboard, get_main_menu_keyboard
from config import ADMINS

logger = logging.getLogger(__name__)
router = Router()

class FinanceStates(StatesGroup):
    waiting_for_company = State()
    waiting_for_payment_method = State()
    waiting_for_amount = State()
    waiting_for_reference = State()
    waiting_for_destination = State()

@router.message(F.text.in_(["إيداع", "Deposit"]))
async def deposit_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle deposit request"""
    try:
        user_id = message.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("error"))
            return
        
        # Get active companies
        companies_result = await session.execute(
            select(Company).where(Company.is_active == True)
        )
        companies = companies_result.scalars().all()
        
        if not companies:
            await message.answer(
                "لا توجد شركات متاحة حالياً" if user.language == "ar" else "No companies available currently"
            )
            return
        
        # Set state and store request type
        await state.set_state(FinanceStates.waiting_for_company)
        await state.update_data(request_type="deposit", user_lang=user.language)
        
        await message.answer(
            _("select_company", user.language),
            reply_markup=get_companies_keyboard(companies, user.language)
        )
        
    except Exception as e:
        logger.error(f"Error in deposit handler: {e}")
        await message.answer(_("error"))

@router.message(F.text.in_(["سحب", "Withdraw"]))
async def withdraw_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle withdraw request"""
    try:
        user_id = message.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("error"))
            return
        
        # Get active companies
        companies_result = await session.execute(
            select(Company).where(Company.is_active == True)
        )
        companies = companies_result.scalars().all()
        
        if not companies:
            await message.answer(
                "لا توجد شركات متاحة حالياً" if user.language == "ar" else "No companies available currently"
            )
            return
        
        # Set state and store request type
        await state.set_state(FinanceStates.waiting_for_company)
        await state.update_data(request_type="withdraw", user_lang=user.language)
        
        await message.answer(
            _("select_company", user.language),
            reply_markup=get_companies_keyboard(companies, user.language)
        )
        
    except Exception as e:
        logger.error(f"Error in withdraw handler: {e}")
        await message.answer(_("error"))

@router.callback_query(F.data.startswith("company_"), FinanceStates.waiting_for_company)
async def company_selected_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Handle company selection"""
    try:
        company_id = int(callback.data.split("_")[1])
        data = await state.get_data()
        user_lang = data.get("user_lang", "ar")
        
        # Get payment methods for selected company
        payment_methods_result = await session.execute(
            select(PaymentMethod).where(
                PaymentMethod.company_id == company_id,
                PaymentMethod.is_active == True
            )
        )
        payment_methods = payment_methods_result.scalars().all()
        
        if not payment_methods:
            await callback.message.edit_text(
                "لا توجد طرق دفع متاحة لهذه الشركة" if user_lang == "ar" else "No payment methods available for this company"
            )
            return
        
        # Update state
        await state.update_data(company_id=company_id)
        await state.set_state(FinanceStates.waiting_for_payment_method)
        
        await callback.message.edit_text(
            _("select_payment_method", user_lang),
            reply_markup=get_payment_methods_keyboard(payment_methods, user_lang)
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in company selection handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data.startswith("payment_"), FinanceStates.waiting_for_payment_method)
async def payment_method_selected_handler(callback: CallbackQuery, state: FSMContext):
    """Handle payment method selection"""
    try:
        payment_method_id = int(callback.data.split("_")[1])
        data = await state.get_data()
        user_lang = data.get("user_lang", "ar")
        
        # Update state
        await state.update_data(payment_method_id=payment_method_id)
        await state.set_state(FinanceStates.waiting_for_amount)
        
        await callback.message.edit_text(_("enter_amount", user_lang))
        await callback.message.answer(
            "أدخل المبلغ:" if user_lang == "ar" else "Enter amount:",
            reply_markup=get_cancel_keyboard(user_lang)
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in payment method selection handler: {e}")
        await callback.answer(_("error"))

@router.message(FinanceStates.waiting_for_amount)
async def amount_handler(message: Message, state: FSMContext):
    """Handle amount input"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer(
                _("cancelled"),
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        try:
            amount = float(message.text)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            await message.answer(_("invalid_amount"))
            return
        
        data = await state.get_data()
        user_lang = data.get("user_lang", "ar")
        request_type = data.get("request_type")
        
        # Update state
        await state.update_data(amount=amount)
        await state.set_state(FinanceStates.waiting_for_reference)
        
        await message.answer(
            _("enter_reference", user_lang),
            reply_markup=get_cancel_keyboard(user_lang)
        )
        
    except Exception as e:
        logger.error(f"Error in amount handler: {e}")
        await message.answer(_("error"))

@router.message(FinanceStates.waiting_for_reference)
async def reference_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle reference input"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer(
                _("cancelled"),
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        data = await state.get_data()
        user_lang = data.get("user_lang", "ar")
        request_type = data.get("request_type")
        
        # Update state
        await state.update_data(reference=message.text)
        
        if request_type == "withdraw":
            # For withdrawals, ask for destination address
            await state.set_state(FinanceStates.waiting_for_destination)
            await message.answer(
                _("enter_destination", user_lang),
                reply_markup=get_cancel_keyboard(user_lang)
            )
        else:
            # For deposits, create the request
            await create_request(message, session, state)
        
    except Exception as e:
        logger.error(f"Error in reference handler: {e}")
        await message.answer(_("error"))

@router.message(FinanceStates.waiting_for_destination)
async def destination_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle destination address input for withdrawals"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer(
                _("cancelled"),
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Update state
        await state.update_data(destination_address=message.text)
        
        # Create the request
        await create_request(message, session, state)
        
    except Exception as e:
        logger.error(f"Error in destination handler: {e}")
        await message.answer(_("error"))

async def create_request(message: Message, session: AsyncSession, state: FSMContext):
    """Create the financial request"""
    try:
        user_id = message.from_user.id
        data = await state.get_data()
        
        # Get user
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("error"))
            return
        
        # Create request
        new_request = Request(
            user_id=user.id,
            company_id=data["company_id"],
            payment_method_id=data["payment_method_id"],
            request_type=data["request_type"],
            amount=data["amount"],
            reference=data["reference"],
            destination_address=data.get("destination_address"),
            status="pending"
        )
        
        session.add(new_request)
        await session.flush()
        
        await message.answer(
            _("request_submitted", user.language),
            reply_markup=get_main_menu_keyboard(user.language)
        )
        
        # Notify admins
        await notify_admins_new_request(message.bot, new_request, user)
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error creating request: {e}")
        await message.answer(_("error"))

async def notify_admins_new_request(bot, request: Request, user: User):
    """Notify admins about new request"""
    try:
        notification_text = (
            f"🔔 طلب جديد / New Request\n\n"
            f"👤 User: {user.name} ({user.customer_code})\n"
            f"📋 Type: {request.request_type}\n"
            f"💰 Amount: {request.amount}\n"
            f"📝 Reference: {request.reference}\n"
            f"🆔 Request ID: {request.id}\n"
            f"⏰ Time: {request.created_at}"
        )
        
        if request.destination_address:
            notification_text += f"\n🏦 Destination: {request.destination_address}"
        
        for admin_id in ADMINS:
            try:
                await bot.send_message(admin_id, notification_text)
            except Exception as e:
                logger.warning(f"Failed to notify admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error notifying admins: {e}")

# Handle cancel callbacks
@router.callback_query(F.data == "cancel")
async def cancel_callback_handler(callback: CallbackQuery, state: FSMContext):
    """Handle cancel callback"""
    await state.clear()
    await callback.message.edit_text(_("cancelled"))
    await callback.answer()