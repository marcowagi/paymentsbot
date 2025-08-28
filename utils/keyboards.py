"""
Common keyboard layouts for the Telegram Finance Bot with Guest Mode support
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from utils.i18n import _

def get_main_menu_keyboard(lang: str = "ar", is_registered: bool = True) -> ReplyKeyboardMarkup:
    """Get main menu keyboard based on user registration status"""
    builder = ReplyKeyboardBuilder()
    
    if is_registered:
        # Full menu for registered users
        if lang == "ar":
            builder.add(KeyboardButton(text="🏦 طلب إيداع"))
            builder.add(KeyboardButton(text="💸 طلب سحب"))
            builder.add(KeyboardButton(text="👤 حسابي"))
            builder.add(KeyboardButton(text="📑 طلباتي"))
            builder.add(KeyboardButton(text="📩 شكوى"))
            builder.add(KeyboardButton(text="🔄 تغيير العملة"))
            builder.add(KeyboardButton(text="🌐 تغيير اللغة"))
            builder.add(KeyboardButton(text="🆘 دعم"))
            builder.add(KeyboardButton(text="♻️ إعادة تعيين"))
        else:
            builder.add(KeyboardButton(text="🏦 Request Deposit"))
            builder.add(KeyboardButton(text="💸 Request Withdrawal"))
            builder.add(KeyboardButton(text="👤 My Account"))
            builder.add(KeyboardButton(text="📑 My Requests"))
            builder.add(KeyboardButton(text="📩 Complaint"))
            builder.add(KeyboardButton(text="🔄 Change Currency"))
            builder.add(KeyboardButton(text="🌐 Change Language"))
            builder.add(KeyboardButton(text="🆘 Support"))
            builder.add(KeyboardButton(text="♻️ Reset"))
    else:
        # Limited menu for guest users
        if lang == "ar":
            builder.add(KeyboardButton(text="👤 حسابي"))
            builder.add(KeyboardButton(text="🌐 تغيير اللغة"))
            builder.add(KeyboardButton(text="🔄 تغيير العملة"))
            builder.add(KeyboardButton(text="🆘 دعم"))
            builder.add(KeyboardButton(text="♻️ إعادة تعيين"))
        else:
            builder.add(KeyboardButton(text="👤 My Account"))
            builder.add(KeyboardButton(text="🌐 Change Language"))
            builder.add(KeyboardButton(text="🔄 Change Currency"))
            builder.add(KeyboardButton(text="🆘 Support"))
            builder.add(KeyboardButton(text="♻️ Reset"))
    
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup(resize_keyboard=True)

def get_registration_keyboard(lang: str = "ar") -> InlineKeyboardMarkup:
    """Get registration choice keyboard"""
    builder = InlineKeyboardBuilder()
    
    if lang == "ar":
        builder.add(InlineKeyboardButton(text="📝 تسجيل حساب جديد", callback_data="register"))
        builder.add(InlineKeyboardButton(text="👁️ تصفح كضيف", callback_data="guest_mode"))
    else:
        builder.add(InlineKeyboardButton(text="📝 Register New Account", callback_data="register"))
        builder.add(InlineKeyboardButton(text="👁️ Browse as Guest", callback_data="guest_mode"))
    
    builder.adjust(1)  # 1 button per row
    return builder.as_markup()

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Get language selection keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🇸🇦 العربية", callback_data="lang_ar"))
    builder.add(InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en"))
    return builder.as_markup()

def get_currency_keyboard() -> InlineKeyboardMarkup:
    """Get currency selection keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🇸🇦 SAR", callback_data="currency_SAR"))
    builder.add(InlineKeyboardButton(text="🇺🇸 USD", callback_data="currency_USD"))
    builder.add(InlineKeyboardButton(text="🇪🇺 EUR", callback_data="currency_EUR"))
    builder.add(InlineKeyboardButton(text="🇦🇪 AED", callback_data="currency_AED"))
    builder.adjust(2)
    return builder.as_markup()

