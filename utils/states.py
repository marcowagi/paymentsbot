"""
FSM States for conversation management in the Telegram Finance Bot
"""

from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

class DepositStates(StatesGroup):
    waiting_for_company = State()
    waiting_for_payment_method = State()
    waiting_for_amount = State()
    waiting_for_reference = State()
    waiting_for_receipt = State()
    waiting_for_confirmation = State()

class WithdrawStates(StatesGroup):
    waiting_for_company = State()
    waiting_for_payment_method = State()
    waiting_for_amount = State()
    waiting_for_address = State()
    waiting_for_confirmation = State()

class ComplaintStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_attachment = State()
    waiting_for_confirmation = State()

class AdminStates(StatesGroup):
    # User management
    waiting_for_user_search = State()
    waiting_for_user_action = State()
    
    # Request management
    waiting_for_request_action = State()
    waiting_for_admin_notes = State()
    
    # Company management
    waiting_for_company_name_ar = State()
    waiting_for_company_name_en = State()
    waiting_for_company_currency = State()
    
    # Payment method management
    waiting_for_payment_method_name_ar = State()
    waiting_for_payment_method_name_en = State()
    waiting_for_payment_method_type = State()
    waiting_for_payment_method_fields = State()
    
    # Broadcasting
    waiting_for_broadcast_message = State()
    waiting_for_broadcast_confirmation = State()
    
    # Admin management
    waiting_for_admin_user_id = State()
    waiting_for_admin_roles = State()
    
    # Reports
    waiting_for_report_filter = State()
    
    # Support channels
    waiting_for_support_channel_type = State()
    waiting_for_support_channel_value = State()

class UserSettingsStates(StatesGroup):
    waiting_for_name_change = State()
    waiting_for_phone_change = State()
    waiting_for_address_name = State()
    waiting_for_address_value = State()