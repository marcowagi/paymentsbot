"""
Companies management handler for admin CRUD operations
"""

import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Company, PaymentMethod
from utils.keyboards import get_cancel_keyboard
from config import ADMINS

logger = logging.getLogger(__name__)
router = Router()

class CompanyStates(StatesGroup):
    waiting_for_company_name_ar = State()
    waiting_for_company_name_en = State()
    waiting_for_payment_method_company = State()
    waiting_for_payment_method_name_ar = State()
    waiting_for_payment_method_name_en = State()

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMINS

@router.message(Command("add_company"))
async def add_company_handler(message: Message, state: FSMContext):
    """Handle adding new company"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer("غير مصرح / Unauthorized")
            return
        
        await state.set_state(CompanyStates.waiting_for_company_name_ar)
        await message.answer(
            "أدخل اسم الشركة بالعربية / Enter company name in Arabic:",
            reply_markup=get_cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in add company handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.message(CompanyStates.waiting_for_company_name_ar)
async def company_name_ar_handler(message: Message, state: FSMContext):
    """Handle Arabic company name input"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer("تم الإلغاء / Cancelled")
            return
        
        await state.update_data(name_ar=message.text)
        await state.set_state(CompanyStates.waiting_for_company_name_en)
        
        await message.answer(
            "أدخل اسم الشركة بالإنجليزية / Enter company name in English:",
            reply_markup=get_cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in company name AR handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.message(CompanyStates.waiting_for_company_name_en)
async def company_name_en_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle English company name input and create company"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer("تم الإلغاء / Cancelled")
            return
        
        data = await state.get_data()
        
        # Create new company
        new_company = Company(
            name_ar=data["name_ar"],
            name_en=message.text,
            is_active=True
        )
        
        session.add(new_company)
        await session.flush()
        
        await message.answer(
            f"✅ تم إضافة الشركة بنجاح / Company added successfully\n"
            f"Arabic: {data['name_ar']}\n"
            f"English: {message.text}\n"
            f"ID: {new_company.id}"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in company name EN handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.message(Command("list_companies"))
async def list_companies_handler(message: Message, session: AsyncSession):
    """Handle listing all companies"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer("غير مصرح / Unauthorized")
            return
        
        # Get all companies
        result = await session.execute(select(Company).order_by(Company.id))
        companies = result.scalars().all()
        
        if not companies:
            await message.answer("لا توجد شركات / No companies found")
            return
        
        companies_text = "🏢 قائمة الشركات / Companies List:\n\n"
        
        for company in companies:
            status = "✅ نشط / Active" if company.is_active else "❌ غير نشط / Inactive"
            companies_text += (
                f"🆔 ID: {company.id}\n"
                f"📝 Arabic: {company.name_ar}\n"
                f"📝 English: {company.name_en}\n"
                f"📊 Status: {status}\n"
                f"📅 Created: {company.created_at.strftime('%Y-%m-%d')}\n"
                f"{'─' * 30}\n"
            )
        
        # Send in chunks if too long
        if len(companies_text) > 4000:
            for i in range(0, len(companies_text), 4000):
                await message.answer(companies_text[i:i+4000])
        else:
            await message.answer(companies_text)
        
    except Exception as e:
        logger.error(f"Error in list companies handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.message(Command("add_payment_method"))
async def add_payment_method_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle adding new payment method"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer("غير مصرح / Unauthorized")
            return
        
        # Get active companies
        result = await session.execute(select(Company).where(Company.is_active == True))
        companies = result.scalars().all()
        
        if not companies:
            await message.answer("لا توجد شركات نشطة / No active companies found")
            return
        
        companies_text = "اختر الشركة بإدخال الرقم / Choose company by entering ID:\n\n"
        for company in companies:
            companies_text += f"{company.id} - {company.name_ar} / {company.name_en}\n"
        
        await state.set_state(CompanyStates.waiting_for_payment_method_company)
        await message.answer(
            companies_text,
            reply_markup=get_cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in add payment method handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.message(CompanyStates.waiting_for_payment_method_company)
async def payment_method_company_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle company selection for payment method"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer("تم الإلغاء / Cancelled")
            return
        
        try:
            company_id = int(message.text)
        except ValueError:
            await message.answer("رقم غير صحيح / Invalid number")
            return
        
        # Verify company exists and is active
        result = await session.execute(
            select(Company).where(Company.id == company_id, Company.is_active == True)
        )
        company = result.scalar_one_or_none()
        
        if not company:
            await message.answer("شركة غير موجودة أو غير نشطة / Company not found or inactive")
            return
        
        await state.update_data(company_id=company_id)
        await state.set_state(CompanyStates.waiting_for_payment_method_name_ar)
        
        await message.answer(
            f"أدخل اسم طريقة الدفع بالعربية لشركة {company.name_ar} / Enter payment method name in Arabic for {company.name_en}:",
            reply_markup=get_cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in payment method company handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.message(CompanyStates.waiting_for_payment_method_name_ar)
async def payment_method_name_ar_handler(message: Message, state: FSMContext):
    """Handle Arabic payment method name input"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer("تم الإلغاء / Cancelled")
            return
        
        await state.update_data(method_name_ar=message.text)
        await state.set_state(CompanyStates.waiting_for_payment_method_name_en)
        
        await message.answer(
            "أدخل اسم طريقة الدفع بالإنجليزية / Enter payment method name in English:",
            reply_markup=get_cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in payment method name AR handler: {e}")
        await message.answer("حدث خطأ / Error occurred")

@router.message(CompanyStates.waiting_for_payment_method_name_en)
async def payment_method_name_en_handler(message: Message, session: AsyncSession, state: FSMContext):
    """Handle English payment method name input and create payment method"""
    try:
        if message.text in ["إلغاء", "Cancel"]:
            await state.clear()
            await message.answer("تم الإلغاء / Cancelled")
            return
        
        data = await state.get_data()
        
        # Create new payment method
        new_payment_method = PaymentMethod(
            company_id=data["company_id"],
            name_ar=data["method_name_ar"],
            name_en=message.text,
            is_active=True
        )
        
        session.add(new_payment_method)
        await session.flush()
        
        # Get company name for confirmation
        result = await session.execute(select(Company).where(Company.id == data["company_id"]))
        company = result.scalar_one()
        
        await message.answer(
            f"✅ تم إضافة طريقة الدفع بنجاح / Payment method added successfully\n"
            f"Company: {company.name_ar} / {company.name_en}\n"
            f"Arabic: {data['method_name_ar']}\n"
            f"English: {message.text}\n"
            f"ID: {new_payment_method.id}"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in payment method name EN handler: {e}")
        await message.answer("حدث خطأ / Error occurred")