def get_yes_no_keyboard(lang: str = "ar") -> InlineKeyboardMarkup:
    """Get yes/no confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    
    if lang == "ar":
        builder.add(InlineKeyboardButton(text="✅ نعم", callback_data="confirm_yes"))
        builder.add(InlineKeyboardButton(text="❌ لا", callback_data="confirm_no"))
    else:
        builder.add(InlineKeyboardButton(text="✅ Yes", callback_data="confirm_yes"))
        builder.add(InlineKeyboardButton(text="❌ No", callback_data="confirm_no"))
    
    return builder.as_markup()

def get_cancel_keyboard(lang: str = "ar") -> ReplyKeyboardMarkup:
    """Get cancel keyboard"""
    builder = ReplyKeyboardBuilder()
    
    if lang == "ar":
        builder.add(KeyboardButton(text="❌ إلغاء"))
    else:
        builder.add(KeyboardButton(text="❌ Cancel"))
    
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def get_admin_panel_keyboard(lang: str = "ar", permissions: list = None) -> InlineKeyboardMarkup:
    """Get admin panel keyboard based on user permissions"""
    builder = InlineKeyboardBuilder()
    permissions = permissions or []
    
    if lang == "ar":
        # Add buttons based on permissions
        builder.add(InlineKeyboardButton(text="📊 إحصائيات شاملة", callback_data="admin_statistics"))
        
        if "ApproveTx" in permissions:
            builder.add(InlineKeyboardButton(text="🗂️ طلبات معلقة", callback_data="admin_pending_requests"))
        
        if "ManageUsers" in permissions:
            builder.add(InlineKeyboardButton(text="👥 إدارة المستخدمين", callback_data="admin_manage_users"))
        
        if "ManagePayments" in permissions:
            builder.add(InlineKeyboardButton(text="🏢 إدارة الشركات", callback_data="admin_manage_companies"))
            builder.add(InlineKeyboardButton(text="💳 وسائل الدفع", callback_data="admin_payment_methods"))
        
        if "ManageAdmins" in permissions:
            builder.add(InlineKeyboardButton(text="👮 إدارة الأدمِن", callback_data="admin_manage_admins"))
        
        if "Broadcast" in permissions:
            builder.add(InlineKeyboardButton(text="📢 إرسال جماعي", callback_data="admin_broadcast"))
        
        if "Reports" in permissions:
            builder.add(InlineKeyboardButton(text="📊 تقرير Excel", callback_data="admin_excel_report"))
            builder.add(InlineKeyboardButton(text="💾 نسخة احتياطية", callback_data="admin_backup"))
        
        if "Settings" in permissions:
            builder.add(InlineKeyboardButton(text="🔧 إعدادات النظام", callback_data="admin_settings"))
        
        builder.add(InlineKeyboardButton(text="🏠 عودة للقائمة الرئيسية", callback_data="admin_main_menu"))
    else:
        # English version
        builder.add(InlineKeyboardButton(text="📊 Comprehensive Statistics", callback_data="admin_statistics"))
        
        if "ApproveTx" in permissions:
            builder.add(InlineKeyboardButton(text="🗂️ Pending Requests", callback_data="admin_pending_requests"))
        
        if "ManageUsers" in permissions:
            builder.add(InlineKeyboardButton(text="👥 Manage Users", callback_data="admin_manage_users"))
        
        if "ManagePayments" in permissions:
            builder.add(InlineKeyboardButton(text="🏢 Manage Companies", callback_data="admin_manage_companies"))
            builder.add(InlineKeyboardButton(text="💳 Payment Methods", callback_data="admin_payment_methods"))
        
        if "ManageAdmins" in permissions:
            builder.add(InlineKeyboardButton(text="👮 Manage Admins", callback_data="admin_manage_admins"))
        
        if "Broadcast" in permissions:
            builder.add(InlineKeyboardButton(text="📢 Broadcast Message", callback_data="admin_broadcast"))
        
        if "Reports" in permissions:
            builder.add(InlineKeyboardButton(text="📊 Excel Report", callback_data="admin_excel_report"))
            builder.add(InlineKeyboardButton(text="💾 Backup", callback_data="admin_backup"))
        
        if "Settings" in permissions:
            builder.add(InlineKeyboardButton(text="🔧 System Settings", callback_data="admin_settings"))
        
        builder.add(InlineKeyboardButton(text="🏠 Back to Main Menu", callback_data="admin_main_menu"))
    
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()

def get_companies_keyboard(companies, lang: str = "ar") -> InlineKeyboardMarkup:
    """Get companies selection keyboard"""
    builder = InlineKeyboardBuilder()
    
    for company in companies:
        name = company.name_ar if lang == "ar" else company.name_en
        builder.add(InlineKeyboardButton(text=name, callback_data=f"company_{company.id}"))
    
    # Add cancel button
    cancel_text = "❌ إلغاء" if lang == "ar" else "❌ Cancel"
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
    back_text = "🔙 رجوع" if lang == "ar" else "🔙 Back"
    cancel_text = "❌ إلغاء" if lang == "ar" else "❌ Cancel"
    builder.add(InlineKeyboardButton(text=back_text, callback_data="back"))
    builder.add(InlineKeyboardButton(text=cancel_text, callback_data="cancel"))
    
    builder.adjust(1)  # 1 button per row
    return builder.as_markup()

def get_request_status_keyboard(lang: str = "ar") -> InlineKeyboardMarkup:
    """Get request status filter keyboard"""
    builder = InlineKeyboardBuilder()
    
    if lang == "ar":
        builder.add(InlineKeyboardButton(text="⏳ معلق", callback_data="status_pending"))
        builder.add(InlineKeyboardButton(text="✅ مُعتمد", callback_data="status_approved"))
        builder.add(InlineKeyboardButton(text="❌ مرفوض", callback_data="status_rejected"))
        builder.add(InlineKeyboardButton(text="📋 الكل", callback_data="status_all"))
    else:
        builder.add(InlineKeyboardButton(text="⏳ Pending", callback_data="status_pending"))
        builder.add(InlineKeyboardButton(text="✅ Approved", callback_data="status_approved"))
        builder.add(InlineKeyboardButton(text="❌ Rejected", callback_data="status_rejected"))
        builder.add(InlineKeyboardButton(text="📋 All", callback_data="status_all"))
    
    builder.adjust(2)
    return builder.as_markup()