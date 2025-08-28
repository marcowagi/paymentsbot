"""
Common keyboard layouts for the Telegram Finance Bot
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from utils.i18n import _

def get_main_menu_keyboard(lang: str = "ar") -> ReplyKeyboardMarkup:
    """Get main menu keyboard"""
    builder = ReplyKeyboardBuilder()
    
    # Main buttons with Arabic/English text
    if lang == "ar":
        builder.add(KeyboardButton(text="حسابي"))
        builder.add(KeyboardButton(text="إيداع"))
        builder.add(KeyboardButton(text="سحب"))
        builder.add(KeyboardButton(text="تغيير اللغة"))
        builder.add(KeyboardButton(text="الدعم"))
        builder.add(KeyboardButton(text="إعادة التعيين"))
    else:
        builder.add(KeyboardButton(text="My Account"))
        builder.add(KeyboardButton(text="Deposit"))
        builder.add(KeyboardButton(text="Withdraw"))
        builder.add(KeyboardButton(text="Change Language"))
        builder.add(KeyboardButton(text="Support"))
        builder.add(KeyboardButton(text="Reset"))
    
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup(resize_keyboard=True)

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Get language selection keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="العربية", callback_data="lang_ar"))
    builder.add(InlineKeyboardButton(text="English", callback_data="lang_en"))
    return builder.as_markup()

def get_yes_no_keyboard(lang: str = "ar") -> InlineKeyboardMarkup:
    """Get yes/no confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    
    if lang == "ar":
        builder.add(InlineKeyboardButton(text="نعم", callback_data="confirm_yes"))
        builder.add(InlineKeyboardButton(text="لا", callback_data="confirm_no"))
    else:
        builder.add(InlineKeyboardButton(text="Yes", callback_data="confirm_yes"))
        builder.add(InlineKeyboardButton(text="No", callback_data="confirm_no"))
    
    return builder.as_markup()

def get_cancel_keyboard(lang: str = "ar") -> ReplyKeyboardMarkup:
    """Get cancel keyboard"""
    builder = ReplyKeyboardBuilder()
    
    if lang == "ar":
        builder.add(KeyboardButton(text="إلغاء"))
    else:
        builder.add(KeyboardButton(text="Cancel"))
    
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def get_admin_panel_keyboard(lang: str = "ar") -> InlineKeyboardMarkup:
    """Get admin panel keyboard"""
    builder = InlineKeyboardBuilder()
    
    if lang == "ar":
        builder.add(InlineKeyboardButton(text="الطلبات المعلقة", callback_data="admin_pending_requests"))
        builder.add(InlineKeyboardButton(text="الشكاوى المعلقة", callback_data="admin_pending_complaints"))
        builder.add(InlineKeyboardButton(text="إدارة الشركات", callback_data="admin_manage_companies"))
        builder.add(InlineKeyboardButton(text="👮 إدارة المدراء", callback_data="admin_manage_admins"))
        builder.add(InlineKeyboardButton(text="الإعلانات", callback_data="admin_announcements"))
        builder.add(InlineKeyboardButton(text="البث", callback_data="admin_broadcast"))
        builder.add(InlineKeyboardButton(text="التقارير", callback_data="admin_reports"))
        builder.add(InlineKeyboardButton(text="النسخ الاحتياطية", callback_data="admin_backups"))
    else:
        builder.add(InlineKeyboardButton(text="Pending Requests", callback_data="admin_pending_requests"))
        builder.add(InlineKeyboardButton(text="Pending Complaints", callback_data="admin_pending_complaints"))
        builder.add(InlineKeyboardButton(text="Manage Companies", callback_data="admin_manage_companies"))
        builder.add(InlineKeyboardButton(text="👮 Manage Admins", callback_data="admin_manage_admins"))
        builder.add(InlineKeyboardButton(text="Announcements", callback_data="admin_announcements"))
        builder.add(InlineKeyboardButton(text="Broadcast", callback_data="admin_broadcast"))
        builder.add(InlineKeyboardButton(text="Reports", callback_data="admin_reports"))
        builder.add(InlineKeyboardButton(text="Backups", callback_data="admin_backups"))
    
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()

def get_companies_keyboard(companies, lang: str = "ar") -> InlineKeyboardMarkup:
    """Get companies selection keyboard"""
    builder = InlineKeyboardBuilder()
    
    for company in companies:
        name = company.name_ar if lang == "ar" else company.name_en
        builder.add(InlineKeyboardButton(text=name, callback_data=f"company_{company.id}"))
    
    # Add cancel button
    cancel_text = "إلغاء" if lang == "ar" else "Cancel"
    builder.add(InlineKeyboardButton(text=cancel_text, callback_data="cancel"))
    
    builder.adjust(1)  # 1 button per row
    return builder.as_markup()

def get_payment_methods_keyboard(payment_methods, lang: str = "ar") -> InlineKeyboardMarkup:
    """Get payment methods selection keyboard"""
    builder = InlineKeyboardBuilder()
    
    for method in payment_methods:
        name = method.name_ar if lang == "ar" else method.name_en
        builder.add(InlineKeyboardButton(text=name, callback_data=f"payment_{method.id}"))
    
    # Add back and cancel buttons
    back_text = "رجوع" if lang == "ar" else "Back"
    cancel_text = "إلغاء" if lang == "ar" else "Cancel"
    builder.add(InlineKeyboardButton(text=back_text, callback_data="back"))
    builder.add(InlineKeyboardButton(text=cancel_text, callback_data="cancel"))
    
    builder.adjust(1)  # 1 button per row
    return builder.as_markup()

def get_admin_management_keyboard(lang: str = "ar") -> InlineKeyboardMarkup:
    """Get admin management keyboard"""
    builder = InlineKeyboardBuilder()
    
    if lang == "ar":
        builder.add(InlineKeyboardButton(text="📋 عرض قائمة المدراء", callback_data="admin_list_admins"))
        builder.add(InlineKeyboardButton(text="➕ إضافة مدير دائم", callback_data="admin_add_permanent"))
        builder.add(InlineKeyboardButton(text="⏱️ إضافة مدير مؤقت", callback_data="admin_add_temporary"))
        builder.add(InlineKeyboardButton(text="➖ إزالة مدير", callback_data="admin_remove_admin"))
        builder.add(InlineKeyboardButton(text="📊 إحصائيات المدراء", callback_data="admin_stats"))
        builder.add(InlineKeyboardButton(text="↩️ العودة للوحة الأدمن", callback_data="admin_back_to_panel"))
    else:
        builder.add(InlineKeyboardButton(text="📋 View Admin List", callback_data="admin_list_admins"))
        builder.add(InlineKeyboardButton(text="➕ Add Permanent Admin", callback_data="admin_add_permanent"))
        builder.add(InlineKeyboardButton(text="⏱️ Add Temporary Admin", callback_data="admin_add_temporary"))
        builder.add(InlineKeyboardButton(text="➖ Remove Admin", callback_data="admin_remove_admin"))
        builder.add(InlineKeyboardButton(text="📊 Admin Statistics", callback_data="admin_stats"))
        builder.add(InlineKeyboardButton(text="↩️ Back to Admin Panel", callback_data="admin_back_to_panel"))
    
    builder.adjust(1)  # 1 button per row
    return builder.as_markup()