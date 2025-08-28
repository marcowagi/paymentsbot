"""
Finance handler for deposit and withdrawal requests with Guest Mode restrictions and comprehensive transaction flow
"""

import logging
import uuid
from decimal import Decimal, InvalidOperation
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Company, PaymentMethod, Request, RequestType, RequestStatus
from utils.i18n import _
from utils.keyboards import (
    get_companies_keyboard, get_payment_methods_keyboard, get_cancel_keyboard, 
    get_main_menu_keyboard, get_yes_no_keyboard
)
from utils.states import DepositStates, WithdrawStates
from utils.auth import is_guest_mode, create_audit_log
from config import ADMINS

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text.in_(["🏦 طلب إيداع", "🏦 Request Deposit"]))
async def deposit_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle deposit request with guest mode check"""
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
        
        await state.set_state(DepositStates.waiting_for_company)
        await state.update_data(request_type="deposit")
        
        await message.answer(
            _("select_company", user.language),
            reply_markup=get_companies_keyboard(companies, user.language)
        )
        
    except Exception as e:
        logger.error(f"Error in deposit handler: {e}")
        await message.answer(_("error"))

@router.message(F.text.in_(["💸 طلب سحب", "💸 Request Withdrawal"]))
async def withdraw_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle withdrawal request with guest mode check"""
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
        
        await state.set_state(WithdrawStates.waiting_for_company)
        await state.update_data(request_type="withdraw")
        
        await message.answer(
            _("select_company", user.language),
            reply_markup=get_companies_keyboard(companies, user.language)
        )
        
    except Exception as e:
        logger.error(f"Error in withdraw handler: {e}")
        await message.answer(_("error"))

