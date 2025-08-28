"""
Admin handler for admin panel and authorization
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import User, Request, Complaint, AuditLog
from utils.i18n import _
from utils.keyboards import get_admin_panel_keyboard, get_admin_management_keyboard
from config import ADMINS

logger = logging.getLogger(__name__)
router = Router()

class AdminStates(StatesGroup):
    waiting_for_user_id = State()

async def is_admin(user_id: int, session: AsyncSession) -> bool:
    """Check if user is admin (super admin from config or database admin)"""
    # Check if user is super admin from config
    if user_id in ADMINS:
        return True
    
    # Check if user is database admin
    result = await session.execute(
        select(User).where(
            User.telegram_id == user_id,
            User.is_admin == True
        )
    )
    user = result.scalar_one_or_none()
    return user is not None

def is_super_admin(user_id: int) -> bool:
    """Check if user is super admin from config"""
    return user_id in ADMINS

async def log_admin_action(session: AsyncSession, action: str, performed_by: int, target_user_id: int = None, details: str = None):
    """Log admin action to audit log"""
    audit_log = AuditLog(
        action=action,
        performed_by=performed_by,
        target_user_id=target_user_id,
        details=details
    )
    session.add(audit_log)
    await session.commit()

@router.message(Command("admin"))
async def admin_panel_handler(message: Message, session: AsyncSession):
    """Handle admin panel access"""
    try:
        user_id = message.from_user.id
        
        if not await is_admin(user_id, session):
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
        
        if not await is_admin(user_id, session):
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
        
        if not await is_admin(user_id, session):
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

@router.callback_query(F.data == "admin_manage_admins")
async def admin_manage_admins_handler(callback: CallbackQuery, session: AsyncSession):
    """Handle admin management panel access - only for super admins"""
    try:
        user_id = callback.from_user.id
        
        # Only super admins can access admin management
        if not is_super_admin(user_id):
            await callback.answer(_("unauthorized"))
            return
        
        # Get admin's language preference
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        admin_user = result.scalar_one_or_none()
        lang = admin_user.language if admin_user else "ar"
        
        admin_text = _("admin_management_panel", lang)
        
        await callback.message.edit_text(
            admin_text,
            reply_markup=get_admin_management_keyboard(lang)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin management handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data == "admin_back_to_panel")
async def admin_back_to_panel_handler(callback: CallbackQuery, session: AsyncSession):
    """Handle back to admin panel"""
    try:
        user_id = callback.from_user.id
        
        if not await is_admin(user_id, session):
            await callback.answer(_("unauthorized"))
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
        
        await callback.message.edit_text(
            admin_text,
            reply_markup=get_admin_panel_keyboard(lang)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in back to admin panel handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data == "admin_list_admins")
async def admin_list_admins_handler(callback: CallbackQuery, session: AsyncSession):
    """Handle listing all admins"""
    try:
        user_id = callback.from_user.id
        
        if not is_super_admin(user_id):
            await callback.answer(_("unauthorized"))
            return
        
        # Get admin's language preference
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        admin_user = result.scalar_one_or_none()
        lang = admin_user.language if admin_user else "ar"
        
        # Get all database admins
        db_admins_result = await session.execute(
            select(User).where(User.is_admin == True).order_by(User.name)
        )
        db_admins = db_admins_result.scalars().all()
        
        admin_text = _("admin_list_header", lang) + "\n\n"
        
        # Add super admins from config
        for super_admin_id in ADMINS:
            super_admin_result = await session.execute(
                select(User).where(User.telegram_id == super_admin_id)
            )
            super_admin = super_admin_result.scalar_one_or_none()
            
            if super_admin:
                admin_text += _("admin_entry", lang, 
                    name=super_admin.name or "Unknown",
                    customer_code=super_admin.customer_code,
                    type=_("admin_type_super", lang),
                    telegram_id=super_admin.telegram_id
                ) + "\n" + "─" * 30 + "\n"
        
        # Add database admins
        for admin in db_admins:
            admin_type = _("admin_type_temporary", lang) if admin.is_temporary_admin else _("admin_type_permanent", lang)
            admin_text += _("admin_entry", lang,
                name=admin.name or "Unknown",
                customer_code=admin.customer_code,
                type=admin_type,
                telegram_id=admin.telegram_id
            ) + "\n" + "─" * 30 + "\n"
        
        if len(db_admins) == 0 and len(ADMINS) == 0:
            admin_text = _("no_admins_found", lang)
        
        await callback.message.edit_text(
            admin_text[:4000],  # Telegram message limit
            reply_markup=get_admin_management_keyboard(lang)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in list admins handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery, session: AsyncSession):
    """Handle admin statistics"""
    try:
        user_id = callback.from_user.id
        
        if not is_super_admin(user_id):
            await callback.answer(_("unauthorized"))
            return
        
        # Get admin's language preference
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        admin_user = result.scalar_one_or_none()
        lang = admin_user.language if admin_user else "ar"
        
        # Get statistics
        total_db_admins_result = await session.execute(
            select(func.count(User.id)).where(User.is_admin == True)
        )
        total_db_admins = total_db_admins_result.scalar()
        
        permanent_admins_result = await session.execute(
            select(func.count(User.id)).where(
                User.is_admin == True,
                User.is_temporary_admin == False
            )
        )
        permanent_admins = permanent_admins_result.scalar()
        
        temporary_admins_result = await session.execute(
            select(func.count(User.id)).where(User.is_temporary_admin == True)
        )
        temporary_admins = temporary_admins_result.scalar()
        
        super_admins_count = len(ADMINS)
        total_admins = total_db_admins + super_admins_count
        
        # Security recommendation
        security_msg = _("good_security", lang)
        if permanent_admins + super_admins_count <= 1:
            security_msg = _("consider_more_admins", lang)
        
        stats_text = (
            f"{_('admin_statistics', lang)}\n\n"
            f"{_('total_admins', lang, count=total_admins)}\n"
            f"{_('super_admins', lang, count=super_admins_count)}\n"
            f"{_('permanent_admins', lang, count=permanent_admins)}\n"
            f"{_('temporary_admins', lang, count=temporary_admins)}\n\n"
            f"{_('security_recommendation', lang, message=security_msg)}"
        )
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_admin_management_keyboard(lang)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in admin stats handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data == "admin_add_permanent")
async def admin_add_permanent_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle adding permanent admin"""
    try:
        user_id = callback.from_user.id
        
        if not is_super_admin(user_id):
            await callback.answer(_("unauthorized"))
            return
        
        # Get admin's language preference
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        admin_user = result.scalar_one_or_none()
        lang = admin_user.language if admin_user else "ar"
        
        await state.set_state(AdminStates.waiting_for_user_id)
        await state.update_data(action="add_permanent", lang=lang)
        
        await callback.message.edit_text(_("enter_user_id", lang))
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in add permanent admin handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data == "admin_add_temporary")
async def admin_add_temporary_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle adding temporary admin"""
    try:
        user_id = callback.from_user.id
        
        if not is_super_admin(user_id):
            await callback.answer(_("unauthorized"))
            return
        
        # Get admin's language preference
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        admin_user = result.scalar_one_or_none()
        lang = admin_user.language if admin_user else "ar"
        
        await state.set_state(AdminStates.waiting_for_user_id)
        await state.update_data(action="add_temporary", lang=lang)
        
        await callback.message.edit_text(_("enter_user_id", lang))
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in add temporary admin handler: {e}")
        await callback.answer(_("error"))

@router.callback_query(F.data == "admin_remove_admin")
async def admin_remove_admin_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle removing admin"""
    try:
        user_id = callback.from_user.id
        
        if not is_super_admin(user_id):
            await callback.answer(_("unauthorized"))
            return
        
        # Get admin's language preference
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        admin_user = result.scalar_one_or_none()
        lang = admin_user.language if admin_user else "ar"
        
        await state.set_state(AdminStates.waiting_for_user_id)
        await state.update_data(action="remove_admin", lang=lang)
        
        await callback.message.edit_text(_("enter_user_id", lang))
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in remove admin handler: {e}")
        await callback.answer(_("error"))

