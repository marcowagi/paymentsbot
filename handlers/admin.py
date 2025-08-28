"""
Admin handler for admin panel and authorization
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import User, Request, Complaint
from utils.i18n import _
from utils.keyboards import get_admin_panel_keyboard
from config import ADMINS

logger = logging.getLogger(__name__)
router = Router()

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMINS

@router.message(Command("admin"))
async def admin_panel_handler(message: Message, session: AsyncSession):
    """Handle admin panel access"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            await message.answer(_("unauthorized"))
            return
        
        # Get admin's language preference
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        admin_user = result.scalar_one_or_none()
        lang = admin_user.language if admin_user else "ar"
        
        # Get counts
        pending_requests_count = await session.execute(
            select(func.count(Request.id)).where(Request.status == "pending")
        )
        pending_requests = pending_requests_count.scalar()
        
        pending_complaints_count = await session.execute(
            select(func.count(Complaint.id)).where(Complaint.status == "pending")
        )
        pending_complaints = pending_complaints_count.scalar()
        
        admin_text = (
            f"🔐 {_('admin_panel', lang)}\n\n"
            f"📋 {_('pending_requests', lang, count=pending_requests)}\n"
            f"📢 {_('pending_complaints', lang, count=pending_complaints)}"
        )
        
        await message.answer(
            admin_text,
            reply_markup=get_admin_panel_keyboard(lang)
        )
        
    except Exception as e:
        logger.error(f"Error in admin panel handler: {e}")
        await message.answer(_("error"))

@router.callback_query(F.data == "admin_pending_requests")
async def admin_pending_requests_handler(callback: CallbackQuery, session: AsyncSession):
    """Handle pending requests view"""
    try:
        user_id = callback.from_user.id
        
        if not is_admin(user_id):
            await callback.answer(_("unauthorized"))
            return
        
        # Get pending requests
        result = await session.execute(
            select(Request).where(Request.status == "pending").order_by(Request.created_at.desc()).limit(10)
        )
        requests = result.scalars().all()
        
        if not requests:
            await callback.message.edit_text("لا توجد طلبات معلقة / No pending requests")
            await callback.answer()
            return
        
        requests_text = "📋 الطلبات المعلقة / Pending Requests:\n\n"
        
        for req in requests:
            # Get user info
            user_result = await session.execute(
                select(User).where(User.id == req.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            requests_text += (
                f"🆔 ID: {req.id}\n"
                f"👤 User: {user.name if user else 'Unknown'} ({user.customer_code if user else 'N/A'})\n"
                f"📋 Type: {req.request_type}\n"
                f"💰 Amount: {req.amount}\n"
                f"📝 Reference: {req.reference}\n"
                f"⏰ Created: {req.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"{'─' * 30}\n"
            )
        
        await callback.message.edit_text(requests_text[:4000])  # Telegram message limit
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in pending requests handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data == "admin_pending_complaints")
async def admin_pending_complaints_handler(callback: CallbackQuery, session: AsyncSession):
    """Handle pending complaints view"""
    try:
        user_id = callback.from_user.id
        
        if not is_admin(user_id):
            await callback.answer(_("unauthorized"))
            return
        
        # Get pending complaints
        result = await session.execute(
            select(Complaint).where(Complaint.status == "pending").order_by(Complaint.created_at.desc()).limit(10)
        )
        complaints = result.scalars().all()
        
        if not complaints:
            await callback.message.edit_text("لا توجد شكاوى معلقة / No pending complaints")
            await callback.answer()
            return
        
        complaints_text = "📢 الشكاوى المعلقة / Pending Complaints:\n\n"
        
        for complaint in complaints:
            # Get user info
            user_result = await session.execute(
                select(User).where(User.id == complaint.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            complaints_text += (
                f"🆔 ID: {complaint.id}\n"
                f"👤 User: {user.name if user else 'Unknown'} ({user.customer_code if user else 'N/A'})\n"
                f"📝 Message: {complaint.message[:100]}{'...' if len(complaint.message) > 100 else ''}\n"
                f"⏰ Created: {complaint.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"{'─' * 30}\n"
            )
        
        await callback.message.edit_text(complaints_text[:4000])  # Telegram message limit
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in pending complaints handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data == "admin_manage_companies")
async def admin_manage_companies_handler(callback: CallbackQuery):
    """Handle company management - redirect to companies handler"""
    await callback.message.edit_text(
        "إدارة الشركات / Companies Management\n\n"
        "استخدم الأوامر التالية / Use the following commands:\n"
        "/add_company - إضافة شركة جديدة / Add new company\n"
        "/list_companies - عرض الشركات / List companies\n"
        "/add_payment_method - إضافة طريقة دفع / Add payment method"
    )
    await callback.answer()

# Additional admin commands will be handled by other handlers (companies, broadcast, etc.)