@router.callback_query(F.data.startswith("company_"))
async def company_selection_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Handle company selection for both deposit and withdrawal"""
    try:
        company_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer(_("error"))
            return
        
        # Get company
        company_result = await session.execute(
            select(Company).where(Company.id == company_id)
        )
        company = company_result.scalar_one_or_none()
        
        if not company:
            await callback.answer(_("error"))
            return
        
        # Get active payment methods for this company
        payment_methods_result = await session.execute(
            select(PaymentMethod).where(
                PaymentMethod.company_id == company_id,
                PaymentMethod.is_active == True
            )
        )
        payment_methods = payment_methods_result.scalars().all()
        
        if not payment_methods:
            await callback.answer(
                "لا توجد طرق دفع متاحة لهذه الشركة" if user.language == "ar" else "No payment methods available for this company"
            )
            return
        
        # Get current request type from state
        data = await state.get_data()
        request_type = data.get("request_type", "deposit")
        
        await state.update_data(company_id=company_id, company_name=company.name_ar if user.language == "ar" else company.name_en)
        
        if request_type == "deposit":
            await state.set_state(DepositStates.waiting_for_payment_method)
        else:
            await state.set_state(WithdrawStates.waiting_for_payment_method)
        
        await callback.message.edit_text(
            _("select_payment_method", user.language),
            reply_markup=get_payment_methods_keyboard(payment_methods, user.language)
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in company selection handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data.startswith("payment_"))
async def payment_method_selection_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Handle payment method selection"""
    try:
        payment_method_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer(_("error"))
            return
        
        # Get payment method
        payment_method_result = await session.execute(
            select(PaymentMethod).where(PaymentMethod.id == payment_method_id)
        )
        payment_method = payment_method_result.scalar_one_or_none()
        
        if not payment_method:
            await callback.answer(_("error"))
            return
        
        await state.update_data(
            payment_method_id=payment_method_id,
            payment_method_name=payment_method.name_ar if user.language == "ar" else payment_method.name_en
        )
        
        # Get current request type from state
        data = await state.get_data()
        request_type = data.get("request_type", "deposit")
        
        if request_type == "deposit":
            await state.set_state(DepositStates.waiting_for_amount)
        else:
            await state.set_state(WithdrawStates.waiting_for_amount)
        
        await callback.message.edit_text(
            _("enter_amount", user.language) + f" ({user.currency})",
            reply_markup=None
        )
        
        await callback.message.answer(
            _("enter_amount_instruction", user.language),
            reply_markup=get_cancel_keyboard(user.language)
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in payment method selection handler: {e}")
        await callback.answer(_("error"))

@router.message(WithdrawStates.waiting_for_amount)
@router.message(DepositStates.waiting_for_amount)
async def amount_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle amount input for both deposit and withdrawal"""
    try:
        user_id = message.from_user.id
        amount_text = message.text.strip()
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("please_start"))
            return
        
        # Handle cancel
        if amount_text in ["❌ إلغاء", "❌ Cancel"]:
            await state.clear()
            await message.answer(
                _("cancelled", user.language),
                reply_markup=get_main_menu_keyboard(user.language, user.is_registered)
            )
            return
        
        # Validate amount
        try:
            amount = Decimal(amount_text.replace(',', '.'))
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except (ValueError, InvalidOperation):
            await message.answer(
                _("invalid_amount_format", user.language),
                reply_markup=get_cancel_keyboard(user.language)
            )
            return
        
        # Basic amount validation (you can customize these limits)
        min_amount = Decimal('1.00')
        max_amount = Decimal('1000000.00')
        
        if amount < min_amount:
            await message.answer(
                _("amount_too_small", user.language, min_amount=str(min_amount)),
                reply_markup=get_cancel_keyboard(user.language)
            )
            return
        
        if amount > max_amount:
            await message.answer(
                _("amount_too_large", user.language, max_amount=str(max_amount)),
                reply_markup=get_cancel_keyboard(user.language)
            )
            return
        
        await state.update_data(amount=str(amount), currency=user.currency)
        
        # Get current request type from state
        data = await state.get_data()
        request_type = data.get("request_type", "deposit")
        
        if request_type == "deposit":
            await state.set_state(DepositStates.waiting_for_reference)
            await message.answer(
                _("enter_reference_instruction", user.language),
                reply_markup=get_cancel_keyboard(user.language)
            )
        else:
            await state.set_state(WithdrawStates.waiting_for_address)
            await message.answer(
                _("enter_withdrawal_address", user.language),
                reply_markup=get_cancel_keyboard(user.language)
            )
        
    except Exception as e:
        logger.error(f"Error in amount handler: {e}")
        await message.answer(_("error"))

@router.message(DepositStates.waiting_for_reference)
async def deposit_reference_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle deposit reference input"""
    try:
        user_id = message.from_user.id
        reference = message.text.strip()
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("please_start"))
            return
        
        # Handle cancel
        if reference in ["❌ إلغاء", "❌ Cancel"]:
            await state.clear()
            await message.answer(
                _("cancelled", user.language),
                reply_markup=get_main_menu_keyboard(user.language, user.is_registered)
            )
            return
        
        await state.update_data(reference=reference)
        await state.set_state(DepositStates.waiting_for_confirmation)
        
        # Show confirmation
        data = await state.get_data()
        confirmation_text = _("request_confirmation", user.language,
                             type=_("deposit_type", user.language),
                             company=data.get("company_name", ""),
                             payment_method=data.get("payment_method_name", ""),
                             amount=data.get("amount", ""),
                             currency=data.get("currency", ""),
                             additional_info=_("reference_info", user.language, reference=reference))
        
        await message.answer(
            confirmation_text,
            reply_markup=get_yes_no_keyboard(user.language)
        )
        
    except Exception as e:
        logger.error(f"Error in deposit reference handler: {e}")
        await message.answer(_("error"))