@router.message(AdminStates.waiting_for_user_id)
async def process_user_id_handler(message: Message, state: FSMContext, session: AsyncSession):
    """Process user ID input for admin operations"""
    try:
        data = await state.get_data()
        action = data.get("action")
        lang = data.get("lang", "ar")
        current_admin_id = message.from_user.id
        
        # Validate user ID
        try:
            target_user_id = int(message.text.strip())
        except ValueError:
            await message.answer(_("error", lang))
            return
        
        # Check if target user exists and is registered
        result = await session.execute(
            select(User).where(User.telegram_id == target_user_id)
        )
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            await message.answer(_("user_not_found", lang))
            return
        
        if not target_user.is_registered:
            await message.answer(_("user_not_registered", lang))
            return
        
        if action == "add_permanent":
            # Check if user is already admin
            if target_user.is_admin or target_user_id in ADMINS:
                await message.answer(_("user_already_admin", lang))
                await state.clear()
                return
            
            # Add permanent admin
            target_user.is_admin = True
            target_user.is_temporary_admin = False
            await session.commit()
            
            # Log action
            await log_admin_action(
                session, "add_permanent_admin", current_admin_id, 
                target_user_id, f"Added {target_user.name} as permanent admin"
            )
            
            await message.answer(_("admin_added_successfully", lang))
            
        elif action == "add_temporary":
            # Check if user is already admin
            if target_user.is_admin or target_user_id in ADMINS:
                await message.answer(_("user_already_admin", lang))
                await state.clear()
                return
            
            # Add temporary admin
            target_user.is_admin = True
            target_user.is_temporary_admin = True
            await session.commit()
            
            # Log action
            await log_admin_action(
                session, "add_temporary_admin", current_admin_id,
                target_user_id, f"Added {target_user.name} as temporary admin"
            )
            
            await message.answer(_("admin_added_successfully", lang))
            
        elif action == "remove_admin":
            # Check if user is super admin (cannot be removed)
            if target_user_id in ADMINS:
                await message.answer(_("cannot_remove_super_admin", lang))
                await state.clear()
                return
            
            # Check if user is admin
            if not target_user.is_admin:
                await message.answer(_("user_not_admin", lang))
                await state.clear()
                return
            
            # Remove admin
            target_user.is_admin = False
            target_user.is_temporary_admin = False
            await session.commit()
            
            # Log action
            await log_admin_action(
                session, "remove_admin", current_admin_id,
                target_user_id, f"Removed {target_user.name} from admin"
            )
            
            await message.answer(_("admin_removed_successfully", lang))
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in process user ID handler: {e}")
        await message.answer(_("error"))
        await state.clear()

# Additional admin commands will be handled by other handlers (companies, broadcast, etc.)