"""
Admin handler for admin panel and authorization with role-based permissions
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import User, Request, Complaint, RequestStatus, ComplaintStatus, RequestType, Company, PaymentMethod
from utils.i18n import _
from utils.keyboards import get_admin_panel_keyboard, get_main_menu_keyboard
from utils.auth import get_user_permissions, is_super_admin, has_permission, Permissions
from config import ADMINS

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("admin"))
async def admin_panel_handler(message: Message, session: AsyncSession):
    """Handle admin panel access with permission checks"""
    try:
        user_id = message.from_user.id
        
        # Get user permissions
        permissions = await get_user_permissions(session, user_id)
        
        if not permissions:
            await message.answer(_("unauthorized"))
            return
        
        # Get user for language
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        lang = user.language if user else "ar"
        
        # Get statistics for admin dashboard
        stats = await get_admin_statistics(session)
        
        admin_text = f"🔧 {'لوحة تحكم المدير' if lang == 'ar' else 'Admin Control Panel'}\n\n"
        
        if lang == "ar":
            admin_text += f"📊 الإحصائيات:\n"
            admin_text += f"👥 المستخدمون: {stats['users_count']}\n"
            admin_text += f"⏳ طلبات معلقة: {stats['pending_requests']}\n"
            admin_text += f"💬 شكاوى معلقة: {stats['pending_complaints']}\n"
            admin_text += f"✅ طلبات مُعتمدة اليوم: {stats['approved_today']}\n\n"
            admin_text += f"🔑 صلاحياتك: {', '.join(permissions)}"
        else:
            admin_text += f"📊 Statistics:\n"
            admin_text += f"👥 Users: {stats['users_count']}\n"
            admin_text += f"⏳ Pending Requests: {stats['pending_requests']}\n"
            admin_text += f"💬 Pending Complaints: {stats['pending_complaints']}\n"
            admin_text += f"✅ Approved Today: {stats['approved_today']}\n\n"
            admin_text += f"🔑 Your Permissions: {', '.join(permissions)}"
        
        await message.answer(
            admin_text,
            reply_markup=get_admin_panel_keyboard(lang, permissions)
        )
        
    except Exception as e:
        logger.error(f"Error in admin panel handler: {e}")
        await message.answer(_("error"))

@router.callback_query(F.data == "admin_pending_requests")
async def admin_pending_requests_handler(callback: CallbackQuery, session: AsyncSession):
    """Handle pending requests view"""
    try:
        user_id = callback.from_user.id
        
        # Check permission
        if not await has_permission(session, user_id, Permissions.APPROVE_TX):
            await callback.answer(_("permission_denied"))
            return
        
        # Get user for language
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        lang = user.language if user else "ar"
        
        # Get pending requests
        pending_requests = await session.execute(
            select(Request, User, Company, PaymentMethod)
            .join(User, Request.user_id == User.id)
            .join(Company, Request.company_id == Company.id) 
            .join(PaymentMethod, Request.payment_method_id == PaymentMethod.id)
            .where(Request.status == RequestStatus.pending)
            .order_by(Request.created_at.desc())
            .limit(10)
        )
        requests = pending_requests.all()
        
        if not requests:
            await callback.message.edit_text(
                "لا توجد طلبات معلقة" if lang == "ar" else "No pending requests"
            )
            return
        
        response = f"🗂️ {'الطلبات المعلقة' if lang == 'ar' else 'Pending Requests'}\n\n"
        
        for request, req_user, company, payment_method in requests:
            company_name = company.name_ar if lang == "ar" else company.name_en
            request_type = "إيداع" if request.request_type.value == "deposit" else "سحب"
            if lang == "en":
                request_type = "Deposit" if request.request_type.value == "deposit" else "Withdrawal"
            
            response += f"🆔 {request.id} | {request_type}\n"
            response += f"👤 {req_user.name} ({req_user.customer_code})\n"
            response += f"🏢 {company_name}\n"
            response += f"💰 {request.amount} {request.currency}\n"
            if request.reference:
                response += f"📄 {request.reference}\n"
            if request.user_withdraw_to:
                response += f"📍 {request.user_withdraw_to}\n"
            response += f"📅 {request.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        await callback.message.edit_text(response)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin pending requests handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data == "admin_statistics")
async def admin_statistics_handler(callback: CallbackQuery, session: AsyncSession):
    """Handle comprehensive statistics view"""
    try:
        user_id = callback.from_user.id
        
        # Check permission
        permissions = await get_user_permissions(session, user_id)
        if not permissions:
            await callback.answer(_("unauthorized"))
            return
        
        # Get user for language
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        lang = user.language if user else "ar"
        
        # Get comprehensive statistics
        stats = await get_comprehensive_statistics(session)
        
        if lang == "ar":
            response = f"📊 إحصائيات شاملة\n\n"
            response += f"👥 إجمالي المستخدمين: {stats['total_users']}\n"
            response += f"✅ مستخدمون مسجلون: {stats['registered_users']}\n"
            response += f"👁️ مستخدمون ضيوف: {stats['guest_users']}\n\n"
            response += f"💼 إجمالي الطلبات: {stats['total_requests']}\n"
            response += f"⏳ معلقة: {stats['pending_requests']}\n"
            response += f"✅ مُعتمدة: {stats['approved_requests']}\n"
            response += f"❌ مرفوضة: {stats['rejected_requests']}\n\n"
            response += f"💰 إجمالي المبالغ:\n"
            response += f"📈 إيداعات: {stats['total_deposits']}\n"
            response += f"📉 سحوبات: {stats['total_withdrawals']}\n\n"
            response += f"💬 إجمالي الشكاوى: {stats['total_complaints']}\n"
            response += f"⏳ شكاوى معلقة: {stats['pending_complaints']}\n"
        else:
            response = f"📊 Comprehensive Statistics\n\n"
            response += f"👥 Total Users: {stats['total_users']}\n"
            response += f"✅ Registered Users: {stats['registered_users']}\n"
            response += f"👁️ Guest Users: {stats['guest_users']}\n\n"
            response += f"💼 Total Requests: {stats['total_requests']}\n"
            response += f"⏳ Pending: {stats['pending_requests']}\n"
            response += f"✅ Approved: {stats['approved_requests']}\n"
            response += f"❌ Rejected: {stats['rejected_requests']}\n\n"
            response += f"💰 Total Amounts:\n"
            response += f"📈 Deposits: {stats['total_deposits']}\n"
            response += f"📉 Withdrawals: {stats['total_withdrawals']}\n\n"
            response += f"💬 Total Complaints: {stats['total_complaints']}\n"
            response += f"⏳ Pending Complaints: {stats['pending_complaints']}\n"
        
        await callback.message.edit_text(response)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin statistics handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data == "admin_main_menu")
async def admin_main_menu_handler(callback: CallbackQuery, session: AsyncSession):
    """Handle return to main menu"""
    try:
        user_id = callback.from_user.id
        
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer(_("error"))
            return
        
        await callback.message.edit_text(
            _("main_menu", user.language),
            reply_markup=None
        )
        
        await callback.message.answer(
            _("main_menu", user.language),
            reply_markup=get_main_menu_keyboard(user.language, user.is_registered)
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin main menu handler: {e}")
        await callback.answer(_("error"))

async def get_admin_statistics(session: AsyncSession) -> dict:
    """Get basic admin dashboard statistics"""
    try:
        # Get user count
        users_count = await session.execute(select(func.count(User.id)))
        users_count = users_count.scalar() or 0
        
        # Get pending requests count
        pending_requests = await session.execute(
            select(func.count(Request.id)).where(Request.status == RequestStatus.pending)
        )
        pending_requests = pending_requests.scalar() or 0
        
        # Get pending complaints count
        pending_complaints = await session.execute(
            select(func.count(Complaint.id)).where(Complaint.status == ComplaintStatus.pending)
        )
        pending_complaints = pending_complaints.scalar() or 0
        
        # Get approved requests today
        from datetime import datetime, timedelta
        today = datetime.now().date()
        approved_today = await session.execute(
            select(func.count(Request.id)).where(
                Request.status == RequestStatus.approved,
                func.date(Request.updated_at) == today
            )
        )
        approved_today = approved_today.scalar() or 0
        
        return {
            'users_count': users_count,
            'pending_requests': pending_requests,
            'pending_complaints': pending_complaints,
            'approved_today': approved_today
        }
        
    except Exception as e:
        logger.error(f"Error getting admin statistics: {e}")
        return {
            'users_count': 0,
            'pending_requests': 0,
            'pending_complaints': 0,
            'approved_today': 0
        }

async def get_comprehensive_statistics(session: AsyncSession) -> dict:
    """Get comprehensive statistics for admin"""
    try:
        # User statistics
        total_users = await session.execute(select(func.count(User.id)))
        total_users = total_users.scalar() or 0
        
        registered_users = await session.execute(
            select(func.count(User.id)).where(User.is_registered == True)
        )
        registered_users = registered_users.scalar() or 0
        
        guest_users = total_users - registered_users
        
        # Request statistics
        total_requests = await session.execute(select(func.count(Request.id)))
        total_requests = total_requests.scalar() or 0
        
        pending_requests = await session.execute(
            select(func.count(Request.id)).where(Request.status == RequestStatus.pending)
        )
        pending_requests = pending_requests.scalar() or 0
        
        approved_requests = await session.execute(
            select(func.count(Request.id)).where(Request.status == RequestStatus.approved)
        )
        approved_requests = approved_requests.scalar() or 0
        
        rejected_requests = await session.execute(
            select(func.count(Request.id)).where(Request.status == RequestStatus.rejected)
        )
        rejected_requests = rejected_requests.scalar() or 0
        
        # Amount statistics
        total_deposits = await session.execute(
            select(func.sum(Request.amount)).where(
                Request.request_type == RequestType.deposit,
                Request.status == RequestStatus.approved
            )
        )
        total_deposits = total_deposits.scalar() or 0
        
        total_withdrawals = await session.execute(
            select(func.sum(Request.amount)).where(
                Request.request_type == RequestType.withdraw, 
                Request.status == RequestStatus.approved
            )
        )
        total_withdrawals = total_withdrawals.scalar() or 0
        
        # Complaint statistics
        total_complaints = await session.execute(select(func.count(Complaint.id)))
        total_complaints = total_complaints.scalar() or 0
        
        pending_complaints = await session.execute(
            select(func.count(Complaint.id)).where(Complaint.status == ComplaintStatus.pending)
        )
        pending_complaints = pending_complaints.scalar() or 0
        
        return {
            'total_users': total_users,
            'registered_users': registered_users,
            'guest_users': guest_users,
            'total_requests': total_requests,
            'pending_requests': pending_requests,
            'approved_requests': approved_requests,
            'rejected_requests': rejected_requests,
            'total_deposits': f"{total_deposits:.2f}",
            'total_withdrawals': f"{total_withdrawals:.2f}",
            'total_complaints': total_complaints,
            'pending_complaints': pending_complaints
        }
        
    except Exception as e:
        logger.error(f"Error getting comprehensive statistics: {e}")
        return {
            'total_users': 0,
            'registered_users': 0,
            'guest_users': 0,
            'total_requests': 0,
            'pending_requests': 0,
            'approved_requests': 0,
            'rejected_requests': 0,
            'total_deposits': "0.00",
            'total_withdrawals': "0.00",
            'total_complaints': 0,
            'pending_complaints': 0
        }