@router.message(WithdrawStates.waiting_for_address)
async def withdraw_address_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle withdrawal address input"""
    try:
        user_id = message.from_user.id
        address = message.text.strip()
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(_("please_start"))
            return
        
        # Handle cancel
        if address in ["❌ إلغاء", "❌ Cancel"]:
            await state.clear()
            await message.answer(
                _("cancelled", user.language),
                reply_markup=get_main_menu_keyboard(user.language, user.is_registered)
            )
            return
        
        await state.update_data(user_withdraw_to=address)
        await state.set_state(WithdrawStates.waiting_for_confirmation)
        
        # Show confirmation
        data = await state.get_data()
        confirmation_text = _("request_confirmation", user.language,
                             type=_("withdrawal_type", user.language),
                             company=data.get("company_name", ""),
                             payment_method=data.get("payment_method_name", ""),
                             amount=data.get("amount", ""),
                             currency=data.get("currency", ""),
                             additional_info=_("withdrawal_address_info", user.language, address=address))
        
        await message.answer(
            confirmation_text,
            reply_markup=get_yes_no_keyboard(user.language)
        )
        
    except Exception as e:
        logger.error(f"Error in withdrawal address handler: {e}")
        await message.answer(_("error"))

@router.callback_query(F.data == "confirm_yes")
async def confirm_request_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Handle request confirmation"""
    try:
        user_id = callback.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer(_("error"))
            return
        
        # Get request data from state
        data = await state.get_data()
        
        # Generate client token for idempotency
        client_token = str(uuid.uuid4())
        
        # Create request
        request_type = RequestType.deposit if data.get("request_type") == "deposit" else RequestType.withdraw
        
        new_request = Request(
            user_id=user.id,
            company_id=int(data.get("company_id")),
            payment_method_id=int(data.get("payment_method_id")),
            request_type=request_type,
            amount=Decimal(data.get("amount")),
            currency=data.get("currency", user.currency),
            reference=data.get("reference"),
            user_withdraw_to=data.get("user_withdraw_to"),
            status=RequestStatus.pending,
            client_token=client_token
        )
        
        session.add(new_request)
        await session.commit()
        
        # Create audit log
        await create_audit_log(
            session, user_id, "create_request", "request", new_request.id,
            before=None,
            after={
                "type": request_type.value,
                "amount": str(new_request.amount),
                "currency": new_request.currency,
                "status": RequestStatus.pending.value
            }
        )
        
        # Clear state
        await state.clear()
        
        await callback.message.edit_text(
            _("request_created_successfully", user.language, request_id=new_request.id),
            reply_markup=None
        )
        
        await callback.message.answer(
            _("main_menu", user.language),
            reply_markup=get_main_menu_keyboard(user.language, user.is_registered)
        )
        
        # Notify admins (you can implement this later)
        # await notify_admins_new_request(new_request)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in confirm request handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data == "confirm_no")
async def cancel_request_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Handle request cancellation"""
    try:
        user_id = callback.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer(_("error"))
            return
        
        await state.clear()
        
        await callback.message.edit_text(
            _("cancelled", user.language),
            reply_markup=None
        )
        
        await callback.message.answer(
            _("main_menu", user.language),
            reply_markup=get_main_menu_keyboard(user.language, user.is_registered)
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in cancel request handler: {e}")
        await callback.answer(_("error"))

@router.message(F.text.in_(["📑 طلباتي", "📑 My Requests"]))
async def my_requests_handler(message: Message, session: AsyncSession):
    """Handle my requests view"""
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
        
        # Get user's requests
        requests_result = await session.execute(
            select(Request, Company, PaymentMethod)
            .join(Company, Request.company_id == Company.id)
            .join(PaymentMethod, Request.payment_method_id == PaymentMethod.id)
            .where(Request.user_id == user.id)
            .order_by(Request.created_at.desc())
        )
        requests = requests_result.all()
        
        if not requests:
            await message.answer(_("no_requests_found", user.language))
            return
        
        # Format requests
        response = _("my_requests_header", user.language) + "\n\n"
        
        for request, company, payment_method in requests:
            company_name = company.name_ar if user.language == "ar" else company.name_en
            request_type = _("deposit_type", user.language) if request.request_type == RequestType.deposit else _("withdrawal_type", user.language)
            status = _("status_" + request.status.value, user.language)
            
            request_info = _("request_details", user.language,
                           id=request.id,
                           type=request_type,
                           company=company_name,
                           amount=str(request.amount),
                           currency=request.currency,
                           status=status,
                           date=request.created_at.strftime("%Y-%m-%d %H:%M"))
            
            response += request_info + "\n\n"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Error in my requests handler: {e}")
        await message.answer(_("error"))

# Handle cancel callbacks
@router.callback_query(F.data == "cancel")
async def cancel_callback_handler(callback: CallbackQuery, state: FSMContext):
    """Handle cancel callback"""
    try:
        await state.clear()
        await callback.message.edit_text(_("cancelled"))
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in cancel callback handler: {e}")
        await callback.answer(_("error"))