#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import csv
import urllib.request
import urllib.parse
import logging
import threading
import time
import zipfile
from datetime import datetime

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveDUXBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self.user_states = {}
        self.temp_company_data = {}  # إضافة المتغير المفقود
        self.init_files()
        self.admin_ids = self.get_admin_ids()
        
        # تحميل معرفات الأدمن من متغيرات البيئة
        admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
        if admin_ids_str:
            self.admin_user_ids = [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip().isdigit()]
        else:
            self.admin_user_ids = []
        
        # إدارة الأدمن المؤقت (للجلسة الواحدة)
        self.temp_admin_user_ids = []
        
        # نظام العملات
        self.currencies = {
            'SAR': {'name': 'الريال السعودي', 'symbol': 'ر.س', 'flag': '🇸🇦'},
            'AED': {'name': 'الدرهم الإماراتي', 'symbol': 'د.إ', 'flag': '🇦🇪'},
            'EGP': {'name': 'الجنيه المصري', 'symbol': 'ج.م', 'flag': '🇪🇬'},
            'KWD': {'name': 'الدينار الكويتي', 'symbol': 'د.ك', 'flag': '🇰🇼'},
            'QAR': {'name': 'الريال القطري', 'symbol': 'ر.ق', 'flag': '🇶🇦'},
            'BHD': {'name': 'الدينار البحريني', 'symbol': 'د.ب', 'flag': '🇧🇭'},
            'OMR': {'name': 'الريال العماني', 'symbol': 'ر.ع', 'flag': '🇴🇲'},
            'JOD': {'name': 'الدينار الأردني', 'symbol': 'د.أ', 'flag': '🇯🇴'},
            'LBP': {'name': 'الليرة اللبنانية', 'symbol': 'ل.ل', 'flag': '🇱🇧'},
            'IQD': {'name': 'الدينار العراقي', 'symbol': 'د.ع', 'flag': '🇮🇶'},
            'SYP': {'name': 'الليرة السورية', 'symbol': 'ل.س', 'flag': '🇸🇾'},
            'MAD': {'name': 'الدرهم المغربي', 'symbol': 'د.م', 'flag': '🇲🇦'},
            'TND': {'name': 'الدينار التونسي', 'symbol': 'د.ت', 'flag': '🇹🇳'},
            'DZD': {'name': 'الدينار الجزائري', 'symbol': 'د.ج', 'flag': '🇩🇿'},
            'LYD': {'name': 'الدينار الليبي', 'symbol': 'د.ل', 'flag': '🇱🇾'},
            'USD': {'name': 'الدولار الأمريكي', 'symbol': '$', 'flag': '🇺🇸'},
            'EUR': {'name': 'اليورو', 'symbol': '€', 'flag': '🇪🇺'},
            'TRY': {'name': 'الليرة التركية', 'symbol': '₺', 'flag': '🇹🇷'}
        }
        
        logger.info(f"تم تحميل {len(self.admin_user_ids)} مدير دائم: {self.admin_user_ids}")
        
        # بدء نظام النسخ الاحتياطي التلقائي
        self.start_backup_scheduler()
        
    def init_files(self):
        """إنشاء جميع ملفات النظام"""
        # ملف المستخدمين
        if not os.path.exists('users.csv'):
            with open('users.csv', 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['telegram_id', 'name', 'phone', 'customer_id', 'language', 'date', 'is_banned', 'ban_reason', 'currency'])
        
        # ملف المعاملات المتقدم
        if not os.path.exists('transactions.csv'):
            with open('transactions.csv', 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'customer_id', 'telegram_id', 'name', 'type', 'company', 'wallet_number', 'amount', 'exchange_address', 'status', 'date', 'admin_note', 'processed_by'])
        
        # ملف الشركات
        if not os.path.exists('companies.csv'):
            with open('companies.csv', 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'name', 'type', 'details', 'is_active'])
                # شركات افتراضية
                companies = [
                    ['1', 'STC Pay', 'both', 'محفظة إلكترونية', 'active'],
                    ['2', 'البنك الأهلي', 'deposit', 'حساب بنكي رقم: 1234567890', 'active'],
                    ['3', 'فودافون كاش', 'both', 'محفظة إلكترونية', 'active'],
                    ['4', 'بنك الراجحي', 'deposit', 'حساب بنكي رقم: 0987654321', 'active'],
                    ['5', 'مدى البنك الأهلي', 'withdraw', 'رقم الحساب للسحب', 'active']
                ]
                for company in companies:
                    writer.writerow(company)
        
        # ملف عناوين الصرافة
        if not os.path.exists('exchange_addresses.csv'):
            with open('exchange_addresses.csv', 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'address', 'is_active'])
                writer.writerow(['1', 'شارع الملك فهد، الرياض، مقابل مول الرياض - الدور الأول', 'yes'])
        
        # ملف الشكاوى
        if not os.path.exists('complaints.csv'):
            with open('complaints.csv', 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'customer_id', 'message', 'status', 'date', 'admin_response'])
        
        # ملف إعدادات النظام
        if not os.path.exists('system_settings.csv'):
            with open('system_settings.csv', 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['setting_key', 'setting_value', 'description'])
                settings = [
                    ['min_deposit', '50', 'أقل مبلغ إيداع'],
                    ['min_withdrawal', '100', 'أقل مبلغ سحب'],
                    ['max_daily_withdrawal', '10000', 'أقصى سحب يومي'],
                    ['support_phone', '+966501234567', 'رقم الدعم'],
                    ['company_name', 'DUX', 'اسم الشركة'],
                    ['default_currency', 'SAR', 'العملة الافتراضية']
                ]
                for setting in settings:
                    writer.writerow(setting)
        
        logger.info("تم إنشاء جميع ملفات النظام بنجاح")
        
    def api_call(self, method, data=None):
        """استدعاء API مُحسن"""
        url = f"{self.api_url}/{method}"
        try:
            if data:
                json_data = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=json_data)
                req.add_header('Content-Type', 'application/json')
            else:
                req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"خطأ في API: {e}")
            return None
    
    def send_message(self, chat_id, text, keyboard=None):
        """إرسال رسالة"""
        data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
        if keyboard:
            data['reply_markup'] = keyboard
        return self.api_call('sendMessage', data)
    
    def get_updates(self):
        """جلب التحديثات"""
        url = f"{self.api_url}/getUpdates?offset={self.offset + 1}&timeout=10"
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"خطأ في جلب التحديثات: {e}")
            return None
    
    def get_admin_ids(self):
        """جلب معرفات الأدمن"""
        admin_ids = os.getenv('ADMIN_USER_IDS', '').split(',')
        return [admin_id.strip() for admin_id in admin_ids if admin_id.strip()]
    
    def is_admin(self, telegram_id):
        """فحص صلاحية الأدمن"""
        return (str(telegram_id) in self.admin_ids or 
                int(telegram_id) in self.admin_user_ids or 
                int(telegram_id) in self.temp_admin_user_ids)
    
    def notify_admins(self, message):
        """إشعار جميع الأدمن"""
        for admin_id in self.admin_ids:
            try:
                self.send_message(admin_id, message, self.admin_keyboard())
            except:
                pass
    
    def find_user(self, telegram_id):
        """البحث عن مستخدم"""
        try:
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['telegram_id'] == str(telegram_id):
                        return row
        except:
            pass
        return None
    
    def get_companies(self, service_type=None):
        """جلب الشركات النشطة"""
        companies = []
        try:
            # التأكد من وجود الملف
            with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # التأكد من أن الشركة نشطة
                    if row.get('is_active', '').lower() in ['active', 'yes', '1', 'true']:
                        # فلترة حسب نوع الخدمة
                        if not service_type:
                            companies.append(row)
                        elif row['type'] == service_type or row['type'] == 'both':
                            companies.append(row)
        except FileNotFoundError:
            # إنشاء ملف الشركات إذا لم يكن موجوداً
            with open('companies.csv', 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'name', 'type', 'details', 'is_active'])
        except Exception as e:
            # تسجيل الخطأ للتشخيص
            logger.error(f"خطأ في قراءة ملف الشركات: {e}")
        
        return companies
    
    def get_exchange_address(self):
        """جلب عنوان الصرافة النشط"""
        try:
            with open('exchange_addresses.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['is_active'] == 'yes':
                        return row['address']
        except:
            pass
        return "العنوان غير متوفر حالياً"
    
    def get_setting(self, key):
        """جلب إعداد النظام"""
        try:
            with open('system_settings.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['setting_key'] == key:
                        return row['setting_value']
        except:
            pass
        return None
    
    def main_keyboard(self, lang='ar', user_id=None):
        """القائمة الرئيسية"""
        if lang == 'ar':
            keyboard = [
                [{'text': '💰 طلب إيداع'}, {'text': '💸 طلب سحب'}],
                [{'text': '📋 طلباتي'}, {'text': '👤 حسابي'}],
                [{'text': '📨 شكوى'}, {'text': '🆘 دعم'}],
                [{'text': '💱 تغيير العملة'}, {'text': '🔄 إعادة تعيين'}],
                [{'text': '🇺🇸 English'}],
                [{'text': '/admin'}]
            ]
            
            # إضافة زر التسجيل للمستخدمين غير المسجلين
            if user_id and not self.find_user(user_id):
                keyboard.insert(-2, [{'text': '📝 تسجيل حساب'}])
            
            return {
                'keyboard': keyboard,
                'resize_keyboard': True
            }
        else:
            keyboard = [
                [{'text': '💰 Deposit Request'}, {'text': '💸 Withdrawal Request'}],
                [{'text': '📋 My Requests'}, {'text': '👤 Profile'}],
                [{'text': '📨 Complaint'}, {'text': '🆘 Support'}],
                [{'text': '💱 Change Currency'}, {'text': '🔄 Reset System'}],
                [{'text': '🇸🇦 العربية'}],
                [{'text': '/admin'}]
            ]
            
            # إضافة زر التسجيل للمستخدمين غير المسجلين
            if user_id and not self.find_user(user_id):
                keyboard.insert(-2, [{'text': '📝 Register Account'}])
            
            return {
                'keyboard': keyboard,
                'resize_keyboard': True
            }
    
    def admin_keyboard(self):
        """لوحة مفاتيح الأدمن الشاملة"""
        return {
            'keyboard': [
                [{'text': '📋 الطلبات المعلقة'}, {'text': '✅ طلبات مُوافقة'}],
                [{'text': '👥 إدارة المستخدمين'}, {'text': '🔍 البحث'}],
                [{'text': '💳 وسائل الدفع'}, {'text': '📊 الإحصائيات'}],
                [{'text': '📊 تقرير Excel احترافي'}, {'text': '💾 نسخة احتياطية فورية'}],
                [{'text': '📢 إرسال جماعي'}, {'text': '🚫 حظر مستخدم'}],
                [{'text': '✅ إلغاء حظر'}, {'text': '📝 إضافة شركة'}],
                [{'text': '⚙️ إدارة الشركات'}, {'text': '📍 إدارة العناوين'}],
                [{'text': '🛠️ تعديل بيانات الدعم'}],
                [{'text': '⚙️ إعدادات النظام'}, {'text': '📨 الشكاوى'}],
                [{'text': '📋 نسخ أوامر سريعة'}, {'text': '📧 إرسال رسالة لعميل'}],
                [{'text': '💾 نسخة احتياطية فورية'}, {'text': '🔄 إعادة تعيين النظام'}],
                [{'text': '👥 إدارة الأدمن'}],
                [{'text': '🏠 القائمة الرئيسية'}]
            ],
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
    
    def companies_keyboard(self, service_type):
        """لوحة اختيار الشركات مع تحديث فوري"""
        companies = self.get_companies(service_type)
        keyboard = []
        
        # إضافة أزرار الشركات
        for company in companies:
            keyboard.append([{'text': f"🏢 {company['name']}"}])
        
        # إضافة أزرار العودة وإعادة التعيين
        keyboard.append([{'text': '🔙 العودة للقائمة الرئيسية'}, {'text': '🔄 إعادة تعيين النظام'}])
        
        return {'keyboard': keyboard, 'resize_keyboard': True, 'one_time_keyboard': True}
    
    def handle_start(self, message):
        """معالج بداية المحادثة"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        
        # فحص إذا كان المستخدم موجود
        user = self.find_user(user_id)
        if user:
            if user.get('is_banned') == 'yes':
                ban_reason = user.get('ban_reason', 'غير محدد')
                self.send_message(chat_id, f"❌ تم حظر حسابك\nالسبب: {ban_reason}\n\nللاستفسار تواصل مع الإدارة")
                return
            
            welcome_text = f"مرحباً بعودتك {user['name']}! 👋\n🆔 رقم العميل: {user['customer_id']}"
            self.send_message(chat_id, welcome_text, self.main_keyboard(user.get('language', 'ar'), user_id))
        else:
            welcome_text = """مرحباً بك في نظام DUX المالي المتقدم! 👋

🔹 خدمات الإيداع والسحب
🔹 دعم فني متخصص
🔹 أمان وموثوقية عالية

يرجى إرسال اسمك الكامل للتسجيل:"""
            
            # كيبورد للمستخدمين الجدد مع خيار التخطي
            new_user_keyboard = {
                'keyboard': [
                    [{'text': '⏭️ تخطي التسجيل'}],
                    [{'text': '🔄 إعادة تعيين النظام'}]
                ],
                'resize_keyboard': True,
                'one_time_keyboard': True
            }
            
            self.send_message(chat_id, welcome_text, new_user_keyboard)
            self.user_states[user_id] = 'registering_name'
    
    def handle_registration(self, message):
        """معالجة التسجيل"""
        user_id = message['from']['id']
        state = self.user_states.get(user_id)
        
        if state == 'registering_name':
            name = message['text'].strip()
            
            # التحقق من أزرار الإدارة
            if name == '⏭️ تخطي التسجيل':
                # إنهاء حالة التسجيل والانتقال للقائمة الرئيسية
                if user_id in self.user_states:
                    del self.user_states[user_id]
                
                skip_text = """✅ تم تخطي التسجيل!

يمكنك استخدام النظام كزائر. لاحقاً يمكنك التسجيل لحفظ بياناتك.

⚠️ ملاحظة: بدون تسجيل، لن تتمكن من:
• حفظ طلباتك
• تتبع حالة المعاملات
• الوصول للدعم الفني المخصص"""

                self.send_message(message['chat']['id'], skip_text, self.main_keyboard('ar', user_id))
                return
            elif name == '❌ إلغاء التسجيل':
                # إلغاء التسجيل والعودة للقائمة الرئيسية
                if user_id in self.user_states:
                    del self.user_states[user_id]
                
                cancel_text = """❌ تم إلغاء التسجيل

يمكنك إعادة المحاولة في أي وقت باستخدام زر "📝 تسجيل حساب" """

                self.send_message(message['chat']['id'], cancel_text, self.main_keyboard('ar', user_id))
                return
            
            if len(name) < 2:
                self.send_message(message['chat']['id'], "❌ اسم قصير جداً. يرجى إدخال اسم صحيح:")
                return
            
            self.user_states[user_id] = f'registering_phone_{name}'
            
            # كيبورد مشاركة جهة الاتصال
            contact_keyboard = {
                'keyboard': [
                    [{'text': '📱 مشاركة رقم الهاتف', 'request_contact': True}],
                    [{'text': '✍️ كتابة الرقم يدوياً'}],
                    [{'text': '🔄 إعادة تعيين النظام'}]
                ],
                'resize_keyboard': True,
                'one_time_keyboard': True
            }
            
            phone_message = """ممتاز! الآن أرسل رقم هاتفك:

📱 يمكنك مشاركة رقمك مباشرة بالضغط على "📱 مشاركة رقم الهاتف"
✍️ أو اكتب الرقم يدوياً مع رمز البلد (مثال: +966501234567)"""
            
            self.send_message(message['chat']['id'], phone_message, contact_keyboard)
            
        elif state.startswith('registering_phone_'):
            name = state.replace('registering_phone_', '')
            
            # التحقق من نوع الرسالة
            if 'contact' in message:
                # مشاركة جهة الاتصال
                phone = message['contact']['phone_number']
                if not phone.startswith('+'):
                    phone = '+' + phone
            elif 'text' in message:
                text = message['text'].strip()
                
                if text == '✍️ كتابة الرقم يدوياً':
                    manual_text = """✍️ اكتب رقم هاتفك مع رمز البلد:

مثال: +966501234567
مثال: +201234567890"""
                    self.send_message(message['chat']['id'], manual_text)
                    return
                
                phone = text
                if len(phone) < 10:
                    self.send_message(message['chat']['id'], "❌ رقم هاتف غير صحيح. يرجى إدخال رقم صحيح مع رمز البلد:")
                    return
            else:
                self.send_message(message['chat']['id'], "❌ يرجى مشاركة جهة الاتصال أو كتابة الرقم:")
                return
            
            # إنشاء رقم عميل تلقائي
            customer_id = f"C{str(int(datetime.now().timestamp()))[-6:]}"
            
            # حفظ المستخدم
            with open('users.csv', 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([user_id, name, phone, customer_id, 'ar', 
                               datetime.now().strftime('%Y-%m-%d'), 'no', ''])
            
            welcome_text = f"""✅ تم التسجيل بنجاح!

👤 الاسم: {name}
📱 الهاتف: {phone}
🆔 رقم العميل: {customer_id}
📅 تاريخ التسجيل: {datetime.now().strftime('%Y-%m-%d')}

يمكنك الآن استخدام جميع الخدمات المالية:"""
            
            self.send_message(message['chat']['id'], welcome_text, self.main_keyboard())
            del self.user_states[user_id]
            
            # إشعار الأدمن بعضو جديد
            admin_msg = f"""🆕 عضو جديد انضم للنظام

👤 الاسم: {name}
📱 الهاتف: {phone}
🆔 رقم العميل: {customer_id}
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
            self.notify_admins(admin_msg)
    
    def create_deposit_request(self, message):
        """إنشاء طلب إيداع"""
        user = self.find_user(message['from']['id'])
        if not user:
            return
        
        # عرض الشركات المتاحة للإيداع مع تحديث فوري
        deposit_companies = self.get_companies('deposit')
        if not deposit_companies:
            self.send_message(message['chat']['id'], "❌ لا توجد شركات متاحة للإيداع حالياً\n\nتواصل مع الإدارة لإضافة شركات الإيداع")
            return
        
        companies_text = "💰 طلب إيداع جديد\n\n🏢 اختر الشركة للإيداع:\n\n"
        for company in deposit_companies:
            type_display = {'deposit': 'إيداع', 'withdraw': 'سحب', 'both': 'الكل'}.get(company['type'], company['type'])
            companies_text += f"🔹 {company['name']} ({type_display}) - {company['details']}\n"
        
        companies_text += f"\n📊 إجمالي الشركات المتاحة: {len(deposit_companies)}"
        
        self.send_message(message['chat']['id'], companies_text, self.companies_keyboard('deposit'))
        self.user_states[message['from']['id']] = 'selecting_deposit_company'
    
    def create_withdrawal_request(self, message):
        """إنشاء طلب سحب"""
        user = self.find_user(message['from']['id'])
        if not user:
            return
        
        # عرض الشركات المتاحة للسحب مع تحديث فوري
        withdraw_companies = self.get_companies('withdraw')
        if not withdraw_companies:
            self.send_message(message['chat']['id'], "❌ لا توجد شركات متاحة للسحب حالياً\n\nتواصل مع الإدارة لإضافة شركات السحب")
            return
        
        companies_text = "💸 طلب سحب جديد\n\n🏢 اختر الشركة للسحب:\n\n"
        for company in withdraw_companies:
            type_display = {'deposit': 'إيداع', 'withdraw': 'سحب', 'both': 'الكل'}.get(company['type'], company['type'])
            companies_text += f"🔹 {company['name']} ({type_display}) - {company['details']}\n"
        
        companies_text += f"\n📊 إجمالي الشركات المتاحة: {len(withdraw_companies)}"
        
        self.send_message(message['chat']['id'], companies_text, self.companies_keyboard('withdraw'))
        self.user_states[message['from']['id']] = 'selecting_withdraw_company'
    
    def process_deposit_flow(self, message):
        """معالجة تدفق الإيداع الكامل"""
        user_id = message['from']['id']
        state = self.user_states.get(user_id, '')
        text = message['text']
        
        if state == 'selecting_deposit_company':
            # إزالة الرمز التعبيري من اسم الشركة
            selected_company_name = text.replace('🏢 ', '')
            
            # البحث عن الشركة المختارة
            companies = self.get_companies('deposit')
            selected_company = None
            for company in companies:
                if company['name'] == selected_company_name:
                    selected_company = company
                    break
            
            if not selected_company:
                self.send_message(message['chat']['id'], "❌ اختيار غير صحيح. يرجى اختيار شركة من القائمة:")
                return
            
            # عرض وسائل الدفع للشركة المختارة
            self.show_payment_method_selection(message, selected_company['id'], 'deposit')
            
        elif state.startswith('deposit_wallet_'):
            parts = state.split('_', 3)
            company_id = parts[2]
            company_name = parts[3] if len(parts) > 3 else ''
            method_id = parts[4] if len(parts) > 4 else ''
            wallet_number = text.strip()
            
            if len(wallet_number) < 5:
                self.send_message(message['chat']['id'], "❌ رقم المحفظة/الحساب قصير جداً. يرجى إدخال رقم صحيح:")
                return
            
            # الانتقال لمرحلة إدخال المبلغ
            user = self.find_user(user_id)
            user_currency = user.get('currency', self.get_setting('default_currency') or 'SAR')
            min_deposit = self.get_setting('min_deposit') or '50'
            currency_symbol = self.get_currency_symbol(user_currency)
            amount_text = f"""✅ تم حفظ رقم المحفظة: {wallet_number}

💰 الآن أدخل المبلغ المطلوب إيداعه:

📌 أقل مبلغ للإيداع: {min_deposit} {currency_symbol}
💡 أدخل المبلغ بالأرقام فقط (مثال: 500)"""
            
            self.send_message(message['chat']['id'], amount_text)
            self.user_states[user_id] = f'deposit_amount_{company_id}_{company_name}_{method_id}_{wallet_number}'
            
        elif state.startswith('deposit_amount_'):
            parts = state.split('_', 4)
            company_id = parts[2]
            company_name = parts[3]
            method_id = parts[4] if len(parts) > 4 else ''
            wallet_number = parts[5] if len(parts) > 5 else ''
            
            try:
                amount = float(text.strip())
                user = self.find_user(user_id)
                user_currency = user.get('currency', self.get_setting('default_currency') or 'SAR')
                min_deposit = float(self.get_setting('min_deposit') or '50')
                
                if amount < min_deposit:
                    currency_symbol = self.get_currency_symbol(user_currency)
                    self.send_message(message['chat']['id'], f"❌ أقل مبلغ للإيداع {min_deposit} {currency_symbol}. يرجى إدخال مبلغ أكبر:")
                    return
                    
            except ValueError:
                self.send_message(message['chat']['id'], "❌ مبلغ غير صحيح. يرجى إدخال رقم صحيح:")
                return
            
            # إنشاء المعاملة
            trans_id = f"DEP{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # حفظ المعاملة
            with open('transactions.csv', 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([trans_id, user['customer_id'], user['telegram_id'], user['name'], 
                               'deposit', company_name, wallet_number, amount, '', 'pending', 
                               datetime.now().strftime('%Y-%m-%d %H:%M'), '', '', user_currency])
            
            # رسالة تأكيد للعميل
            confirmation = f"""✅ تم إرسال طلب الإيداع بنجاح

🆔 رقم المعاملة: {trans_id}
👤 العميل: {user['name']} ({user['customer_id']})
🏢 الشركة: {company_name}
💳 رقم المحفظة: {wallet_number}
💰 المبلغ: {self.format_amount_with_currency(amount, user_currency)}
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
⏳ الحالة: في انتظار المراجعة

سيتم إشعارك فور مراجعة طلبك."""
            
            self.send_message(message['chat']['id'], confirmation, self.main_keyboard(user.get('language', 'ar')))
            del self.user_states[user_id]
            
            # إشعار فوري للأدمن بطلب الإيداع
            for admin_id in self.admin_ids:
                try:
                    admin_notification = f"""🔔 طلب إيداع جديد

🆔 رقم المعاملة: {trans_id}
👤 العميل: {user['name']} ({user['customer_id']})
🏢 الشركة: {company_name}
💳 رقم المحفظة: {wallet_number}
💰 المبلغ: {self.format_amount_with_currency(amount, user_currency)}
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}

لمراجعة الطلب: موافقة {trans_id} أو رفض {trans_id} [سبب]"""
                    self.send_message(admin_id, admin_notification)
                except:
                    pass
    
    def process_withdrawal_flow(self, message):
        """معالجة تدفق السحب الكامل"""
        user_id = message['from']['id']
        state = self.user_states.get(user_id, '')
        text = message['text']
        
        if state == 'selecting_withdraw_company':
            # إزالة الرمز التعبيري من اسم الشركة
            selected_company_name = text.replace('🏢 ', '')
            
            # البحث عن الشركة المختارة
            companies = self.get_companies('withdraw')
            selected_company = None
            for company in companies:
                if company['name'] == selected_company_name:
                    selected_company = company
                    break
            
            if not selected_company:
                self.send_message(message['chat']['id'], "❌ اختيار غير صحيح. يرجى اختيار شركة من القائمة:")
                return
            
            # عرض وسائل الدفع للشركة المختارة
            self.show_payment_method_selection(message, selected_company['id'], 'withdraw')
            
        elif state.startswith('withdraw_wallet_'):
            parts = state.split('_', 3)
            company_id = parts[2]
            company_name = parts[3] if len(parts) > 3 else ''
            method_id = parts[4] if len(parts) > 4 else ''
            wallet_number = text.strip()
            
            if len(wallet_number) < 5:
                self.send_message(message['chat']['id'], "❌ رقم المحفظة/الحساب قصير جداً. يرجى إدخال رقم صحيح:")
                return
            
            # الانتقال لمرحلة إدخال المبلغ
            user = self.find_user(user_id)
            user_currency = user.get('currency', self.get_setting('default_currency') or 'SAR')
            min_withdrawal = self.get_setting('min_withdrawal') or '100'
            max_withdrawal = self.get_setting('max_daily_withdrawal') or '10000'
            currency_symbol = self.get_currency_symbol(user_currency)
            amount_text = f"""✅ تم حفظ رقم المحفظة: {wallet_number}

💰 الآن أدخل المبلغ المطلوب سحبه:

📌 أقل مبلغ للسحب: {min_withdrawal} {currency_symbol}
📌 أقصى مبلغ يومي: {max_withdrawal} {currency_symbol}
💡 أدخل المبلغ بالأرقام فقط (مثال: 1000)"""
            
            self.send_message(message['chat']['id'], amount_text)
            self.user_states[user_id] = f'withdraw_amount_{company_id}_{company_name}_{method_id}_{wallet_number}'
            
        elif state.startswith('withdraw_amount_'):
            parts = state.split('_', 4)
            company_id = parts[2]
            company_name = parts[3]
            method_id = parts[4] if len(parts) > 4 else ''
            wallet_number = parts[5] if len(parts) > 5 else ''
            
            try:
                amount = float(text.strip())
                user = self.find_user(user_id)
                user_currency = user.get('currency', self.get_setting('default_currency') or 'SAR')
                min_withdrawal = float(self.get_setting('min_withdrawal') or '100')
                max_withdrawal = float(self.get_setting('max_daily_withdrawal') or '10000')
                
                if amount < min_withdrawal:
                    currency_symbol = self.get_currency_symbol(user_currency)
                    self.send_message(message['chat']['id'], f"❌ أقل مبلغ للسحب {min_withdrawal} {currency_symbol}. يرجى إدخال مبلغ أكبر:")
                    return
                
                if amount > max_withdrawal:
                    currency_symbol = self.get_currency_symbol(user_currency)
                    self.send_message(message['chat']['id'], f"❌ أقصى مبلغ للسحب اليومي {max_withdrawal} {currency_symbol}. يرجى إدخال مبلغ أقل:")
                    return
                    
            except ValueError:
                self.send_message(message['chat']['id'], "❌ مبلغ غير صحيح. يرجى إدخال رقم صحيح:")
                return
            
            # عرض عنوان السحب الثابت وطلب كود التأكيد
            withdrawal_address = self.get_exchange_address()
            
            currency_symbol = self.get_currency_symbol(user_currency)
            confirm_text = f"""✅ تم تأكيد المبلغ: {amount} {currency_symbol}

📍 عنوان السحب: 
{withdrawal_address}

🔐 يرجى إرسال كود التأكيد:"""
            
            self.send_message(message['chat']['id'], confirm_text)
            self.user_states[user_id] = f'withdraw_confirmation_code_{company_id}_{company_name}_{wallet_number}_{amount}_{withdrawal_address}'
            

        elif state.startswith('withdraw_confirmation_code_'):
            # فصل البيانات من الحالة
            data_part = state.replace('withdraw_confirmation_code_', '')
            parts = data_part.split('_')
            company_id = parts[0] if len(parts) > 0 else ''
            company_name = parts[1] if len(parts) > 1 else ''
            wallet_number = parts[2] if len(parts) > 2 else ''
            amount = parts[3] if len(parts) > 3 else ''
            withdrawal_address = parts[4] if len(parts) > 4 else ''
            confirmation_code = text.strip()
            
            if len(confirmation_code) < 3:
                self.send_message(message['chat']['id'], "❌ كود التأكيد قصير جداً. يرجى إدخال كود صحيح:")
                return
            
            # التأكيد النهائي مع أزرار
            user = self.find_user(user_id)
            user_currency = user.get('currency', self.get_setting('default_currency') or 'SAR')
            currency_symbol = self.get_currency_symbol(user_currency)
            final_confirm_text = f"""📋 مراجعة نهائية لطلب السحب:

🏢 الشركة: {company_name}
💳 رقم المحفظة: {wallet_number}
💰 المبلغ: {amount} {currency_symbol}
📍 عنوان السحب: {withdrawal_address}
🔐 كود التأكيد: {confirmation_code}

اختر من الأزرار أدناه:"""
            
            # إنشاء لوحة مفاتيح التأكيد
            confirm_keyboard = {
                'keyboard': [
                    [{'text': '✅ تأكيد الطلب'}, {'text': '❌ إلغاء'}],
                    [{'text': '🔄 إعادة تعيين النظام'}, {'text': '🏠 القائمة الرئيسية'}]
                ],
                'resize_keyboard': True,
                'one_time_keyboard': True
            }
            
            self.send_message(message['chat']['id'], final_confirm_text, confirm_keyboard)
            self.user_states[user_id] = f'withdraw_final_confirm_{company_id}_{company_name}_{wallet_number}_{amount}_{withdrawal_address}_{confirmation_code}'
            
        elif state.startswith('withdraw_final_confirm_'):
            # فصل البيانات من الحالة
            data_part = state.replace('withdraw_final_confirm_', '')
            parts = data_part.split('_')
            company_id = parts[0] if len(parts) > 0 else ''
            company_name = parts[1] if len(parts) > 1 else ''
            wallet_number = parts[2] if len(parts) > 2 else ''
            amount = parts[3] if len(parts) > 3 else ''
            withdrawal_address = parts[4] if len(parts) > 4 else ''
            confirmation_code = parts[5] if len(parts) > 5 else ''
            
            # معالجة أزرار التأكيد والإلغاء
            if text == '✅ تأكيد الطلب':
                # إنشاء المعاملة
                user = self.find_user(user_id)
                trans_id = f"WTH{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # حفظ المعاملة مع عنوان السحب وكود التأكيد
                with open('transactions.csv', 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow([trans_id, user['customer_id'], user['telegram_id'], user['name'], 
                                   'withdraw', company_name, wallet_number, amount, withdrawal_address, 'pending', 
                                   datetime.now().strftime('%Y-%m-%d %H:%M'), confirmation_code, '', user_currency])
                
                # رسالة تأكيد للعميل
                confirmation_msg = f"""✅ تم إرسال طلب السحب بنجاح

🆔 رقم المعاملة: {trans_id}
👤 العميل: {user['name']} ({user['customer_id']})
🏢 الشركة: {company_name}
💳 رقم المحفظة: {wallet_number}
💰 المبلغ: {amount} ريال
📍 عنوان السحب: {withdrawal_address}
🔐 كود التأكيد: {confirmation_code}
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
⏳ الحالة: في انتظار المراجعة

سيتم إشعارك فور الموافقة على طلبك."""
                
                self.send_message(message['chat']['id'], confirmation_msg, self.main_keyboard(user.get('language', 'ar')))
                del self.user_states[user_id]
                
                # إشعار فوري للأدمن
                for admin_id in self.admin_ids:
                    try:
                        admin_notification = f"""🔔 طلب سحب جديد

🆔 رقم المعاملة: {trans_id}
👤 العميل: {user['name']} ({user['customer_id']})
🏢 الشركة: {company_name}
💳 رقم المحفظة: {wallet_number}
💰 المبلغ: {amount} ريال
📍 عنوان السحب: {withdrawal_address}
🔐 كود التأكيد: {confirmation_code}
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}

لمراجعة الطلب: موافقة {trans_id} أو رفض {trans_id} [سبب]"""
                        self.send_message(admin_id, admin_notification)
                    except:
                        pass
                
            elif text == '❌ إلغاء':
                user = self.find_user(user_id)
                self.send_message(message['chat']['id'], "❌ تم إلغاء طلب السحب", self.main_keyboard(user.get('language', 'ar')))
                del self.user_states[user_id]
                
            elif text == '🏠 القائمة الرئيسية':
                user = self.find_user(user_id)
                del self.user_states[user_id]
                welcome_text = f"""🏠 مرحباً بك في النظام المالي

👤 العميل: {user.get('name', 'غير محدد')}
🆔 رقم العميل: {user.get('customer_id', 'غير محدد')}

اختر الخدمة المطلوبة:"""
                self.send_message(message['chat']['id'], welcome_text, self.main_keyboard(user.get('language', 'ar')))
                
            else:
                self.send_message(message['chat']['id'], "❌ يرجى اختيار من الأزرار المتاحة")
            
        # (معالج قديم محذوف لأن نظام السحب تم تحديثه)
    
    def show_user_transactions(self, message):
        """عرض معاملات المستخدم"""
        user = self.find_user(message['from']['id'])
        if not user:
            return
        
        transactions_text = f"📋 طلبات العميل: {user['name']}\n\n"
        found_transactions = False
        
        try:
            with open('transactions.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['customer_id'] == user['customer_id']:
                        found_transactions = True
                        status_emoji = "⏳" if row['status'] == 'pending' else "✅" if row['status'] == 'approved' else "❌"
                        type_emoji = "💰" if row['type'] == 'deposit' else "💸"
                        
                        transactions_text += f"{status_emoji} {type_emoji} {row['id']}\n"
                        transactions_text += f"🏢 {row['company']}\n"
                        transactions_text += f"💰 {row['amount']} ريال\n"
                        transactions_text += f"📅 {row['date']}\n"
                        
                        if row['status'] == 'rejected' and row.get('admin_note'):
                            transactions_text += f"📝 السبب: {row['admin_note']}\n"
                        elif row['status'] == 'approved':
                            transactions_text += f"✅ تمت الموافقة\n"
                        elif row['status'] == 'pending':
                            transactions_text += f"⏳ قيد المراجعة\n"
                        
                        transactions_text += "\n"
        except:
            pass
        
        if not found_transactions:
            transactions_text += "لا توجد معاملات سابقة"
        
        self.send_message(message['chat']['id'], transactions_text, self.main_keyboard(user.get('language', 'ar')))
    
    def show_user_profile(self, message):
        """عرض ملف المستخدم"""
        user = self.find_user(message['from']['id'])
        if not user:
            return
        
        profile_text = f"""👤 ملف العميل

🆔 رقم العميل: {user['customer_id']}
📛 الاسم: {user['name']}
📱 الهاتف: {user['phone']}
📅 تاريخ التسجيل: {user['date']}
🌐 اللغة: {'العربية' if user.get('language') == 'ar' else 'English'}

🔸 حالة الحساب: {'🚫 محظور' if user.get('is_banned') == 'yes' else '✅ نشط'}"""
        
        if user.get('is_banned') == 'yes' and user.get('ban_reason'):
            profile_text += f"\n📝 سبب الحظر: {user['ban_reason']}"
        
        self.send_message(message['chat']['id'], profile_text, self.main_keyboard(user.get('language', 'ar')))
    
    def handle_admin_panel(self, message):
        """لوحة تحكم الأدمن الرئيسية"""
        if not self.is_admin(message['from']['id']):
            return
        
        admin_welcome = """🔧 لوحة تحكم الأدمن

مرحباً بك في لوحة التحكم الشاملة
استخدم الأزرار أدناه للتنقل"""
        
        self.send_message(message['chat']['id'], admin_welcome, self.admin_keyboard())
    
    def process_message(self, message):
        """معالج الرسائل الرئيسي"""
        if 'text' not in message and 'contact' not in message:
            return
        
        text = message.get('text', '')
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        
        # بداية المحادثة
        if text == '/start':
            self.handle_start(message)
            return
            
        # معالجة زر إعادة التعيين أولاً (أولوية عالية)
        if text in ['🔄 إعادة تعيين النظام', '🔄 Reset System', '🔄 إعادة تعيين', '🆘 إصلاح شامل']:
            user = self.find_user(user_id)
            if user:
                self.super_reset_user_system(user_id, chat_id, user)
            else:
                self.handle_start(message)
            return
        
        # معالجة الحالات المختلفة
        if user_id in self.user_states:
            state = self.user_states[user_id]
            
            # معالجة التسجيل
            if isinstance(state, str) and state.startswith('registering'):
                self.handle_registration(message)
                return
            
            # معالجة الإيداع والسحب
            elif isinstance(state, str) and ('deposit' in state or 'withdraw' in state):
                if 'deposit' in state:
                    self.process_deposit_flow(message)
                else:
                    self.process_withdrawal_flow(message)
                return
            
            # معالجة اختيار وسيلة الدفع
            elif isinstance(state, dict) and state.get('step') == 'selecting_payment_method':
                self.handle_payment_method_selection(message, text)
                return
        
        # فحص المستخدم المسجل
        user = self.find_user(user_id)
        if not user:
            self.handle_start(message)
            return
        
        # فحص الحظر
        if user.get('is_banned') == 'yes':
            ban_reason = user.get('ban_reason', 'غير محدد')
            self.send_message(chat_id, f"❌ تم حظر حسابك\nالسبب: {ban_reason}")
            return
        
        # معالجة أوامر الأدمن
        if self.is_admin(user_id):
            if text == '/admin':
                self.handle_admin_panel(message)
                return
            
            # معالجة حالات الأدمن الخاصة
            if user_id in self.user_states:
                admin_state = self.user_states[user_id]
                if isinstance(admin_state, str):
                    if admin_state == 'admin_broadcasting':
                        self.send_broadcast_message(message, text)
                        return
                    elif admin_state.startswith('adding_company_'):
                        self.handle_company_wizard(message)
                        return
                    elif admin_state.startswith('editing_company_') or admin_state == 'selecting_company_edit':
                        self.handle_company_edit_wizard(message)
                        return
                    elif admin_state == 'confirming_company_delete':
                        self.handle_company_delete_confirmation(message)
                        return
                    elif admin_state.startswith('deleting_company_'):
                        company_id = admin_state.replace('deleting_company_', '')
                        self.finalize_company_delete(message, company_id)
                        return
                    elif admin_state == 'sending_user_message_id':
                        self.handle_user_message_id(message)
                        return
                    elif admin_state.startswith('sending_user_message_'):
                        customer_id = admin_state.replace('sending_user_message_', '')
                        self.handle_user_message_content(message, customer_id)
                        return
                    elif admin_state == 'selecting_method_to_edit':
                        self.handle_method_edit_selection(message)
                        return
                    elif admin_state == 'selecting_method_to_delete':
                        self.handle_method_delete_selection(message)
                        return
                    elif admin_state.startswith('editing_method_'):
                        method_id = admin_state.replace('editing_method_', '')
                        self.handle_method_edit_data(message, method_id)
                        return
                    elif admin_state == 'adding_payment_simple':
                        self.handle_simple_payment_company_selection(message)
                        return
                    elif admin_state.startswith('adding_payment_method_'):
                        self.handle_simple_payment_method_data(message)
                        return
                    elif admin_state == 'selecting_method_to_edit_simple':
                        self.handle_simple_method_edit_selection(message)
                        return
                    elif admin_state == 'selecting_method_to_delete_simple':
                        self.handle_simple_method_delete_selection(message)
                        return
                    elif admin_state.startswith('editing_method_simple_'):
                        method_id = admin_state.replace('editing_method_simple_', '')
                        self.handle_simple_method_edit_data(message, method_id)
                        return
                    elif admin_state == 'selecting_method_to_disable':
                        self.handle_method_disable_selection(message)
                        return
                    elif admin_state == 'selecting_method_to_enable':
                        self.handle_method_enable_selection(message)
                        return
                    elif admin_state.startswith('replying_to_complaint_'):
                        complaint_id = admin_state.replace('replying_to_complaint_', '')
                        self.handle_complaint_reply_buttons(message, complaint_id)
                        return
                    elif admin_state.startswith('editing_support_'):
                        self.handle_support_data_edit(message, admin_state)
                        return

            
            # معالجة النصوص والأزرار للأدمن
            self.handle_admin_actions(message)
            return
        
        # جلب عملة المستخدم أو العملة الافتراضية
        user_currency = user.get('currency', self.get_setting('default_currency') or 'SAR')
        
        # معالجة القوائم الرئيسية للمستخدمين
        if text in ['💰 طلب إيداع', '💰 Deposit Request']:
            logger.info(f"معالجة طلب إيداع من {user_id}")
            self.create_deposit_request(message)
        elif text in ['💸 طلب سحب', '💸 Withdrawal Request']:
            logger.info(f"معالجة طلب سحب من {user_id}")
            self.create_withdrawal_request(message)
        elif text in ['📋 طلباتي', '📋 My Requests']:
            self.show_user_transactions(message)
        elif text in ['👤 حسابي', '👤 Profile']:
            self.show_user_profile(message)
        elif text in ['📨 شكوى', '📨 Complaint']:
            self.handle_complaint_start(message)
        elif text in ['🆘 دعم', '🆘 Support']:
            support_text = f"""🆘 الدعم الفني

📞 رقم الهاتف: {self.get_setting('support_phone') or '+966501234567'}
⏰ ساعات العمل: 24/7
🏢 الشركة: DUX

يمكنك أيضاً إرسال شكوى من خلال النظام"""
            self.send_message(chat_id, support_text, self.main_keyboard(user.get('language', 'ar'), user_id))
        elif text in ['🇺🇸 English', '🇸🇦 العربية']:
            self.handle_language_change(message, text)
        elif text in ['💱 تغيير العملة', '💱 Change Currency']:
            self.show_currency_selection(message)
        elif text in ['📝 تسجيل حساب', '📝 Register Account']:
            # بدء عملية التسجيل للمستخدمين غير المسجلين
            self.start_registration(message)
        elif text == '/myid':
            self.send_message(chat_id, f"🆔 معرف المستخدم الخاص بك: {user_id}")
        elif text in ['🔙 العودة للقائمة الرئيسية', '🔙 العودة', '⬅️ العودة', '🏠 الرئيسية', '🏠 القائمة الرئيسية', '🔄 إعادة تعيين', '🔄 إعادة تعيين النظام', '🆘 إصلاح', 'reset', 'fix', '🔄 Reset System', '🆘 إصلاح شامل']:
            # إجراء إعادة تعيين شاملة وقوية
            self.super_reset_user_system(user_id, chat_id, user)
        else:
            # معالجة حالات المستخدم الخاصة
            if user_id in self.user_states:
                state = self.user_states[user_id]
                if state == 'writing_complaint':
                    self.save_complaint(message, text)
                    return
                elif state == 'selecting_currency':
                    self.handle_currency_selection(message, text)
                    return
            
            # رسالة خطأ محسنة مع زر إصلاح قوي
            error_keyboard = {
                'keyboard': [
                    [{'text': '🔄 إعادة تعيين النظام'}, {'text': '🆘 إصلاح شامل'}],
                    [{'text': '💰 طلب إيداع'}, {'text': '💸 طلب سحب'}],
                    [{'text': '📋 طلباتي'}, {'text': '👤 حسابي'}],
                    [{'text': '🏠 القائمة الرئيسية'}]
                ],
                'resize_keyboard': True,
                'one_time_keyboard': True
            }
            
            error_msg = f"""❌ أمر غير مفهوم أو خطأ في النظام

🔧 لحل أي مشكلة، اختر:
• 🔄 إعادة تعيين النظام - إصلاح بسيط
• 🆘 إصلاح شامل - حل جميع المشاكل

أو اختر من الخدمات المتاحة:"""
            
            self.send_message(chat_id, error_msg, error_keyboard)
    
    def start_registration(self, message):
        """بدء عملية التسجيل للمستخدمين غير المسجلين"""
        user_id = message['from']['id']
        chat_id = message['chat']['id']
        
        # التحقق إذا كان المستخدم مسجل بالفعل
        user = self.find_user(user_id)
        if user:
            self.send_message(chat_id, f"✅ أنت مسجل بالفعل!\n🆔 رقم العميل: {user['customer_id']}", 
                            self.main_keyboard(user.get('language', 'ar'), user_id))
            return
        
        # بدء عملية التسجيل
        welcome_text = """📝 بدء التسجيل في نظام DUX

يرجى إرسال اسمك الكامل للتسجيل:"""
        
        # كيبورد مع خيار الإلغاء
        registration_keyboard = {
            'keyboard': [
                [{'text': '❌ إلغاء التسجيل'}],
                [{'text': '🔄 إعادة تعيين النظام'}]
            ],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(chat_id, welcome_text, registration_keyboard)
        self.user_states[user_id] = 'registering_name'
    
    def super_reset_user_system(self, user_id, chat_id, user):
        """إعادة تعيين شاملة وقوية للنظام"""
        try:
            logger.info(f"بدء إعادة تعيين شاملة للمستخدم: {user_id}")
            
            # 1. تنظيف جميع حالات المستخدم
            if user_id in self.user_states:
                del self.user_states[user_id]
                logger.info(f"تم حذف حالة المستخدم: {user_id}")
            
            # 2. تنظيف البيانات المؤقتة
            temp_data_attrs = [
                'temp_company_data',
                'edit_company_data', 
                'temp_deposit_data',
                'temp_withdrawal_data',
                'temp_complaint_data',
                'temp_payment_data',
                'admin_temp_data'
            ]
            
            for attr in temp_data_attrs:
                if hasattr(self, attr) and user_id in getattr(self, attr, {}):
                    del getattr(self, attr)[user_id]
                    logger.info(f"تم حذف {attr} للمستخدم: {user_id}")
            
            # 3. إعادة تحميل بيانات المستخدم من الملف
            fresh_user = self.find_user(user_id)
            if fresh_user:
                user.update(fresh_user)
                logger.info(f"تم إعادة تحميل بيانات المستخدم: {user_id}")
            
            # 4. التحقق من سلامة الملفات الأساسية وإصلاحها
            self.verify_and_fix_system_files()
            
            # 5. إرسال رسالة نجاح مع معلومات محدثة
            welcome_text = f"""✅ تم إعادة تعيين النظام بنجاح!

🔧 تم إجراء التالي:
• تنظيف جميع الحالات المؤقتة
• إعادة تحميل البيانات الشخصية
• فحص سلامة النظام
• إصلاح أي أخطاء محتملة

👤 بياناتك المحدثة:
🏷️ الاسم: {user.get('name', 'غير محدد')}
🆔 رقم العميل: {user.get('customer_id', 'غير محدد')}
📱 الهاتف: {user.get('phone', 'غير محدد')}
🌐 اللغة: {'العربية' if user.get('language', 'ar') == 'ar' else 'English'}

🏠 النظام جاهز للاستخدام - اختر الخدمة المطلوبة:"""
            
            # إرسال الرسالة مع الكيبورد المناسب
            if self.is_admin(user_id):
                keyboard = self.admin_keyboard()
            else:
                keyboard = self.main_keyboard(user.get('language', 'ar'))
                
            self.send_message(chat_id, welcome_text, keyboard)
            logger.info(f"تمت إعادة التعيين الشاملة بنجاح للمستخدم: {user_id}")
            
        except Exception as e:
            logger.error(f"خطأ في إعادة التعيين الشاملة للمستخدم {user_id}: {e}")
            
            # في حالة فشل إعادة التعيين، إرسال رسالة طوارئ
            emergency_text = """🚨 حدث خطأ في إعادة التعيين

🔧 يرجى المحاولة مرة أخرى أو التواصل مع الدعم الفني

⚡ رقم الدعم: +966501234567"""
            
            emergency_keyboard = {
                'keyboard': [
                    [{'text': '🆘 إصلاح شامل'}, {'text': '🔄 إعادة تعيين النظام'}],
                    [{'text': '💰 طلب إيداع'}, {'text': '💸 طلب سحب'}]
                ],
                'resize_keyboard': True
            }
            
            self.send_message(chat_id, emergency_text, emergency_keyboard)
    
    def verify_and_fix_system_files(self):
        """فحص وإصلاح ملفات النظام الأساسية"""
        try:
            # التحقق من وجود الملفات الأساسية وإنشاؤها إذا لزم الأمر
            required_files = [
                'users.csv',
                'transactions.csv', 
                'companies.csv',
                'complaints.csv',
                'payment_methods.csv',
                'exchange_addresses.csv'
            ]
            
            for file_name in required_files:
                if not os.path.exists(file_name):
                    logger.warning(f"ملف مفقود يتم إنشاؤه: {file_name}")
                    self.init_files()  # إعادة إنشاء جميع الملفات
                    break
                    
            logger.info("تم فحص سلامة ملفات النظام بنجاح")
            
        except Exception as e:
            logger.error(f"خطأ في فحص ملفات النظام: {e}")

    def handle_admin_actions(self, message):
        """معالجة إجراءات الأدمن"""
        text = message['text']
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        
        # الأزرار الرئيسية
        if text == '📋 الطلبات المعلقة':
            self.show_pending_requests(message)
        elif text == '✅ طلبات مُوافقة':
            self.show_approved_transactions(message)
        elif text == '👥 إدارة المستخدمين':
            self.show_users_management(message)
        elif text == '🔍 البحث':
            self.prompt_admin_search(message)
        elif text == '👥 إدارة الأدمن':
            self.show_admin_management(message)
        elif text == '📋 عرض قائمة المديرين':
            self.show_detailed_admin_list(message)
        elif text == '➕ إضافة مدير دائم':
            self.prompt_add_permanent_admin(message)
        elif text == '🕐 إضافة مدير مؤقت':
            self.prompt_add_temp_admin(message)
        elif text == '➖ إزالة مدير':
            self.prompt_remove_admin(message)
        elif text == '📊 إحصائيات المديرين':
            self.show_admin_statistics(message)
        elif text == '🆔 معرف المستخدم':
            self.send_message(message['chat']['id'], f"🆔 معرف المستخدم الخاص بك: {message['from']['id']}", self.admin_keyboard())
        elif text == '💳 وسائل الدفع':
            self.show_payment_methods_management(message)
        elif text == '📊 الإحصائيات':
            self.show_detailed_stats(message)
        elif text == '📊 تقرير Excel احترافي':
            self.generate_professional_excel_report(message)
        elif text == '📢 إرسال جماعي':
            self.prompt_broadcast(message)
        elif text == '🚫 حظر مستخدم':
            self.prompt_ban_user(message)
        elif text == '✅ إلغاء حظر':
            self.prompt_unban_user(message)
        
        # معالجة أوامر النص المباشرة
        elif text.startswith('حظر '):
            parts = text.split(' ', 2)
            if len(parts) >= 3:
                customer_id = parts[1]
                reason = parts[2]
                self.ban_user_admin(message, customer_id, reason)
            else:
                self.send_message(chat_id, "❌ الصيغة الصحيحة:\nحظر [رقم_العميل] [سبب_الحظر]\nمثال: حظر C810563 مخالفة الشروط", self.admin_keyboard())
        
        elif text.startswith('الغاء_حظر ') or text.startswith('الغاء حظر '):
            customer_id = text.replace('الغاء_حظر ', '').replace('الغاء حظر ', '').strip()
            if customer_id:
                self.unban_user_admin(message, customer_id)
            else:
                self.send_message(chat_id, "❌ الصيغة الصحيحة:\nالغاء_حظر [رقم_العميل]\nمثال: الغاء_حظر C810563", self.admin_keyboard())
        elif text == '📝 إضافة شركة':
            self.start_add_company_wizard(message)
        elif text == '⚙️ إدارة الشركات':
            self.show_companies_management_enhanced(message)
        elif text == '🔄 تحديث القائمة':
            self.show_companies_management_enhanced(message)
        elif text == '➕ إضافة شركة جديدة':
            self.prompt_add_company(message)
        elif text == '✏️ تعديل شركة':
            self.prompt_edit_company(message)
        elif text == '🗑️ حذف شركة':
            self.prompt_delete_company(message)
        elif text == '🔄 تحديث القائمة':
            self.show_companies_management_enhanced(message)
        elif text in ['↩️ العودة للوحة الأدمن', '🏠 لوحة الأدمن']:
            self.handle_admin_panel(message)
        elif text in ['↩️ العودة', '🔙 العودة', '⬅️ العودة']:
            # تحديد السياق المناسب للعودة حسب الحالة
            user_state = self.user_states.get(message['from']['id'])
            if user_state:
                if 'payment' in str(user_state) or 'method' in str(user_state):
                    self.show_payment_methods_management(message)
                elif 'company' in str(user_state):
                    self.show_companies_management_enhanced(message)
                else:
                    self.handle_admin_panel(message)
            else:
                self.handle_admin_panel(message)
        elif text == '📍 إدارة العناوين':
            self.show_addresses_management(message)
        elif text == '🛠️ تعديل بيانات الدعم':
            self.show_support_data_editor(message)
        elif text == '📞 تعديل رقم الهاتف':
            self.start_phone_edit_wizard(message)
        elif text == '💬 تعديل حساب التليجرام':
            self.start_telegram_edit_wizard(message)
        elif text == '📧 تعديل البريد الإلكتروني':
            self.start_email_edit_wizard(message)
        elif text == '🕒 تعديل ساعات العمل':
            self.start_hours_edit_wizard(message)
        elif text == '🔄 تحديث بيانات الدعم':
            self.show_support_data_editor(message)
        elif text == '⚙️ إعدادات النظام':
            self.show_system_settings(message)
        elif text == '📨 الشكاوى':
            self.show_complaints_admin(message)
        elif text in ['🔄 تحديث الشكاوى', '🔄 تحديث']:
            self.show_complaints_admin(message)
        elif text.startswith('📞 رد على '):
            complaint_id = text.replace('📞 رد على ', '').strip()
            self.start_complaint_reply_wizard(message, complaint_id)
        elif text == '📋 نسخ أوامر سريعة':
            self.show_quick_copy_commands(message)
        elif text == '📧 إرسال رسالة لعميل':
            self.start_send_user_message(message)
        elif text == '💾 نسخة احتياطية فورية':
            self.manual_backup_command(message)
        elif text == '➕ إضافة وسيلة دفع':
            self.start_simple_payment_method_wizard(message)
        elif text == '✏️ تعديل وسيلة دفع':
            self.start_edit_payment_method_wizard(message)
        elif text == '🗑️ حذف وسيلة دفع':
            self.start_delete_payment_method_wizard(message)
        elif text == '📊 عرض وسائل الدفع':
            self.show_all_payment_methods_simplified(message)
        elif text == '⏹️ إيقاف وسيلة دفع':
            self.start_disable_payment_method_wizard(message)
        elif text == '▶️ تشغيل وسيلة دفع':
            self.start_enable_payment_method_wizard(message)
        elif text in ['🏠 القائمة الرئيسية', '🏠 الرئيسية']:
            # إنهاء جلسة الأدمن والعودة للقائمة الرئيسية
            if message['from']['id'] in self.user_states:
                del self.user_states[message['from']['id']]
            user = self.find_user(message['from']['id'])
            if user:
                welcome_text = f"""🏠 مرحباً بك مرة أخرى

👤 العميل: {user.get('name', 'غير محدد')}
🆔 رقم العميل: {user.get('customer_id', 'غير محدد')}

اختر الخدمة المطلوبة:"""
                self.send_message(chat_id, welcome_text, self.main_keyboard(user.get('language', 'ar')))
        
        # أوامر نصية للأدمن (مبسطة مع احتمالات متعددة)
        elif any(word in text.lower() for word in ['موافقة', 'موافق', 'اوافق', 'أوافق', 'قبول', 'مقبول', 'تأكيد', 'تاكيد', 'نعم']):
            # استخراج رقم المعاملة
            words = text.split()
            trans_id = None
            for word in words:
                if any(word.startswith(prefix) for prefix in ['DEP', 'WTH']):
                    trans_id = word
                    break
            
            if trans_id:
                self.approve_transaction(message, trans_id)
            else:
                self.send_message(message['chat']['id'], "❌ لم يتم العثور على رقم المعاملة. مثال: موافقة DEP123456", self.admin_keyboard())
                
        elif any(word in text.lower() for word in ['رفض', 'رافض', 'لا', 'مرفوض', 'إلغاء', 'الغاء', 'منع']):
            # استخراج رقم المعاملة والسبب
            words = text.split()
            trans_id = None
            reason_start = -1
            
            for i, word in enumerate(words):
                if any(word.startswith(prefix) for prefix in ['DEP', 'WTH']):
                    trans_id = word
                    reason_start = i + 1
                    break
            
            if trans_id:
                reason = ' '.join(words[reason_start:]) if reason_start != -1 and reason_start < len(words) else 'غير محدد'
                self.reject_transaction(message, trans_id, reason)
            else:
                self.send_message(message['chat']['id'], "❌ لم يتم العثور على رقم المعاملة. مثال: رفض DEP123456 سبب الرفض", self.admin_keyboard())
        elif text.startswith('بحث '):
            query = text.replace('بحث ', '')
            self.search_users_admin(message, query)
        elif text.startswith('اضافة_ادمن '):
            user_id_to_add = text.replace('اضافة_ادمن ', '')
            self.add_admin_user(message, user_id_to_add)
        elif text.startswith('اضافة ادمن '):
            user_id_to_add = text.replace('اضافة ادمن ', '')
            self.add_admin_user(message, user_id_to_add)
        elif text.startswith('ادمن_مؤقت '):
            user_id_to_add = text.replace('ادمن_مؤقت ', '')
            self.add_temp_admin(message, user_id_to_add)
        elif text.startswith('ازالة_ادمن '):
            user_id_to_remove = text.replace('ازالة_ادمن ', '')
            self.remove_admin_user(message, user_id_to_remove)
        elif text.startswith('حظر '):
            parts = text.replace('حظر ', '').split(' ', 1)
            customer_id = parts[0]
            reason = parts[1] if len(parts) > 1 else 'مخالفة الشروط'
            self.ban_user_admin(message, customer_id, reason)
        elif text.startswith('الغاء_حظر '):
            customer_id = text.replace('الغاء_حظر ', '')
            self.unban_user_admin(message, customer_id)
        elif text.startswith('اضافة_شركة '):
            self.add_company_simple_with_display(message, text)
        elif text.startswith('حذف_شركة '):
            company_id = text.replace('حذف_شركة ', '')
            self.delete_company_simple(message, company_id)
        elif text.startswith('عنوان_جديد '):
            new_address = text.replace('عنوان_جديد ', '')
            self.update_address_simple(message, new_address)
        elif any(word in text.lower() for word in ['عنوان', 'العنوان', 'تحديث_عنوان']):
            # استخراج العنوان الجديد
            new_address = text
            for word in ['عنوان', 'العنوان', 'تحديث_عنوان']:
                new_address = new_address.replace(word, '').strip()
            if new_address:
                self.update_address_simple(message, new_address)
            else:
                self.send_message(message['chat']['id'], "يرجى كتابة العنوان الجديد. مثال: عنوان شارع الملك فهد", self.admin_keyboard())
        elif text.startswith('تعديل_اعداد '):
            self.update_setting_simple(message, text)
        elif text == '✅ حفظ الشركة':
            # التعامل مع حفظ الشركة - تنفيذ مباشر
            if user_id in self.user_states and self.user_states[user_id] == 'confirming_company':
                if user_id in self.temp_company_data:
                    company_data = self.temp_company_data[user_id]
                    company_id = str(int(datetime.now().timestamp()))
                    
                    try:
                        # حفظ الشركة في الملف
                        with open('companies.csv', 'a', newline='', encoding='utf-8-sig') as f:
                            writer = csv.writer(f)
                            writer.writerow([company_id, company_data['name'], company_data['type'], company_data['details'], 'active'])
                        
                        success_msg = f"""🎉 تم إضافة الشركة بنجاح!

🆔 المعرف: {company_id}
🏢 الاسم: {company_data['name']}
⚡ النوع: {company_data['type_display']}
📋 التفاصيل: {company_data['details']}

الشركة متاحة الآن للعملاء ✅"""
                        
                        self.send_message(chat_id, success_msg, self.admin_keyboard())
                        
                        # تنظيف البيانات المؤقتة
                        del self.user_states[user_id]
                        del self.temp_company_data[user_id]
                        
                    except Exception as e:
                        self.send_message(chat_id, f"❌ فشل في حفظ الشركة: {str(e)}", self.admin_keyboard())
                else:
                    self.send_message(chat_id, "❌ لا توجد بيانات شركة محفوظة", self.admin_keyboard())
            else:
                self.send_message(chat_id, "❌ لا توجد شركة للحفظ. ابدأ بإضافة شركة جديدة أولاً.", self.admin_keyboard())
        elif text == '✅ حفظ التغييرات':
            # التعامل مع حفظ تغييرات الشركة
            if user_id in self.user_states and self.user_states[user_id] == 'editing_company_menu':
                self.save_company_changes(message)
            else:
                self.send_message(chat_id, "❌ لا توجد تغييرات للحفظ. ابدأ بتعديل شركة أولاً.", self.admin_keyboard())
        elif text in ['❌ إلغاء', 'إلغاء', 'الغاء']:
            # إلغاء العملية الحالية
            if user_id in self.user_states:
                del self.user_states[user_id]
            if user_id in self.edit_company_data:
                del self.edit_company_data[user_id]
            self.send_message(chat_id, "❌ تم إلغاء العملية", self.admin_keyboard())
        else:
            self.send_message(chat_id, "أمر غير مفهوم. استخدم الأزرار أو الأوامر الصحيحة.", self.admin_keyboard())
    
    def show_pending_requests(self, message):
        """عرض الطلبات المعلقة للأدمن مع أوامر نسخ سهلة"""
        pending_text = "📋 الطلبات المعلقة:\n\n"
        found_pending = False
        copy_commands = []
        
        try:
            with open('transactions.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['status'] == 'pending':
                        found_pending = True
                        type_emoji = "💰" if row['type'] == 'deposit' else "💸"
                        
                        pending_text += f"{type_emoji} **{row['id']}**\n"
                        pending_text += f"👤 {row['name']} ({row['customer_id']})\n"
                        pending_text += f"🏢 {row['company']}\n"
                        pending_text += f"💳 {row['wallet_number']}\n"
                        pending_text += f"💰 {row['amount']} ريال\n"
                        
                        if row.get('exchange_address'):
                            pending_text += f"📍 {row['exchange_address']}\n"
                        
                        pending_text += f"📅 {row['date']}\n"
                        
                        # إضافة أوامر النسخ السريع
                        pending_text += f"\n📋 **أوامر سريعة للنسخ:**\n"
                        pending_text += f"✅ `موافقة {row['id']}`\n"
                        pending_text += f"❌ `رفض {row['id']} السبب_هنا`\n"
                        pending_text += f"▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️\n\n"
                        
                        # حفظ الأوامر للنسخ الجماعي
                        copy_commands.append({
                            'id': row['id'],
                            'approve': f"موافقة {row['id']}",
                            'reject': f"رفض {row['id']} السبب_هنا"
                        })
        except:
            pass
        
        if not found_pending:
            pending_text += "✅ لا توجد طلبات معلقة"
        else:
            # إضافة قسم الأوامر الجاهزة للنسخ
            pending_text += "\n🔥 **أوامر جاهزة للنسخ المباشر:**\n\n"
            
            for cmd in copy_commands:
                pending_text += f"**{cmd['id']}:**\n"
                pending_text += f"✅ `{cmd['approve']}`\n"
                pending_text += f"❌ `{cmd['reject']}`\n\n"
            
            pending_text += "💡 **طرق سهلة للاستخدام:**\n"
            pending_text += "• انقر على الأمر واختر 'نسخ'\n"
            pending_text += "• أو اكتب مباشرة: موافقة + رقم المعاملة\n"
            pending_text += "• للرفض: رفض + رقم المعاملة + السبب\n\n"
            
            pending_text += "📝 **أمثلة أوامر الموافقة:**\n"
            pending_text += "`موافقة` أو `موافق` أو `تأكيد` أو `نعم`\n\n"
            
            pending_text += "📝 **أمثلة أوامر الرفض:**\n"
            pending_text += "`رفض` أو `لا` أو `مرفوض` أو `إلغاء`"
        
        self.send_message(message['chat']['id'], pending_text, self.admin_keyboard())
    
    def approve_transaction(self, message, trans_id):
        """الموافقة على معاملة"""
        success = self.update_transaction_status(trans_id, 'approved', '', str(message['from']['id']))
        
        if success:
            # إشعار العميل
            transaction = self.get_transaction(trans_id)
            if transaction:
                customer_telegram_id = transaction.get('telegram_id')
                if customer_telegram_id:
                    type_text = "الإيداع" if transaction['type'] == 'deposit' else "السحب"
                    customer_msg = f"""✅ تمت الموافقة على طلب {type_text}

🆔 {trans_id}
💰 {transaction['amount']} ريال
🏢 {transaction['company']}
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

{'شكراً لك! تم تأكيد إيداعك.' if transaction['type'] == 'deposit' else 'يرجى زيارة مكتب الصرافة لاستلام المبلغ.'}"""
                    
                    user = self.find_user(customer_telegram_id)
                    lang = user.get('language', 'ar') if user else 'ar'
                    self.send_message(customer_telegram_id, customer_msg, self.main_keyboard(lang))
            
            self.send_message(message['chat']['id'], f"✅ تمت الموافقة على {trans_id}", self.admin_keyboard())
        else:
            self.send_message(message['chat']['id'], f"❌ فشل في الموافقة على {trans_id}", self.admin_keyboard())
    
    def reject_transaction(self, message, trans_id, reason):
        """رفض معاملة"""
        success = self.update_transaction_status(trans_id, 'rejected', reason, str(message['from']['id']))
        
        if success:
            # إشعار العميل
            transaction = self.get_transaction(trans_id)
            if transaction:
                customer_telegram_id = transaction.get('telegram_id')
                if customer_telegram_id:
                    type_text = "الإيداع" if transaction['type'] == 'deposit' else "السحب"
                    customer_msg = f"""❌ تم رفض طلب {type_text}

🆔 {trans_id}
💰 {transaction['amount']} ريال
📝 السبب: {reason}
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

يمكنك إنشاء طلب جديد أو التواصل مع الدعم."""
                    
                    user = self.find_user(customer_telegram_id)
                    lang = user.get('language', 'ar') if user else 'ar'
                    self.send_message(customer_telegram_id, customer_msg, self.main_keyboard(lang))
            
            self.send_message(message['chat']['id'], f"✅ تم رفض {trans_id}\nالسبب: {reason}", self.admin_keyboard())
        else:
            self.send_message(message['chat']['id'], f"❌ فشل في رفض {trans_id}", self.admin_keyboard())
    
    def update_transaction_status(self, trans_id, new_status, note='', admin_id=''):
        """تحديث حالة المعاملة"""
        transactions = []
        success = False
        
        try:
            with open('transactions.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == trans_id:
                        row['status'] = new_status
                        if note:
                            row['admin_note'] = note
                        if admin_id:
                            row['processed_by'] = admin_id
                        success = True
                    transactions.append(row)
            
            if success:
                with open('transactions.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['id', 'customer_id', 'telegram_id', 'name', 'type', 'company', 'wallet_number', 'amount', 'exchange_address', 'status', 'date', 'admin_note', 'processed_by']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(transactions)
        except:
            pass
        
        return success
    
    def get_transaction(self, trans_id):
        """جلب معاملة محددة"""
        try:
            with open('transactions.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == trans_id:
                        return row
        except:
            pass
        return None
    
    def show_detailed_stats(self, message):
        """عرض إحصائيات مفصلة"""
        stats_text = "📊 إحصائيات النظام الشاملة\n\n"
        
        # إحصائيات المستخدمين
        total_users = 0
        banned_users = 0
        try:
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total_users += 1
                    if row.get('is_banned') == 'yes':
                        banned_users += 1
        except:
            pass
        
        # إحصائيات المعاملات
        total_transactions = 0
        pending_count = 0
        approved_count = 0
        rejected_count = 0
        total_deposit_amount = 0
        total_withdraw_amount = 0
        
        try:
            with open('transactions.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total_transactions += 1
                    amount = float(row.get('amount', 0))
                    
                    if row['status'] == 'pending':
                        pending_count += 1
                    elif row['status'] == 'approved':
                        approved_count += 1
                        if row['type'] == 'deposit':
                            total_deposit_amount += amount
                        else:
                            total_withdraw_amount += amount
                    elif row['status'] == 'rejected':
                        rejected_count += 1
        except:
            pass
        
        # إحصائيات الشكاوى
        total_complaints = 0
        try:
            with open('complaints.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                total_complaints = sum(1 for row in reader)
        except:
            pass
        
        stats_text += f"👥 المستخدمون:\n"
        stats_text += f"├ إجمالي المستخدمين: {total_users}\n"
        stats_text += f"├ المستخدمون النشطون: {total_users - banned_users}\n"
        stats_text += f"└ المستخدمون المحظورون: {banned_users}\n\n"
        
        stats_text += f"💰 المعاملات:\n"
        stats_text += f"├ إجمالي المعاملات: {total_transactions}\n"
        stats_text += f"├ معلقة: {pending_count}\n"
        stats_text += f"├ مُوافق عليها: {approved_count}\n"
        stats_text += f"└ مرفوضة: {rejected_count}\n\n"
        
        stats_text += f"💵 المبالغ المُوافق عليها:\n"
        stats_text += f"├ إجمالي الإيداعات: {total_deposit_amount:,.0f} ريال\n"
        stats_text += f"├ إجمالي السحوبات: {total_withdraw_amount:,.0f} ريال\n"
        stats_text += f"└ الفرق: {total_deposit_amount - total_withdraw_amount:,.0f} ريال\n\n"
        
        stats_text += f"📨 الشكاوى: {total_complaints}\n\n"
        stats_text += f"📅 تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        self.send_message(message['chat']['id'], stats_text, self.admin_keyboard())
    
    def add_company_simple_with_display(self, message, text):
        """إضافة شركة مع عرض القائمة المحدثة"""
        result = self.add_company_simple(message, text)
        if result:
            # عرض قائمة الشركات المحدثة فوراً
            self.show_companies_management_enhanced(message)
    
    def add_company_simple(self, message, text):
        """إضافة شركة بصيغة مبسطة"""
        # تنسيق: اضافة_شركة اسم نوع تفاصيل
        parts = text.replace('اضافة_شركة ', '').split(' ', 2)
        if len(parts) < 3:
            help_text = """❌ طريقة إضافة الشركة:

📝 اكتب بالضبط:
اضافة_شركة اسم_الشركة نوع_الخدمة التفاصيل

🔹 أنواع الخدمة (بالإنجليزي):
• ايداع → deposit
• سحب → withdraw  
• ايداع وسحب → both

📋 أمثلة صحيحة:
▫️ اضافة_شركة مدى both محفظة_رقمية
▫️ اضافة_شركة البنك_الأهلي deposit حساب_بنكي
▫️ اضافة_شركة فودافون_كاش withdraw محفظة_الكترونية
▫️ اضافة_شركة STC_Pay both خدمات_دفع"""
            
            self.send_message(message['chat']['id'], help_text, self.admin_keyboard())
            return
        
        company_name = parts[0].replace('_', ' ')
        service_type = parts[1].lower()
        details = parts[2].replace('_', ' ')
        
        # قبول الكلمات العربية وتحويلها
        if service_type in ['ايداع', 'إيداع']:
            service_type = 'deposit'
        elif service_type in ['سحب']:
            service_type = 'withdraw'
        elif service_type in ['كلاهما', 'الكل', 'ايداع_وسحب']:
            service_type = 'both'
        
        if service_type not in ['deposit', 'withdraw', 'both']:
            error_text = """❌ نوع الخدمة خطأ!

✅ الأنواع المقبولة:
• deposit (للإيداع فقط)
• withdraw (للسحب فقط)
• both (للإيداع والسحب)

أو بالعربي:
• ايداع → deposit
• سحب → withdraw
• كلاهما → both

مثال صحيح:
اضافة_شركة مدى both محفظة_رقمية"""
            
            self.send_message(message['chat']['id'], error_text, self.admin_keyboard())
            return
        
        # إنشاء معرف جديد
        company_id = str(int(datetime.now().timestamp()))
        
        try:
            # التأكد من وجود الملف وإنشاؤه إذا لم يكن موجوداً
            file_exists = True
            try:
                with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                    pass
            except FileNotFoundError:
                file_exists = False
            
            # إنشاء الملف مع الرؤوس إذا لم يكن موجوداً
            if not file_exists:
                with open('companies.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['id', 'name', 'type', 'details', 'is_active'])
            
            # إضافة الشركة الجديدة
            with open('companies.csv', 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([company_id, company_name, service_type, details, 'active'])
            
            # رسالة النجاح مع عرض قائمة الشركات المحدثة
            success_msg = f"""✅ تم إضافة الشركة بنجاح!

🆔 المعرف: {company_id}
🏢 الاسم: {company_name}
⚡ النوع: {service_type}
📋 التفاصيل: {details}

📋 قائمة الشركات المحدثة:"""
            
            # عرض جميع الشركات
            try:
                with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    company_count = 0
                    for row in reader:
                        company_count += 1
                        status = "✅" if row.get('is_active') == 'active' else "❌"
                        type_display = {'deposit': 'إيداع', 'withdraw': 'سحب', 'both': 'الكل'}.get(row['type'], row['type'])
                        success_msg += f"\n{status} {row['name']} (ID: {row['id']}) - {type_display}"
                    
                    success_msg += f"\n\n📊 إجمالي الشركات: {company_count}"
            except:
                pass
            
            self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
            return True
            
        except Exception as e:
            self.send_message(message['chat']['id'], f"❌ فشل في إضافة الشركة: {str(e)}", self.admin_keyboard())
            return False
    
    def update_address_simple(self, message, new_address):
        """تحديث عنوان الصرافة"""
        try:
            with open('exchange_addresses.csv', 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'address', 'is_active'])
                writer.writerow(['1', new_address, 'yes'])
            
            self.send_message(message['chat']['id'], f"✅ تم تحديث عنوان الصرافة:\n{new_address}", self.admin_keyboard())
        except Exception as e:
            self.send_message(message['chat']['id'], f"❌ فشل في تحديث العنوان: {str(e)}", self.admin_keyboard())
    
    def run(self):
        """تشغيل البوت"""
        logger.info(f"✅ نظام DUX الشامل يعمل: @{os.getenv('BOT_TOKEN', 'unknown').split(':')[0] if os.getenv('BOT_TOKEN') else 'unknown'}")
        
        while True:
            try:
                updates = self.get_updates()
                if updates and updates.get('ok'):
                    for update in updates['result']:
                        self.offset = update['update_id']
                        
                        if 'message' in update:
                            message = update['message']
                            # تسجيل الرسائل للتشخيص
                            if 'text' in message:
                                logger.info(f"رسالة مستلمة: {message['text']} من {message['from']['id']}")
                            try:
                                self.process_message(message)
                            except Exception as msg_error:
                                logger.error(f"خطأ في معالجة الرسالة: {msg_error}")
                                # إرسال رسالة خطأ للمستخدم
                                try:
                                    error_keyboard = {
                                        'keyboard': [
                                            [{'text': '🔄 إعادة تعيين النظام'}],
                                            [{'text': '💰 طلب إيداع'}, {'text': '💸 طلب سحب'}]
                                        ],
                                        'resize_keyboard': True
                                    }
                                    self.send_message(message['chat']['id'], 
                                                    "❌ حدث خطأ. اضغط على 'إعادة تعيين النظام' للإصلاح", 
                                                    error_keyboard)
                                except:
                                    pass
                        elif 'callback_query' in update:
                            pass  # يمكن إضافة معالجة الأزرار المتقدمة لاحقاً
                            
            except KeyboardInterrupt:
                logger.info("تم إيقاف البوت")
                break
            except Exception as e:
                logger.error(f"خطأ عام: {e}")
                import time
                time.sleep(1)  # انتظار قصير قبل المحاولة مرة أخرى
                continue

    def handle_complaint_start(self, message):
        """بدء عملية الشكوى"""
        self.send_message(message['chat']['id'], "📨 أرسل شكواك أو استفسارك:")
        self.user_states[message['from']['id']] = 'writing_complaint'
    
    def handle_language_change(self, message, text):
        """تغيير اللغة"""
        user_id = message['from']['id']
        new_lang = 'en' if '🇺🇸' in text else 'ar'
        
        # تحديث لغة المستخدم في الملف
        users = []
        try:
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['telegram_id'] == str(user_id):
                        row['language'] = new_lang
                    users.append(row)
            
            with open('users.csv', 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['telegram_id', 'name', 'phone', 'customer_id', 'language', 'date', 'is_banned', 'ban_reason']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(users)
            
            welcome_msg = "Language changed to English!" if new_lang == 'en' else "تم تغيير اللغة إلى العربية!"
            self.send_message(message['chat']['id'], welcome_msg, self.main_keyboard(new_lang))
        except:
            pass
    
    def prompt_admin_search(self, message):
        """طلب البحث من الأدمن"""
        search_help = """🔍 البحث في النظام

أرسل: بحث متبوعاً بالنص المطلوب

يمكنك البحث بـ:
• اسم العميل
• رقم العميل
• رقم الهاتف

مثال: بحث أحمد"""
        self.send_message(message['chat']['id'], search_help, self.admin_keyboard())
        
    def search_users_admin(self, message, query):
        """البحث في المستخدمين للأدمن"""
        try:
            results = []
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # البحث في الاسم أو رقم العميل أو الهاتف
                    if (query.lower() in row.get('name', '').lower() or 
                        query in row.get('customer_id', '') or 
                        query in row.get('phone', '')):
                        results.append(row)
            
            if not results:
                self.send_message(message['chat']['id'], f"❌ لم يتم العثور على نتائج للبحث: {query}", self.admin_keyboard())
                return
            
            response = f"🔍 نتائج البحث عن: {query}\n\n"
            for user in results:
                ban_status = "🚫 محظور" if user.get('is_banned') == 'yes' else "✅ نشط"
                response += f"👤 {user.get('name', 'غير محدد')}\n"
                response += f"🆔 {user.get('customer_id', 'غير محدد')}\n"
                response += f"📱 {user.get('phone', 'غير محدد')}\n"
                response += f"🔸 {ban_status}\n\n"
            
            if len(response) > 4000:
                response = response[:4000] + "\n... والمزيد من النتائج"
            
            self.send_message(message['chat']['id'], response, self.admin_keyboard())
            
        except Exception as e:
            logger.error(f"خطأ في البحث: {e}")
            self.send_message(message['chat']['id'], "❌ حدث خطأ أثناء البحث", self.admin_keyboard())
    
    def add_admin_user(self, message, user_id_to_add):
        """إضافة أدمن جديد"""
        try:
            # التحقق من صحة المعرف
            if not user_id_to_add.isdigit():
                self.send_message(message['chat']['id'], "❌ معرف المستخدم يجب أن يكون رقماً صحيحاً", self.admin_keyboard())
                return
            
            # إضافة الأدمن الجديد للقائمة
            if int(user_id_to_add) not in self.admin_user_ids:
                self.admin_user_ids.append(int(user_id_to_add))
                
                success_msg = f"""✅ تم إضافة أدمن جديد بنجاح!
                
🆔 معرف المستخدم: {user_id_to_add}
🔐 تم منح صلاحيات الإدارة
                
💡 ملاحظة: هذا الأدمن نشط في الجلسة الحالية فقط.
لضمان استمرارية الصلاحيات، يجب إضافة المعرف إلى متغير البيئة ADMIN_USER_IDS"""
                
                self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
                logger.info(f"تم إضافة أدمن جديد: {user_id_to_add}")
            else:
                self.send_message(message['chat']['id'], f"⚠️ المستخدم {user_id_to_add} أدمن بالفعل", self.admin_keyboard())
                
        except Exception as e:
            logger.error(f"خطأ في إضافة الأدمن: {e}")
            self.send_message(message['chat']['id'], "❌ حدث خطأ أثناء إضافة الأدمن", self.admin_keyboard())
    
    def prompt_add_admin(self, message):
        """طلب إضافة أدمن جديد"""
        add_admin_help = """👥 إضافة أدمن جديد
        
الصيغة: اضافة_ادمن معرف_المستخدم

مثال: اضافة_ادمن 123456789

💡 لمعرفة معرف المستخدم، اطلب منه إرسال /myid"""
        self.send_message(message['chat']['id'], add_admin_help, self.admin_keyboard())
    
    def show_admin_list(self, message):
        """عرض قائمة الأدمن"""
        admin_text = "📋 قائمة المديرين:\n\n"
        
        for i, admin_id in enumerate(self.admin_user_ids, 1):
            admin_text += f"{i}. 🆔 {admin_id}\n"
        
        admin_text += f"\n📊 العدد الإجمالي: {len(self.admin_user_ids)} مدير"
        
        self.send_message(message['chat']['id'], admin_text, self.admin_keyboard())
    
    def show_admin_management(self, message):
        """لوحة إدارة المديرين المتقدمة"""
        admin_text = """👥 إدارة المديرين
        
🔧 الخيارات المتاحة:

📋 عرض المديرين الحاليين
➕ إضافة مدير جديد (دائم)
🕐 إضافة مدير مؤقت (للجلسة)
➖ إزالة مدير
📊 إحصائيات المديرين

اختر الخيار المطلوب:"""
        
        keyboard = [
            [{'text': '📋 عرض قائمة المديرين'}, {'text': '➕ إضافة مدير دائم'}],
            [{'text': '🕐 إضافة مدير مؤقت'}, {'text': '➖ إزالة مدير'}],
            [{'text': '📊 إحصائيات المديرين'}, {'text': '🆔 معرف المستخدم'}],
            [{'text': '↩️ العودة للوحة الأدمن'}]
        ]
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
        
        self.send_message(message['chat']['id'], admin_text, reply_keyboard)
        
    def add_temp_admin(self, message, user_id_to_add):
        """إضافة مدير مؤقت للجلسة الحالية فقط"""
        try:
            if not user_id_to_add.isdigit():
                self.send_message(message['chat']['id'], "❌ معرف المستخدم يجب أن يكون رقماً صحيحاً", self.admin_keyboard())
                return
            
            user_id = int(user_id_to_add)
            
            if user_id in self.temp_admin_user_ids:
                self.send_message(message['chat']['id'], f"⚠️ المستخدم {user_id_to_add} مدير مؤقت بالفعل", self.admin_keyboard())
                return
            
            if user_id in self.admin_user_ids:
                self.send_message(message['chat']['id'], f"⚠️ المستخدم {user_id_to_add} مدير دائم بالفعل", self.admin_keyboard())
                return
            
            self.temp_admin_user_ids.append(user_id)
            
            success_msg = f"""✅ تم إضافة مدير مؤقت بنجاح!
            
🆔 معرف المستخدم: {user_id_to_add}
🕐 نوع الصلاحية: مؤقت (للجلسة الحالية)
⏰ ينتهي عند: إعادة تشغيل النظام

💡 المدير المؤقت له جميع الصلاحيات حتى إعادة تشغيل النظام"""
            
            self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
            logger.info(f"تم إضافة مدير مؤقت: {user_id_to_add}")
            
        except Exception as e:
            logger.error(f"خطأ في إضافة المدير المؤقت: {e}")
            self.send_message(message['chat']['id'], "❌ حدث خطأ أثناء إضافة المدير المؤقت", self.admin_keyboard())
    
    def remove_admin_user(self, message, user_id_to_remove):
        """إزالة مدير"""
        try:
            if not user_id_to_remove.isdigit():
                self.send_message(message['chat']['id'], "❌ معرف المستخدم يجب أن يكون رقماً صحيحاً", self.admin_keyboard())
                return
            
            user_id = int(user_id_to_remove)
            removed = False
            admin_type = ""
            
            # إزالة من المديرين المؤقتين
            if user_id in self.temp_admin_user_ids:
                self.temp_admin_user_ids.remove(user_id)
                removed = True
                admin_type = "مؤقت"
            
            # إزالة من المديرين الدائمين (للجلسة الحالية فقط)
            elif user_id in self.admin_user_ids:
                self.admin_user_ids.remove(user_id)
                removed = True
                admin_type = "دائم (من الجلسة الحالية)"
            
            if removed:
                success_msg = f"""✅ تم إزالة المدير بنجاح!
                
🆔 معرف المستخدم: {user_id_to_remove}
🔧 نوع المدير: {admin_type}

⚠️ ملاحظة: إذا كان مديراً دائماً، سيتم استعادته عند إعادة تشغيل النظام إلا إذا تم إزالته من متغير البيئة ADMIN_USER_IDS"""
                
                self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
                logger.info(f"تم إزالة مدير {admin_type}: {user_id_to_remove}")
            else:
                self.send_message(message['chat']['id'], f"❌ المستخدم {user_id_to_remove} ليس مديراً", self.admin_keyboard())
            
        except Exception as e:
            logger.error(f"خطأ في إزالة المدير: {e}")
            self.send_message(message['chat']['id'], "❌ حدث خطأ أثناء إزالة المدير", self.admin_keyboard())
    
    def show_detailed_admin_list(self, message):
        """عرض قائمة المديرين المفصلة"""
        admin_text = "📋 قائمة المديرين المفصلة\n\n"
        
        # المديرين الدائمين
        if self.admin_user_ids:
            admin_text += "🔒 المديرين الدائمين:\n"
            for i, admin_id in enumerate(self.admin_user_ids, 1):
                admin_text += f"   {i}. 🆔 {admin_id} (دائم)\n"
            admin_text += f"   📊 العدد: {len(self.admin_user_ids)}\n\n"
        
        # المديرين المؤقتين
        if self.temp_admin_user_ids:
            admin_text += "🕐 المديرين المؤقتين:\n"
            for i, admin_id in enumerate(self.temp_admin_user_ids, 1):
                admin_text += f"   {i}. 🆔 {admin_id} (مؤقت)\n"
            admin_text += f"   📊 العدد: {len(self.temp_admin_user_ids)}\n\n"
        
        # المديرين من متغيرات البيئة
        if self.admin_ids:
            admin_text += "🌐 مديرين البيئة:\n"
            for i, admin_id in enumerate(self.admin_ids, 1):
                admin_text += f"   {i}. 🆔 {admin_id} (بيئة)\n"
            admin_text += f"   📊 العدد: {len(self.admin_ids)}\n\n"
        
        total_admins = len(self.admin_user_ids) + len(self.temp_admin_user_ids) + len(self.admin_ids)
        admin_text += f"📈 إجمالي المديرين: {total_admins}"
        
        self.send_message(message['chat']['id'], admin_text, self.admin_keyboard())
    
    def prompt_add_permanent_admin(self, message):
        """طلب إضافة مدير دائم"""
        help_text = """➕ إضافة مدير دائم
        
الصيغة: اضافة_ادمن معرف_المستخدم

مثال: اضافة_ادمن 123456789

💡 المدير الدائم:
• يحتفظ بصلاحياته في الجلسة الحالية
• يفقد الصلاحيات عند إعادة التشغيل إلا إذا تم إضافته لمتغير البيئة
• لمعرفة معرف المستخدم: /myid"""
        
        self.send_message(message['chat']['id'], help_text, self.admin_keyboard())
    
    def prompt_add_temp_admin(self, message):
        """طلب إضافة مدير مؤقت"""
        help_text = """🕐 إضافة مدير مؤقت
        
الصيغة: ادمن_مؤقت معرف_المستخدم

مثال: ادمن_مؤقت 123456789

💡 المدير المؤقت:
• صلاحيات مؤقتة للجلسة الحالية فقط
• يفقد الصلاحيات عند إعادة تشغيل النظام
• مناسب للمساعدين المؤقتين"""
        
        self.send_message(message['chat']['id'], help_text, self.admin_keyboard())
    
    def prompt_remove_admin(self, message):
        """طلب إزالة مدير"""
        help_text = """➖ إزالة مدير
        
الصيغة: ازالة_ادمن معرف_المستخدم

مثال: ازالة_ادمن 123456789

⚠️ ملاحظات مهمة:
• يمكن إزالة المديرين المؤقتين والدائمين
• المديرين الدائمين سيتم استعادتهم عند إعادة التشغيل
• لإزالة دائمة، يجب تعديل متغير البيئة ADMIN_USER_IDS"""
        
        self.send_message(message['chat']['id'], help_text, self.admin_keyboard())
    
    def show_admin_statistics(self, message):
        """عرض إحصائيات المديرين"""
        stats_text = """📊 إحصائيات المديرين
        
📈 الإحصائيات العامة:
"""
        
        # إحصائيات المديرين
        permanent_count = len(self.admin_user_ids)
        temp_count = len(self.temp_admin_user_ids)
        env_count = len(self.admin_ids)
        total_count = permanent_count + temp_count + env_count
        
        stats_text += f"🔒 مديرين دائمين: {permanent_count}\n"
        stats_text += f"🕐 مديرين مؤقتين: {temp_count}\n"
        stats_text += f"🌐 mديرين البيئة: {env_count}\n"
        stats_text += f"📊 إجمالي المديرين: {total_count}\n\n"
        
        # إحصائيات الأمان
        stats_text += "🔐 مستوى الأمان:\n"
        if total_count >= 3:
            stats_text += "🟢 ممتاز - عدد كافٍ من المديرين\n"
        elif total_count >= 2:
            stats_text += "🟡 جيد - يُنصح بإضافة مدير إضافي\n"
        else:
            stats_text += "🔴 منخفض - يُنصح بإضافة مديرين إضافيين\n"
        
        # توصيات
        stats_text += "\n💡 التوصيات:\n"
        if temp_count > permanent_count:
            stats_text += "• تحويل بعض المديرين المؤقتين إلى دائمين\n"
        if total_count < 2:
            stats_text += "• إضافة مديرين احتياطيين للطوارئ\n"
        if env_count == 0:
            stats_text += "• إضافة مدير في متغير البيئة للاستمرارية\n"
        
        self.send_message(message['chat']['id'], stats_text, self.admin_keyboard())
    
    def prompt_broadcast(self, message):
        """طلب الإرسال الجماعي"""
        broadcast_help = """📢 الإرسال الجماعي

أرسل رسالة وسيتم إرسالها لجميع المستخدمين النشطين.
اكتب الرسالة مباشرة:"""
        self.send_message(message['chat']['id'], broadcast_help)
        self.user_states[message['from']['id']] = 'admin_broadcasting'
    
    def prompt_ban_user(self, message):
        """طلب حظر مستخدم"""
        ban_help = """🚫 حظر مستخدم

الصيغة: حظر رقم_العميل السبب

مثال: حظر C123456 مخالفة الشروط"""
        self.send_message(message['chat']['id'], ban_help, self.admin_keyboard())
    
    def prompt_unban_user(self, message):
        """طلب إلغاء حظر مستخدم مع عرض المستخدمين المحظورين"""
        # البحث عن المستخدمين المحظورين
        banned_users = []
        try:
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('is_banned', 'no') == 'yes':
                        banned_users.append({
                            'customer_id': row['customer_id'],
                            'name': row['name'],
                            'ban_reason': row.get('ban_reason', 'غير محدد')
                        })
        except:
            pass
        
        unban_help = """✅ إلغاء حظر مستخدم

📝 الصيغة الصحيحة:
الغاء_حظر [رقم_العميل]
أو: الغاء حظر [رقم_العميل]

مثال:
الغاء_حظر C810563"""
        
        if banned_users:
            unban_help += "\n\n🚫 المستخدمين المحظورين حالياً:\n"
            for user in banned_users:
                unban_help += f"\n🆔 {user['customer_id']}\n"
                unban_help += f"👤 {user['name']}\n"
                unban_help += f"📝 السبب: {user['ban_reason']}\n"
                unban_help += f"⚡ `الغاء_حظر {user['customer_id']}`\n"
                unban_help += "▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️\n"
        else:
            unban_help += "\n\n✅ لا يوجد مستخدمين محظورين حالياً"
        
        self.send_message(message['chat']['id'], unban_help, self.admin_keyboard())
    
    def prompt_add_company(self, message):
        """بدء معالج إضافة شركة التفاعلي"""
        help_text = """🏢 معالج إضافة شركة جديدة
        
سأطلب منك المعلومات خطوة بخطوة:

📝 أولاً، أرسل اسم الشركة:
مثال: البنك الأهلي، مدى، STC Pay، فودافون كاش"""
        
        self.send_message(message['chat']['id'], help_text)
        self.user_states[message['from']['id']] = 'adding_company_name'
    
    def handle_company_wizard(self, message):
        """معالج إضافة الشركة التفاعلي"""
        user_id = message['from']['id']
        state = self.user_states.get(user_id)
        text = message.get('text', '').strip()
        
        if state == 'adding_company_name':
            # حفظ اسم الشركة
            if not hasattr(self, 'temp_company_data'):
                self.temp_company_data = {}
            if user_id not in self.temp_company_data:
                self.temp_company_data[user_id] = {}
            
            self.temp_company_data[user_id]['name'] = text
            
            # طلب نوع الخدمة
            service_keyboard = {
                'keyboard': [
                    [{'text': '💳 إيداع فقط'}, {'text': '💰 سحب فقط'}],
                    [{'text': '🔄 إيداع وسحب معاً'}],
                    [{'text': '❌ إلغاء'}]
                ],
                'resize_keyboard': True,
                'one_time_keyboard': True
            }
            
            self.send_message(message['chat']['id'], 
                f"✅ تم حفظ اسم الشركة: {text}\n\n🔧 الآن اختر نوع الخدمة:", 
                service_keyboard)
            self.user_states[user_id] = 'adding_company_type'
            
        elif state == 'adding_company_type':
            # حفظ نوع الخدمة
            if text == '💳 إيداع فقط':
                service_type = 'deposit'
                service_display = 'إيداع فقط'
            elif text == '💰 سحب فقط':
                service_type = 'withdraw'
                service_display = 'سحب فقط'
            elif text == '🔄 إيداع وسحب معاً':
                service_type = 'both'
                service_display = 'إيداع وسحب'
            elif text == '❌ إلغاء':
                del self.user_states[user_id]
                if hasattr(self, 'temp_company_data') and user_id in self.temp_company_data:
                    del self.temp_company_data[user_id]
                self.send_message(message['chat']['id'], "❌ تم إلغاء إضافة الشركة", self.admin_keyboard())
                return
            else:
                self.send_message(message['chat']['id'], "❌ اختر نوع الخدمة من الأزرار المتاحة")
                return
            
            self.temp_company_data[user_id]['type'] = service_type
            self.temp_company_data[user_id]['type_display'] = service_display
            
            # طلب التفاصيل
            self.send_message(message['chat']['id'], 
                f"✅ نوع الخدمة: {service_display}\n\n📋 الآن أرسل تفاصيل الشركة:\nمثال: محفظة إلكترونية، حساب بنكي رقم 1234567890، خدمة دفع رقمية")
            self.user_states[user_id] = 'adding_company_details'
            
        elif state == 'adding_company_details':
            # حفظ التفاصيل وإنهاء العملية
            self.temp_company_data[user_id]['details'] = text
            
            # عرض ملخص التأكيد
            company_data = self.temp_company_data[user_id]
            confirm_text = f"""📊 ملخص الشركة الجديدة:

🏢 الاسم: {company_data['name']}
⚡ نوع الخدمة: {company_data['type_display']}
📋 التفاصيل: {company_data['details']}

هل تريد حفظ هذه الشركة؟"""
            
            confirm_keyboard = {
                'keyboard': [
                    [{'text': '✅ حفظ الشركة'}, {'text': '❌ إلغاء'}],
                    [{'text': '🔄 تعديل الاسم'}, {'text': '🔧 تعديل النوع'}, {'text': '📝 تعديل التفاصيل'}]
                ],
                'resize_keyboard': True,
                'one_time_keyboard': True
            }
            
            self.send_message(message['chat']['id'], confirm_text, confirm_keyboard)
            self.user_states[user_id] = 'confirming_company'
            
        elif state == 'confirming_company':
            company_data = self.temp_company_data[user_id]
            
            if text == '✅ حفظ الشركة':
                # تجنب تشغيل نفس الكود مرتين - هذا يُعالج الآن في handle_admin_actions
                pass
                    
            elif text == '❌ إلغاء':
                del self.user_states[user_id]
                if user_id in self.temp_company_data:
                    del self.temp_company_data[user_id]
                self.send_message(message['chat']['id'], "❌ تم إلغاء إضافة الشركة", self.admin_keyboard())
                
            elif text == '🔄 تعديل الاسم':
                self.send_message(message['chat']['id'], f"📝 الاسم الحالي: {company_data['name']}\n\nأرسل الاسم الجديد:")
                self.user_states[user_id] = 'adding_company_name'
                
            elif text == '🔧 تعديل النوع':
                service_keyboard = {
                    'keyboard': [
                        [{'text': '💳 إيداع فقط'}, {'text': '💰 سحب فقط'}],
                        [{'text': '🔄 إيداع وسحب معاً'}],
                        [{'text': '❌ إلغاء'}]
                    ],
                    'resize_keyboard': True,
                    'one_time_keyboard': True
                }
                self.send_message(message['chat']['id'], f"🔧 النوع الحالي: {company_data['type_display']}\n\nاختر النوع الجديد:", service_keyboard)
                self.user_states[user_id] = 'adding_company_type'
                
            elif text == '📝 تعديل التفاصيل':
                self.send_message(message['chat']['id'], f"📋 التفاصيل الحالية: {company_data['details']}\n\nأرسل التفاصيل الجديدة:")
                self.user_states[user_id] = 'adding_company_details'
                
            else:
                self.send_message(message['chat']['id'], "❌ اختر من الأزرار المتاحة")
    
    def prompt_edit_company(self, message):
        """بدء معالج تعديل الشركة"""
        # عرض الشركات المتاحة للتعديل
        companies_text = "🔧 تعديل الشركات:\n\n"
        
        try:
            with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    status = "✅" if row.get('is_active') == 'active' else "❌"
                    companies_text += f"{status} {row['id']} - {row['name']}\n"
                    companies_text += f"   📋 {row['type']} - {row['details']}\n\n"
        except:
            companies_text += "❌ لا توجد شركات\n\n"
        
        companies_text += "📝 أرسل رقم معرف الشركة التي تريد تعديلها:"
        
        self.send_message(message['chat']['id'], companies_text)
        self.user_states[message['from']['id']] = 'selecting_company_edit'
    
    def handle_company_edit_wizard(self, message):
        """معالج تعديل الشركة التفاعلي"""
        user_id = message['from']['id']
        state = self.user_states.get(user_id)
        text = message.get('text', '').strip()
        
        if state == 'selecting_company_edit':
            # البحث عن الشركة
            company_found = None
            try:
                with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['id'] == text:
                            company_found = row
                            break
            except:
                pass
            
            if not company_found:
                self.send_message(message['chat']['id'], f"❌ لم يتم العثور على شركة بالمعرف: {text}")
                return
            
            # حفظ بيانات الشركة للتعديل
            if not hasattr(self, 'edit_company_data'):
                self.edit_company_data = {}
            self.edit_company_data[user_id] = company_found
            
            # عرض بيانات الشركة الحالية
            type_display = {'deposit': 'إيداع فقط', 'withdraw': 'سحب فقط', 'both': 'إيداع وسحب'}.get(company_found['type'], company_found['type'])
            
            edit_options = f"""📊 بيانات الشركة الحالية:

🆔 المعرف: {company_found['id']}
🏢 الاسم: {company_found['name']}
⚡ النوع: {type_display}
📋 التفاصيل: {company_found['details']}
🔘 الحالة: {'نشط' if company_found.get('is_active') == 'active' else 'غير نشط'}

ماذا تريد تعديل؟"""
            
            edit_keyboard = {
                'keyboard': [
                    [{'text': '📝 تعديل الاسم'}, {'text': '🔧 تعديل النوع'}],
                    [{'text': '📋 تعديل التفاصيل'}, {'text': '🔘 تغيير الحالة'}],
                    [{'text': '✅ حفظ التغييرات'}, {'text': '❌ إلغاء'}]
                ],
                'resize_keyboard': True,
                'one_time_keyboard': True
            }
            
            self.send_message(message['chat']['id'], edit_options, edit_keyboard)
            self.user_states[user_id] = 'editing_company_menu'
            
        elif state == 'editing_company_menu':
            if text == '📝 تعديل الاسم':
                current_name = self.edit_company_data[user_id]['name']
                self.send_message(message['chat']['id'], f"📝 الاسم الحالي: {current_name}\n\nأرسل الاسم الجديد:")
                self.user_states[user_id] = 'editing_company_name'
                
            elif text == '🔧 تعديل النوع':
                service_keyboard = {
                    'keyboard': [
                        [{'text': '💳 إيداع فقط'}, {'text': '💰 سحب فقط'}],
                        [{'text': '🔄 إيداع وسحب معاً'}],
                        [{'text': '↩️ العودة للقائمة'}]
                    ],
                    'resize_keyboard': True,
                    'one_time_keyboard': True
                }
                current_type = {'deposit': 'إيداع فقط', 'withdraw': 'سحب فقط', 'both': 'إيداع وسحب'}.get(self.edit_company_data[user_id]['type'])
                self.send_message(message['chat']['id'], f"🔧 النوع الحالي: {current_type}\n\nاختر النوع الجديد:", service_keyboard)
                self.user_states[user_id] = 'editing_company_type'
                
            elif text == '📋 تعديل التفاصيل':
                current_details = self.edit_company_data[user_id]['details']
                self.send_message(message['chat']['id'], f"📋 التفاصيل الحالية: {current_details}\n\nأرسل التفاصيل الجديدة:")
                self.user_states[user_id] = 'editing_company_details'
                
            elif text == '🔘 تغيير الحالة':
                current_status = self.edit_company_data[user_id].get('is_active', 'active')
                new_status = 'inactive' if current_status == 'active' else 'active'
                status_text = 'نشط' if new_status == 'active' else 'غير نشط'
                
                self.edit_company_data[user_id]['is_active'] = new_status
                self.send_message(message['chat']['id'], f"✅ تم تغيير حالة الشركة إلى: {status_text}")
                
                # العودة لقائمة التعديل
                self.show_edit_menu(message, user_id)
                
            elif text == '✅ حفظ التغييرات':
                self.save_company_changes(message)
                
            elif text == '❌ إلغاء':
                del self.user_states[user_id]
                if user_id in self.edit_company_data:
                    del self.edit_company_data[user_id]
                self.send_message(message['chat']['id'], "❌ تم إلغاء تعديل الشركة", self.admin_keyboard())
                
        elif state == 'editing_company_name':
            self.edit_company_data[user_id]['name'] = text
            self.send_message(message['chat']['id'], f"✅ تم تحديث الاسم إلى: {text}")
            self.show_edit_menu(message, user_id)
            
        elif state == 'editing_company_type':
            if text == '💳 إيداع فقط':
                self.edit_company_data[user_id]['type'] = 'deposit'
                self.send_message(message['chat']['id'], "✅ تم تحديث النوع إلى: إيداع فقط")
            elif text == '💰 سحب فقط':
                self.edit_company_data[user_id]['type'] = 'withdraw'
                self.send_message(message['chat']['id'], "✅ تم تحديث النوع إلى: سحب فقط")
            elif text == '🔄 إيداع وسحب معاً':
                self.edit_company_data[user_id]['type'] = 'both'
                self.send_message(message['chat']['id'], "✅ تم تحديث النوع إلى: إيداع وسحب")
            elif text == '↩️ العودة للقائمة':
                pass
            else:
                self.send_message(message['chat']['id'], "❌ اختر نوع الخدمة من الأزرار المتاحة")
                return
            
            self.show_edit_menu(message, user_id)
            
        elif state == 'editing_company_details':
            self.edit_company_data[user_id]['details'] = text
            self.send_message(message['chat']['id'], f"✅ تم تحديث التفاصيل إلى: {text}")
            self.show_edit_menu(message, user_id)
    
    def show_edit_menu(self, message, user_id):
        """عرض قائمة تعديل الشركة"""
        company_data = self.edit_company_data[user_id]
        type_display = {'deposit': 'إيداع فقط', 'withdraw': 'سحب فقط', 'both': 'إيداع وسحب'}.get(company_data['type'], company_data['type'])
        
        edit_options = f"""📊 بيانات الشركة المحدثة:

🆔 المعرف: {company_data['id']}
🏢 الاسم: {company_data['name']}
⚡ النوع: {type_display}
📋 التفاصيل: {company_data['details']}
🔘 الحالة: {'نشط' if company_data.get('is_active') == 'active' else 'غير نشط'}

ماذا تريد تعديل؟"""
        
        edit_keyboard = {
            'keyboard': [
                [{'text': '📝 تعديل الاسم'}, {'text': '🔧 تعديل النوع'}],
                [{'text': '📋 تعديل التفاصيل'}, {'text': '🔘 تغيير الحالة'}],
                [{'text': '✅ حفظ التغييرات'}, {'text': '❌ إلغاء'}]
            ],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(message['chat']['id'], edit_options, edit_keyboard)
        self.user_states[user_id] = 'editing_company_menu'
    
    def save_company_changes(self, message):
        """حفظ تغييرات الشركة"""
        user_id = message['from']['id']
        try:
            companies = []
            updated_company = self.edit_company_data[user_id]
            
            # قراءة جميع الشركات
            with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == updated_company['id']:
                        companies.append(updated_company)
                    else:
                        companies.append(row)
            
            # كتابة الملف المحدث
            with open('companies.csv', 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['id', 'name', 'type', 'details', 'is_active']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(companies)
            
            type_display = {'deposit': 'إيداع فقط', 'withdraw': 'سحب فقط', 'both': 'إيداع وسحب'}.get(updated_company['type'])
            
            success_msg = f"""🎉 تم حفظ التغييرات بنجاح!

🆔 المعرف: {updated_company['id']}
🏢 الاسم: {updated_company['name']}
⚡ النوع: {type_display}
📋 التفاصيل: {updated_company['details']}
🔘 الحالة: {'نشط' if updated_company.get('is_active') == 'active' else 'غير نشط'}"""
            
            self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
            
        except Exception as e:
            self.send_message(message['chat']['id'], f"❌ فشل في حفظ التغييرات: {str(e)}", self.admin_keyboard())
        
        # تنظيف البيانات المؤقتة
        del self.user_states[user_id]
        if user_id in self.edit_company_data:
            del self.edit_company_data[user_id]
    
    def show_companies_management_enhanced(self, message):
        """عرض إدارة الشركات المحسن مع تحديث فوري"""
        companies_text = "🏢 إدارة الشركات المتقدمة\n\n"
        
        try:
            # قراءة جميع الشركات من الملف مع إعادة تحميل الملف
            companies = []
            with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                companies = list(reader)  # تحويل إلى قائمة فوراً
            
            if len(companies) == 0:
                companies_text += "❌ لا توجد شركات مسجلة\n\n"
            else:
                companies_text += f"📊 إجمالي الشركات: {len(companies)}\n"
                companies_text += f"📅 آخر تحديث: {datetime.now().strftime('%H:%M:%S')}\n\n"
                
                for i, row in enumerate(companies, 1):
                    status = "✅" if row.get('is_active', '').lower() == 'active' else "❌"
                    type_display = {'deposit': 'إيداع', 'withdraw': 'سحب', 'both': 'الكل'}.get(row.get('type', ''), row.get('type', ''))
                    companies_text += f"{i}. {status} **{row.get('name', 'غير محدد')}** (ID: {row.get('id', 'غير محدد')})\n"
                    companies_text += f"   🔧 {type_display} | 📋 {row.get('details', 'لا توجد تفاصيل')}\n\n"
                    
        except Exception as e:
            companies_text += f"❌ خطأ في قراءة ملف الشركات: {str(e)}\n\n"
            # محاولة إظهار محتوى الملف للتشخيص
            try:
                with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                    companies_text += f"محتوى الملف:\n{content[:200]}...\n\n"
            except:
                companies_text += "فشل في قراءة محتوى الملف\n\n"
        
        # أزرار الإدارة المتقدمة
        management_keyboard = {
            'keyboard': [
                [{'text': '➕ إضافة شركة جديدة'}, {'text': '✏️ تعديل شركة'}],
                [{'text': '🗑️ حذف شركة'}, {'text': '🔄 تحديث القائمة'}],
                [{'text': '📋 تصدير البيانات'}, {'text': '↩️ العودة للوحة الأدمن'}]
            ],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        companies_text += """🔧 خيارات الإدارة:
• ➕ إضافة شركة جديدة - معالج تفاعلي خطوة بخطوة
• ✏️ تعديل شركة - تعديل البيانات الموجودة
• 🗑️ حذف شركة - حذف نهائي بأمان
• 🔄 تحديث القائمة - إعادة تحميل البيانات"""
        
        self.send_message(message['chat']['id'], companies_text, management_keyboard)
    
    def prompt_delete_company(self, message):
        """بدء معالج حذف الشركة بأمان"""
        companies_text = "🗑️ حذف الشركات:\n\n"
        
        try:
            with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    status = "✅" if row.get('is_active') == 'active' else "❌"
                    companies_text += f"{status} {row['id']} - {row['name']}\n"
                    companies_text += f"   📋 {row['type']} - {row['details']}\n\n"
        except:
            companies_text += "❌ لا توجد شركات\n\n"
        
        companies_text += "⚠️ أرسل رقم معرف الشركة للحذف:\n(تحذير: الحذف نهائي ولا يمكن التراجع عنه)"
        
        self.send_message(message['chat']['id'], companies_text)
        self.user_states[message['from']['id']] = 'confirming_company_delete'
    
    def handle_company_delete_confirmation(self, message):
        """معالج تأكيد حذف الشركة"""
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        company_id = text
        
        # البحث عن الشركة
        company_found = None
        try:
            with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == company_id:
                        company_found = row
                        break
        except:
            pass
        
        if not company_found:
            self.send_message(message['chat']['id'], f"❌ لم يتم العثور على شركة بالمعرف: {company_id}")
            del self.user_states[user_id]
            return
        
        # عرض تأكيد الحذف
        confirm_text = f"""⚠️ تأكيد حذف الشركة:

🆔 المعرف: {company_found['id']}
🏢 الاسم: {company_found['name']}
📋 النوع: {company_found['type']}
📝 التفاصيل: {company_found['details']}

⚠️ هذا الإجراء نهائي ولا يمكن التراجع عنه!
هل أنت متأكد من الحذف؟"""
        
        confirm_keyboard = {
            'keyboard': [
                [{'text': '🗑️ نعم، احذف الشركة'}, {'text': '❌ إلغاء'}]
            ],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(message['chat']['id'], confirm_text, confirm_keyboard)
        self.user_states[user_id] = f'deleting_company_{company_id}'
    
    def finalize_company_delete(self, message, company_id):
        """إنهاء حذف الشركة"""
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        
        if text == '🗑️ نعم، احذف الشركة':
            # تنفيذ الحذف
            companies = []
            deleted_company = None
            
            try:
                with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['id'] != company_id:
                            companies.append(row)
                        else:
                            deleted_company = row
                
                # كتابة الملف بدون الشركة المحذوفة
                with open('companies.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['id', 'name', 'type', 'details', 'is_active']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(companies)
                
                if deleted_company:
                    success_msg = f"""✅ تم حذف الشركة بنجاح!

🗑️ الشركة المحذوفة:
🆔 المعرف: {deleted_company['id']}
🏢 الاسم: {deleted_company['name']}
📋 النوع: {deleted_company['type']}"""
                    
                    self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
                else:
                    self.send_message(message['chat']['id'], "❌ فشل في العثور على الشركة للحذف", self.admin_keyboard())
                    
            except Exception as e:
                self.send_message(message['chat']['id'], f"❌ فشل في حذف الشركة: {str(e)}", self.admin_keyboard())
        
        elif text == '❌ إلغاء':
            self.send_message(message['chat']['id'], "❌ تم إلغاء حذف الشركة", self.admin_keyboard())
        
        # تنظيف الحالة
        del self.user_states[user_id]
    
    def show_quick_copy_commands(self, message):
        """عرض أوامر نسخ سريعة للأدمن"""
        commands_text = """📋 أوامر نسخ سريعة:

🔥 **أوامر الموافقة والرفض:**
• `موافقة DEP123456`
• `موافق DEP123456`
• `تأكيد DEP123456`
• `نعم DEP123456`

• `رفض DEP123456 مبلغ غير صحيح`
• `لا DEP123456 بيانات ناقصة`
• `مرفوض WTH789012 رقم محفظة خطأ`

💼 **أوامر إدارة الشركات:**
• `اضافة_شركة البنك_الأهلي deposit حساب_بنكي_123456789`
• `اضافة_شركة فودافون_كاش both محفظة_الكترونية`
• `حذف_شركة 1737570855`

💳 **أوامر وسائل الدفع:**
• `اضافة_وسيلة_دفع 1 بنك_الأهلي حساب_بنكي SA123456789012345678`
• `حذف_وسيلة_دفع 123456`
• `تعديل_وسيلة_دفع 123456 SA987654321098765432`

📧 **أوامر الرسائل:**
• النقر على "📧 إرسال رسالة لعميل" ثم إدخال رقم العميل

👥 **أوامر إدارة المستخدمين:**
• `بحث أحمد`
• `بحث C123456`
• `حظر C123456 مخالفة الشروط`
• `الغاء_حظر C123456`

📨 **أوامر الشكاوى:**
• `رد_شكوى 123 شكراً لتواصلك`
• `رد_شكوى 456 تم حل مشكلتك`
• `رد_شكوى 789 نراجع طلبك`

🏢 **أوامر أخرى:**
• `عنوان_جديد شارع الملك فهد الرياض`
• `تعديل_اعداد min_deposit 100`

💡 **نصائح للاستخدام:**
• انقر على أي أمر واختر 'نسخ'
• غير الأرقام والنصوص حسب الحاجة
• استخدم _ بدلاً من المسافات في أسماء الشركات"""
        
        self.send_message(message['chat']['id'], commands_text, self.admin_keyboard())
    
    def get_payment_methods_by_company(self, company_id, transaction_type=None):
        """الحصول على وسائل الدفع لشركة معينة"""
        methods = []
        try:
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if (row['company_id'] == str(company_id) and 
                        row['status'] == 'active'):
                        methods.append(row)
        except:
            pass
        return methods
    
    def show_payment_method_selection(self, message, company_id, transaction_type):
        """عرض وسائل الدفع المتاحة للشركة"""
        user_id = message['from']['id']
        methods = self.get_payment_methods_by_company(company_id, transaction_type)
        
        if not methods:
            self.send_message(message['chat']['id'], 
                            "❌ لا توجد وسائل دفع متاحة لهذه الشركة حالياً",
                            self.main_keyboard('ar'))
            return
        
        methods_text = f"💳 اختر وسيلة الدفع:\n\n"
        keyboard = []
        
        for method in methods:
            methods_text += f"🔹 {method['method_name']}\n"
            methods_text += f"   📋 {method['method_type']}\n"
            if method['additional_info']:
                methods_text += f"   💡 {method['additional_info']}\n"
            methods_text += "\n"
            
            keyboard.append([{'text': method['method_name']}])
        
        keyboard.append([{'text': '🔙 العودة لاختيار الشركة'}])
        
        # حفظ الحالة
        self.user_states[user_id] = {
            'step': 'selecting_payment_method',
            'company_id': company_id,
            'transaction_type': transaction_type,
            'methods': methods
        }
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(message['chat']['id'], methods_text, reply_keyboard)
    
    def add_payment_method(self, company_id, method_name, method_type, account_data, additional_info=""):
        """إضافة وسيلة دفع جديدة"""
        try:
            # إنشاء ID جديد  
            new_id = int(datetime.now().timestamp() * 1000) % 1000000
            
            # إضافة الوسيلة الجديدة
            with open('payment_methods.csv', 'a', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    new_id,
                    company_id,
                    method_name,
                    method_type,
                    account_data,
                    additional_info,
                    'active',
                    datetime.now().strftime('%Y-%m-%d')
                ])
            return True
        except:
            return False
    
    def edit_payment_method(self, method_id, new_data):
        """تعديل وسيلة دفع موجودة"""
        try:
            methods = []
            found = False
            
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == str(method_id):
                        # تحديث البيانات
                        for key, value in new_data.items():
                            if key in row:
                                row[key] = value
                        found = True
                    methods.append(row)
            
            if found:
                # كتابة البيانات المحدثة
                with open('payment_methods.csv', 'w', encoding='utf-8-sig', newline='') as f:
                    if methods:
                        fieldnames = methods[0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(methods)
                return True
        except:
            pass
        return False
    
    def delete_payment_method(self, method_id):
        """حذف وسيلة دفع مع إرجاع البيانات المحذوفة"""
        try:
            methods = []
            deleted_method = None
            
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] != str(method_id):
                        methods.append(row)
                    else:
                        deleted_method = row.copy()
            
            if deleted_method:
                # كتابة الملف حتى لو كان فارغ
                with open('payment_methods.csv', 'w', encoding='utf-8-sig', newline='') as f:
                    fieldnames = ['id', 'company_id', 'method_name', 'method_type', 'account_data', 'additional_info', 'status', 'created_date']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    if methods:  # فقط اكتب الصفوف إذا كانت موجودة
                        writer.writerows(methods)
                
                logger.info(f"تم حذف وسيلة الدفع {method_id}: {deleted_method.get('method_name', 'غير محدد')}")
                return True, deleted_method
            
            return False, None
        except Exception as e:
            logger.error(f"خطأ في حذف وسيلة الدفع {method_id}: {e}")
            return False, None
    
    def start_add_company_wizard(self, message):
        """بدء معالج إضافة شركة تفاعلي"""
        wizard_text = """🧙‍♂️ معالج إضافة الشركة

سأساعدك في إضافة شركة بطريقة سهلة!

📝 أولاً: ما اسم الشركة؟
(مثال: بنك الراجحي، فودافون كاش، مدى)"""
        
        self.send_message(message['chat']['id'], wizard_text)
        self.user_states[message['from']['id']] = 'adding_company_name'
    
    def handle_add_company_wizard(self, message, text):
        """معالجة معالج إضافة الشركة"""
        user_id = message['from']['id']
        state = self.user_states.get(user_id, '')
        
        if state == 'adding_company_name':
            company_name = text.strip()
            if len(company_name) < 2:
                self.send_message(message['chat']['id'], "❌ اسم قصير جداً. أدخل اسم الشركة:")
                return
            
            # عرض أنواع الخدمة
            service_keyboard = {
                'keyboard': [
                    [{'text': '💰 إيداع فقط'}, {'text': '💸 سحب فقط'}],
                    [{'text': '🔄 إيداع وسحب معاً'}],
                    [{'text': '❌ إلغاء'}, {'text': '🔄 إعادة تعيين النظام'}]
                ],
                'resize_keyboard': True,
                'one_time_keyboard': True
            }
            
            self.send_message(message['chat']['id'], f"✅ اسم الشركة: {company_name}\n\n🔹 اختر نوع الخدمة:", service_keyboard)
            self.user_states[user_id] = f'adding_company_type_{company_name}'
            
        elif state.startswith('adding_company_type_'):
            company_name = state.replace('adding_company_type_', '')
            
            if text == '❌ إلغاء':
                self.send_message(message['chat']['id'], "تم إلغاء إضافة الشركة", self.admin_keyboard())
                del self.user_states[user_id]
                return
            
            # تحديد نوع الخدمة
            if text == '💰 إيداع فقط':
                service_type = 'deposit'
                service_ar = 'إيداع فقط'
            elif text == '💸 سحب فقط':
                service_type = 'withdraw'
                service_ar = 'سحب فقط'
            elif text == '🔄 إيداع وسحب معاً':
                service_type = 'both'
                service_ar = 'إيداع وسحب'
            else:
                self.send_message(message['chat']['id'], "❌ اختر من الأزرار المتاحة:")
                return
            
            self.send_message(message['chat']['id'], f"""✅ تم اختيار: {service_ar}

📝 الآن أدخل تفاصيل الشركة:
(مثال: حساب بنكي رقم 1234567890، محفظة إلكترونية، خدمات دفع متعددة)""")
            
            self.user_states[user_id] = f'adding_company_details_{company_name}_{service_type}'
            
        elif state.startswith('adding_company_details_'):
            parts = state.replace('adding_company_details_', '').rsplit('_', 1)
            company_name = parts[0]
            service_type = parts[1]
            details = text.strip()
            
            if len(details) < 3:
                self.send_message(message['chat']['id'], "❌ تفاصيل قصيرة جداً. أدخل وصف مناسب:")
                return
            
            # إنشاء الشركة
            company_id = str(int(datetime.now().timestamp()))
            
            try:
                with open('companies.csv', 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow([company_id, company_name, service_type, details, 'active'])
                
                service_ar = "إيداع فقط" if service_type == 'deposit' else "سحب فقط" if service_type == 'withdraw' else "إيداع وسحب"
                
                success_msg = f"""✅ تم إضافة الشركة بنجاح!

🆔 المعرف: {company_id}
🏢 الاسم: {company_name}
⚡ النوع: {service_ar}
📋 التفاصيل: {details}
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}

الشركة أصبحت متاحة الآن للعملاء."""
                
                self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
                del self.user_states[user_id]
                
            except Exception as e:
                self.send_message(message['chat']['id'], f"❌ فشل في إضافة الشركة: {str(e)}", self.admin_keyboard())
                del self.user_states[user_id]
    
    def show_companies_management(self, message):
        """عرض إدارة الشركات"""
        companies_text = "🏢 إدارة الشركات:\n\n"
        
        try:
            with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    status = "✅" if row.get('is_active') == 'active' else "❌"
                    companies_text += f"{status} {row['id']} - {row['name']}\n"
                    companies_text += f"   📋 {row['type']} - {row['details']}\n\n"
        except:
            pass
        
        companies_text += "📝 الأوامر:\n"
        companies_text += "• اضافة_شركة اسم نوع تفاصيل\n"
        companies_text += "• حذف_شركة رقم_المعرف\n"
        
        self.send_message(message['chat']['id'], companies_text, self.admin_keyboard())
    
    def show_addresses_management(self, message):
        """عرض إدارة العناوين"""
        current_address = self.get_exchange_address()
        
        address_text = f"""📍 إدارة عناوين الصرافة

العنوان الحالي:
{current_address}

لتغيير العنوان:
عنوان_جديد النص_الجديد_للعنوان

مثال:
عنوان_جديد شارع الملك فهد، الرياض، مقابل برج المملكة"""
        
        self.send_message(message['chat']['id'], address_text, self.admin_keyboard())
    
    def show_system_settings(self, message):
        """عرض إعدادات النظام"""
        settings_text = "⚙️ إعدادات النظام:\n\n"
        
        try:
            with open('system_settings.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    settings_text += f"🔧 {row['setting_key']}: {row['setting_value']}\n"
                    settings_text += f"   📝 {row['description']}\n\n"
        except:
            pass
        
        settings_text += "📝 لتعديل إعداد:\n"
        settings_text += "تعديل_اعداد مفتاح_الإعداد القيمة_الجديدة\n\n"
        settings_text += "مثال:\nتعديل_اعداد min_deposit 100"
        
        self.send_message(message['chat']['id'], settings_text, self.admin_keyboard())
    
    def show_complaints_admin(self, message):
        """عرض الشكاوى مع أزرار رد سهلة"""
        complaints_text = "📨 الشكاوى:\n\n"
        keyboard = []
        
        try:
            with open('complaints.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                pending_complaints = [row for row in reader if row['status'] == 'pending']
                
                if not pending_complaints:
                    complaints_text += "✅ لا توجد شكاوى معلقة"
                    keyboard = [
                        [{'text': '🔄 تحديث'}],
                        [{'text': '↩️ العودة للوحة الأدمن'}]
                    ]
                else:
                    for complaint in pending_complaints:
                        complaints_text += f"🆔 {complaint['id']}\n"
                        complaints_text += f"👤 {complaint['customer_id']}\n"
                        complaints_text += f"📝 {complaint['message']}\n"
                        complaints_text += f"📅 {complaint['date']}\n\n"
                        
                        # إضافة أزرار رد سريعة
                        keyboard.append([{'text': f"📞 رد على {complaint['id']}"}])
                    
                    keyboard.extend([
                        [{'text': '🔄 تحديث'}],
                        [{'text': '↩️ العودة للوحة الأدمن'}]
                    ])
                        
        except Exception as e:
            complaints_text += f"❌ خطأ في قراءة الشكاوى: {e}"
            keyboard = [
                [{'text': '🔄 تحديث'}],
                [{'text': '↩️ العودة للوحة الأدمن'}]
            ]
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
        
        self.send_message(message['chat']['id'], complaints_text, reply_keyboard)
    
    def start_complaint_reply_wizard(self, message, complaint_id):
        """بدء معالج الرد على الشكوى"""
        # البحث عن الشكوى
        complaint_found = False
        complaint_data = None
        
        try:
            with open('complaints.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == complaint_id:
                        complaint_found = True
                        complaint_data = row
                        break
        except:
            pass
        
        if not complaint_found:
            self.send_message(message['chat']['id'], f"❌ لم يتم العثور على الشكوى {complaint_id}", self.admin_keyboard())
            return
        
        # عرض تفاصيل الشكوى مع أزرار ردود سريعة
        reply_text = f"""📞 الرد على الشكوى:

🆔 رقم الشكوى: {complaint_id}
👤 العميل: {complaint_data['customer_id']}
📝 الشكوى: {complaint_data['message']}
📅 التاريخ: {complaint_data['date']}

اختر رد سريع أو اكتب رد مخصص:"""
        
        keyboard = [
            [{'text': f"✅ تم الحل - {complaint_id}"}],
            [{'text': f"🔍 قيد المراجعة - {complaint_id}"}],
            [{'text': f"📞 سنتواصل معك - {complaint_id}"}],
            [{'text': f"💡 رد مخصص - {complaint_id}"}],
            [{'text': '🔙 العودة للشكاوى'}]
        ]
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(message['chat']['id'], reply_text, reply_keyboard)
        self.user_states[message['from']['id']] = f'replying_to_complaint_{complaint_id}'
    
    def show_payment_methods_admin(self, message):
        """عرض وسائل الدفع للأدمن"""
        payment_text = """💳 وسائل الدفع المتاحة

هذا القسم يعرض الشركات المتاحة للإيداع والسحب.
استخدم 'إدارة الشركات' لإضافة أو تعديل وسائل الدفع."""
        
        companies = self.get_companies()
        for company in companies:
            service_type = "إيداع وسحب" if company['type'] == 'both' else "إيداع" if company['type'] == 'deposit' else "سحب"
            payment_text += f"\n🏢 {company['name']}\n"
            payment_text += f"   📋 {service_type} - {company['details']}\n"
        
        self.send_message(message['chat']['id'], payment_text, self.admin_keyboard())
    
    def ban_user_admin(self, message, customer_id, reason):
        """حظر مستخدم من قبل الأدمن"""
        users = []
        success = False
        
        try:
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['customer_id'] == customer_id:
                        row['is_banned'] = 'yes'
                        row['ban_reason'] = reason
                        success = True
                    users.append(row)
            
            if success:
                with open('users.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['telegram_id', 'name', 'phone', 'customer_id', 'language', 'date', 'is_banned', 'ban_reason']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(users)
                
                self.send_message(message['chat']['id'], f"✅ تم حظر العميل {customer_id}\nالسبب: {reason}", self.admin_keyboard())
            else:
                self.send_message(message['chat']['id'], f"❌ لم يتم العثور على العميل {customer_id}", self.admin_keyboard())
        except:
            self.send_message(message['chat']['id'], "❌ فشل في حظر المستخدم", self.admin_keyboard())
    
    def unban_user_admin(self, message, customer_id):
        """إلغاء حظر مستخدم من قبل الأدمن"""
        users = []
        success = False
        
        try:
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['customer_id'] == customer_id:
                        row['is_banned'] = 'no'
                        row['ban_reason'] = ''
                        success = True
                    users.append(row)
            
            if success:
                with open('users.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['telegram_id', 'name', 'phone', 'customer_id', 'language', 'date', 'is_banned', 'ban_reason']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(users)
                
                self.send_message(message['chat']['id'], f"✅ تم إلغاء حظر العميل {customer_id}", self.admin_keyboard())
            else:
                self.send_message(message['chat']['id'], f"❌ لم يتم العثور على العميل {customer_id}", self.admin_keyboard())
        except:
            self.send_message(message['chat']['id'], "❌ فشل في إلغاء حظر المستخدم", self.admin_keyboard())
    
    def delete_company_simple(self, message, company_id):
        """حذف شركة بسيط"""
        companies = []
        deleted = False
        
        try:
            with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] != company_id:
                        companies.append(row)
                    else:
                        deleted = True
                        deleted_name = row.get('name', 'Unknown')
            
            if deleted:
                with open('companies.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['id', 'name', 'type', 'details', 'is_active']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(companies)
                
                self.send_message(message['chat']['id'], f"✅ تم حذف الشركة: {deleted_name} (ID: {company_id})", self.admin_keyboard())
            else:
                self.send_message(message['chat']['id'], f"❌ لم يتم العثور على شركة بالمعرف: {company_id}", self.admin_keyboard())
        except:
            self.send_message(message['chat']['id'], "❌ فشل في حذف الشركة", self.admin_keyboard())
    
    def update_setting_simple(self, message, text):
        """تحديث إعداد النظام"""
        # تنسيق: تعديل_اعداد مفتاح_الإعداد القيمة_الجديدة
        parts = text.replace('تعديل_اعداد ', '').split(' ', 1)
        if len(parts) < 2:
            help_text = """❌ تنسيق خاطئ

الصيغة الصحيحة:
تعديل_اعداد مفتاح_الإعداد القيمة_الجديدة

مثال:
تعديل_اعداد min_deposit 100"""
            self.send_message(message['chat']['id'], help_text, self.admin_keyboard())
            return
        
        setting_key = parts[0]
        setting_value = parts[1]
        
        settings = []
        updated = False
        
        try:
            with open('system_settings.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['setting_key'] == setting_key:
                        row['setting_value'] = setting_value
                        updated = True
                    settings.append(row)
            
            if updated:
                with open('system_settings.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['setting_key', 'setting_value', 'description']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(settings)
                
                self.send_message(message['chat']['id'], f"✅ تم تحديث الإعداد:\n{setting_key} = {setting_value}", self.admin_keyboard())
            else:
                self.send_message(message['chat']['id'], f"❌ لم يتم العثور على الإعداد: {setting_key}", self.admin_keyboard())
        except:
            self.send_message(message['chat']['id'], "❌ فشل في تحديث الإعداد", self.admin_keyboard())
    
    def save_complaint(self, message, complaint_text):
        """حفظ شكوى المستخدم"""
        user = self.find_user(message['from']['id'])
        if not user:
            return
        
        complaint_id = f"COMP{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        try:
            # إنشاء ملف الشكاوى مع الهيكل الصحيح إذا لم يكن موجوداً
            if not os.path.exists('complaints.csv'):
                with open('complaints.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['id', 'customer_id', 'subject', 'message', 'status', 'date', 'admin_response'])
            
            # إضافة الشكوى الجديدة
            with open('complaints.csv', 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([complaint_id, user['customer_id'], 'شكوى جديدة', complaint_text, 'pending', 
                               datetime.now().strftime('%Y-%m-%d %H:%M'), ''])
            
            confirmation = f"""✅ تم إرسال شكواك بنجاح

🆔 رقم الشكوى: {complaint_id}
📝 المحتوى: {complaint_text}
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}

سيتم الرد عليك في أقرب وقت ممكن."""
            
            self.send_message(message['chat']['id'], confirmation, self.main_keyboard(user.get('language', 'ar')))
            if message['from']['id'] in self.user_states:
                del self.user_states[message['from']['id']]
            
            # إشعار الأدمن بالشكوى الجديدة
            admin_msg = f"""📨 شكوى جديدة

🆔 {complaint_id}
👤 {user['name']} ({user['customer_id']})
📝 الشكوى: {complaint_text}
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
            
            self.notify_admins(admin_msg)
            
        except Exception as e:
            logger.error(f"خطأ في حفظ الشكوى: {e}")
            self.send_message(message['chat']['id'], "❌ فشل في إرسال الشكوى. حاول مرة أخرى", self.main_keyboard(user.get('language', 'ar')))
            if message['from']['id'] in self.user_states:
                del self.user_states[message['from']['id']]
    
    def send_broadcast_message(self, message, broadcast_text):
        """إرسال رسالة جماعية"""
        sent_count = 0
        failed_count = 0
        
        try:
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                users = list(reader)
            
            # إرسال للمستخدمين النشطين فقط
            for user in users:
                if user.get('is_banned') != 'yes':
                    try:
                        broadcast_msg = f"""📢 رسالة من الإدارة

{broadcast_text}

📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
                        
                        # إرسال الرسالة بدون لوحة مفاتيح حتى لا تؤثر على الأزرار الحالية
                        result = self.send_message(user['telegram_id'], broadcast_msg, None)
                        if result and result.get('ok'):
                            sent_count += 1
                        else:
                            failed_count += 1
                    except:
                        failed_count += 1
            
            summary = f"""✅ تم إرسال الرسالة الجماعية

📊 الإحصائيات:
• تم الإرسال بنجاح: {sent_count}
• فشل في الإرسال: {failed_count}
• إجمالي المحاولات: {sent_count + failed_count}

📝 الرسالة: {broadcast_text}"""
            
            self.send_message(message['chat']['id'], summary, self.admin_keyboard())
            del self.user_states[message['from']['id']]
        except:
            self.send_message(message['chat']['id'], "❌ فشل في الإرسال الجماعي", self.admin_keyboard())
            del self.user_states[message['from']['id']]

    def show_approved_transactions(self, message):
        """عرض المعاملات المُوافق عليها"""
        approved_text = "✅ المعاملات المُوافق عليها (آخر 20 معاملة):\n\n"
        found_approved = False
        count = 0
        
        try:
            with open('transactions.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                transactions = list(reader)
                
                # عكس الترتيب للحصول على أحدث المعاملات
                for row in reversed(transactions):
                    if row['status'] == 'approved' and count < 20:
                        found_approved = True
                        count += 1
                        type_emoji = "💰" if row['type'] == 'deposit' else "💸"
                        
                        approved_text += f"{type_emoji} {row['id']}\n"
                        approved_text += f"👤 {row['name']}\n"
                        approved_text += f"💰 {row['amount']} ريال\n"
                        approved_text += f"📅 {row['date']}\n\n"
        except:
            pass
        
        if not found_approved:
            approved_text += "لا توجد معاملات مُوافق عليها"
        
        self.send_message(message['chat']['id'], approved_text, self.admin_keyboard())
    
    def show_users_management(self, message):
        """عرض إدارة المستخدمين"""
        users_text = "👥 إدارة المستخدمين:\n\n"
        active_count = 0
        banned_count = 0
        
        try:
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('is_banned') == 'yes':
                        banned_count += 1
                    else:
                        active_count += 1
        except:
            pass
        
        users_text += f"✅ مستخدمون نشطون: {active_count}\n"
        users_text += f"🚫 مستخدمون محظورون: {banned_count}\n\n"
        
        users_text += "📝 الأوامر المتاحة:\n"
        users_text += "• بحث اسم_أو_رقم_العميل\n"
        users_text += "• حظر رقم_العميل السبب\n"
        users_text += "• الغاء_حظر رقم_العميل\n\n"
        
        users_text += "مثال:\nبحث أحمد\nحظر C123456 مخالفة_الشروط"
        
        self.send_message(message['chat']['id'], users_text, self.admin_keyboard())
    
    def search_users_admin(self, message, query):
        """البحث في المستخدمين للأدمن"""
        results = []
        try:
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if (query.lower() in row['name'].lower() or 
                        query in row['customer_id'] or 
                        query in row['phone']):
                        results.append(row)
        except:
            pass
        
        if not results:
            self.send_message(message['chat']['id'], f"❌ لم يتم العثور على نتائج للبحث: {query}", self.admin_keyboard())
            return
        
        search_text = f"🔍 نتائج البحث عن: {query}\n\n"
        for user in results[:10]:  # أول 10 نتائج فقط
            status = "🚫 محظور" if user.get('is_banned') == 'yes' else "✅ نشط"
            search_text += f"👤 {user['name']}\n"
            search_text += f"🆔 {user['customer_id']}\n"
            search_text += f"📱 {user['phone']}\n"
            search_text += f"🔸 {status}\n"
            if user.get('is_banned') == 'yes' and user.get('ban_reason'):
                search_text += f"📝 سبب الحظر: {user['ban_reason']}\n"
            search_text += "\n"
        
        self.send_message(message['chat']['id'], search_text, self.admin_keyboard())
    
    def start_simple_payment_method_wizard(self, message):
        """معالج مبسط لإضافة وسيلة دفع"""
        user_id = message['from']['id']
        
        # عرض الشركات المتاحة
        companies = self.get_companies()
        if not companies:
            self.send_message(message['chat']['id'], 
                            "❌ لا توجد شركات متاحة. يجب إضافة شركة أولاً", 
                            self.admin_keyboard())
            return
        
        companies_text = "🏢 اختر الشركة لإضافة وسيلة دفع:\n\n"
        keyboard = []
        
        for company in companies:
            companies_text += f"🔹 {company['name']}\n"
            keyboard.append([{'text': f"🏢 {company['name']}"}])
        
        keyboard.append([{'text': '🔙 العودة'}])
        
        self.user_states[user_id] = 'adding_payment_simple'
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(message['chat']['id'], companies_text, reply_keyboard)
    
    def start_edit_payment_method_wizard(self, message):
        """معالج مبسط لتعديل وسيلة دفع"""
        methods = self.get_all_payment_methods()
        if not methods:
            self.send_message(message['chat']['id'], "❌ لا توجد وسائل دفع متاحة", self.admin_keyboard())
            return
        
        methods_text = "✏️ اختر وسيلة الدفع للتعديل:\n\n"
        keyboard = []
        
        for method in methods:
            company = self.get_company_by_id(method['company_id'])
            company_name = company['name'] if company else 'غير محدد'
            
            methods_text += f"🆔 {method['id']} - {method['method_name']}\n"
            methods_text += f"   🏢 {company_name}\n"
            methods_text += f"   💳 {method['method_type']}\n\n"
            
            keyboard.append([{'text': f"تعديل {method['id']}"}])
        
        keyboard.append([{'text': '🔙 العودة'}])
        
        self.user_states[message['from']['id']] = 'selecting_method_to_edit_simple'
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(message['chat']['id'], methods_text, reply_keyboard)
    
    def start_delete_payment_method_wizard(self, message):
        """معالج مبسط لحذف وسيلة دفع"""
        methods = self.get_all_payment_methods()
        if not methods:
            self.send_message(message['chat']['id'], "❌ لا توجد وسائل دفع متاحة", self.admin_keyboard())
            return
        
        methods_text = "🗑️ اختر وسيلة الدفع للحذف:\n\n"
        keyboard = []
        
        for method in methods:
            company = self.get_company_by_id(method['company_id'])
            company_name = company['name'] if company else 'غير محدد'
            
            methods_text += f"🆔 {method['id']} - {method['method_name']}\n"
            methods_text += f"   🏢 {company_name}\n\n"
            
            keyboard.append([{'text': f"حذف {method['id']}"}])
        
        keyboard.append([{'text': '🔙 العودة'}])
        
        self.user_states[message['from']['id']] = 'selecting_method_to_delete_simple'
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(message['chat']['id'], methods_text, reply_keyboard)
    
    def show_all_payment_methods_simplified(self, message):
        """عرض مبسط لجميع وسائل الدفع"""
        methods = self.get_all_payment_methods()
        
        if not methods:
            self.send_message(message['chat']['id'], "❌ لا توجد وسائل دفع مضافة بعد", self.admin_keyboard())
            return
        
        methods_text = "📊 وسائل الدفع المتاحة:\n\n"
        
        for method in methods:
            company = self.get_company_by_id(method['company_id'])
            company_name = company['name'] if company else 'غير محدد'
            status = "✅ نشط" if method['status'] == 'active' else "❌ متوقف"
            
            methods_text += f"🆔 {method['id']} - {method['method_name']}\n"
            methods_text += f"🏢 الشركة: {company_name}\n"
            methods_text += f"💳 النوع: {method['method_type']}\n"
            methods_text += f"💰 البيانات: {method['account_data']}\n"
            methods_text += f"📊 الحالة: {status}\n"
            if method['additional_info']:
                methods_text += f"💡 معلومات: {method['additional_info']}\n"
            methods_text += "─────────────\n\n"
        
        methods_text += f"📈 إجمالي وسائل الدفع: {len(methods)}"
        
        self.send_message(message['chat']['id'], methods_text, self.admin_keyboard())
    
    def handle_simple_payment_company_selection(self, message):
        """معالجة اختيار الشركة في المعالج المبسط"""
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        
        if text in ['🔙 العودة', '⬅️ العودة']:
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.show_payment_methods_management(message)
            return
        
        # البحث عن الشركة
        company_name = text.replace('🏢 ', '')
        companies = self.get_companies()
        selected_company = None
        
        for company in companies:
            if company['name'] == company_name:
                selected_company = company
                break
        
        if not selected_company:
            self.send_message(message['chat']['id'], "❌ شركة غير صحيحة. اختر من القائمة أعلاه")
            return
        
        # طلب بيانات وسيلة الدفع
        input_text = f"""📋 إضافة وسيلة دفع للشركة: {selected_company['name']}

أدخل البيانات بالتنسيق التالي:
اسم_الوسيلة | نوع_الوسيلة | رقم_الحساب | معلومات_إضافية

مثال:
بنك الأهلي | حساب بنكي | SA1234567890123456789 | حساب رئيسي
أو
فودافون كاش | محفظة إلكترونية | 01012345678 | للدفع السريع

⬅️ /cancel للإلغاء"""
        
        self.send_message(message['chat']['id'], input_text)
        self.user_states[user_id] = f'adding_payment_method_{selected_company["id"]}'
    
    def handle_simple_payment_method_data(self, message):
        """معالجة بيانات وسيلة الدفع المبسطة"""
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        state = self.user_states.get(user_id, '')
        
        if text == '/cancel':
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.show_payment_methods_management(message)
            return
        
        # استخراج معرف الشركة
        company_id = state.replace('adding_payment_method_', '')
        
        # تحليل البيانات المدخلة
        if '|' in text:
            parts = [part.strip() for part in text.split('|')]
            if len(parts) >= 3:
                method_name = parts[0]
                method_type = parts[1]
                account_data = parts[2]
                additional_info = parts[3] if len(parts) > 3 else ""
                
                # إضافة وسيلة الدفع
                success = self.add_payment_method(company_id, method_name, method_type, account_data, additional_info)
                
                if success:
                    company = self.get_company_by_id(company_id)
                    company_name = company['name'] if company else 'غير محدد'
                    
                    success_msg = f"""✅ تم إضافة وسيلة الدفع بنجاح!

🏢 الشركة: {company_name}
📋 الاسم: {method_name}
💳 النوع: {method_type}
💰 البيانات: {account_data}
💡 معلومات: {additional_info if additional_info else 'لا توجد'}"""
                    
                    self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
                else:
                    self.send_message(message['chat']['id'], "❌ فشل في إضافة وسيلة الدفع", self.admin_keyboard())
            else:
                self.send_message(message['chat']['id'], "❌ تنسيق غير صحيح. يجب أن يحتوي على 3 أجزاء على الأقل مفصولة بـ |")
                return
        else:
            self.send_message(message['chat']['id'], "❌ تنسيق غير صحيح. استخدم | للفصل بين البيانات")
            return
        
        # تنظيف الحالة
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    def handle_simple_method_edit_selection(self, message):
        """معالجة اختيار وسيلة الدفع للتعديل المبسط"""
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        
        if text in ['🔙 العودة', '⬅️ العودة']:
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.show_payment_methods_management(message)
            return
        
        if text.startswith('تعديل '):
            method_id = text.replace('تعديل ', '').strip()
            method = self.get_payment_method_by_id(method_id)
            
            if not method:
                self.send_message(message['chat']['id'], "❌ وسيلة دفع غير موجودة")
                return
            
            company = self.get_company_by_id(method['company_id'])
            company_name = company['name'] if company else 'غير محدد'
            
            edit_text = f"""✏️ تعديل وسيلة الدفع

🆔 المعرف: {method['id']}
🏢 الشركة: {company_name}
📋 الاسم الحالي: {method['method_name']}
💳 النوع الحالي: {method['method_type']}
💰 البيانات الحالية: {method['account_data']}
💡 المعلومات الحالية: {method['additional_info']}

أدخل البيانات الجديدة بالتنسيق:
اسم_جديد | نوع_جديد | رقم_حساب_جديد | معلومات_جديدة

⬅️ /cancel للإلغاء"""
            
            self.send_message(message['chat']['id'], edit_text)
            self.user_states[user_id] = f'editing_method_simple_{method_id}'
    
    def handle_simple_method_delete_selection(self, message):
        """معالجة اختيار وسيلة الدفع للحذف المبسط"""
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        
        if text in ['🔙 العودة', '⬅️ العودة']:
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.show_payment_methods_management(message)
            return
        
        if text.startswith('حذف '):
            method_id = text.replace('حذف ', '').strip()
            
            # الحصول على بيانات الوسيلة قبل الحذف
            method_to_delete = self.get_payment_method_by_id(method_id)
            if not method_to_delete:
                self.send_message(message['chat']['id'], f"❌ لم يتم العثور على وسيلة الدفع {method_id}", self.admin_keyboard())
                if user_id in self.user_states:
                    del self.user_states[user_id]
                return
            
            # حذف وسيلة الدفع
            success, deleted_method = self.delete_payment_method(method_id)
            
            if success and deleted_method:
                company = self.get_company_by_id(deleted_method['company_id'])
                company_name = company['name'] if company else 'غير محدد'
                
                success_msg = f"""✅ تم حذف وسيلة الدفع بنجاح!

🆔 المحذوفة: {deleted_method['id']}
🏢 الشركة: {company_name}
📋 الاسم: {deleted_method['method_name']}
💳 النوع: {deleted_method['method_type']}"""
                
                self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
            else:
                self.send_message(message['chat']['id'], f"❌ فشل في حذف وسيلة الدفع {method_id}", self.admin_keyboard())
            
            # تنظيف الحالة
            if user_id in self.user_states:
                del self.user_states[user_id]
    
    def handle_simple_method_edit_data(self, message, method_id):
        """معالجة بيانات التعديل المبسط"""
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        
        if text == '/cancel':
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.show_payment_methods_management(message)
            return
        
        # تحليل البيانات الجديدة - تنسيق مبسط
        if '|' in text:
            parts = [part.strip() for part in text.split('|')]
            if len(parts) >= 3:
                new_name = parts[0]
                new_type = parts[1]
                new_account = parts[2]
                new_info = parts[3] if len(parts) > 3 else ""
                
                # التحقق من وجود الوسيلة قبل التحديث
                existing_method = self.get_payment_method_by_id(method_id)
                if not existing_method:
                    self.send_message(message['chat']['id'], f"❌ لم يتم العثور على وسيلة الدفع رقم {method_id}", self.admin_keyboard())
                    if user_id in self.user_states:
                        del self.user_states[user_id]
                    return
                
                # تحديث وسيلة الدفع
                logger.info(f"محاولة تحديث وسيلة الدفع - المعرف: {method_id}, الاسم: {new_name}, البيانات: {new_account}")
                
                # تسجيل البيانات للتشخيص
                logger.info(f"البيانات المدخلة: الاسم={new_name}, النوع={new_type}, الحساب={new_account}, المعلومات={new_info}")
                
                success = self.update_payment_method_safe(method_id, new_name, new_type, new_account, new_info)
                
                if success:
                    # الحصول على بيانات الشركة
                    company = self.get_company_by_id(existing_method['company_id'])
                    company_name = company['name'] if company else 'غير محدد'
                    
                    success_msg = f"""✅ تم تعديل وسيلة الدفع بنجاح!

🆔 المعرف: {method_id}
🏢 الشركة: {company_name}
📋 الاسم: {new_name}
💳 النوع: {new_type}
💰 البيانات: {new_account}
💡 معلومات إضافية: {new_info if new_info else 'لا توجد'}"""
                    
                    self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
                else:
                    self.send_message(message['chat']['id'], f"❌ فشل في تعديل وسيلة الدفع {method_id}", self.admin_keyboard())
            else:
                self.send_message(message['chat']['id'], "❌ تنسيق غير صحيح!\n\nالتنسيق المطلوب:\nاسم_الوسيلة | نوع_الوسيلة | رقم_الحساب | معلومات_إضافية\n\nمثال:\nفودافون كاش | محفظة إلكترونية | 01012345678 | للدفع السريع")
                return
        else:
            self.send_message(message['chat']['id'], "❌ يجب استخدام | للفصل بين البيانات!\n\nمثال:\nفودافون كاش | محفظة إلكترونية | 01012345678 | للدفع السريع")
            return
        
        # تنظيف الحالة
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    def update_payment_method_safe(self, method_id, new_name, new_type, new_account, new_info=""):
        """تحديث آمن لوسيلة الدفع مع تحقق شامل"""
        try:
            methods = []
            updated = False
            original_method = None
            
            # قراءة الملف والبحث عن الوسيلة
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == str(method_id):
                        original_method = row.copy()
                        # تحديث البيانات
                        row['method_name'] = new_name
                        row['method_type'] = new_type
                        row['account_data'] = new_account
                        row['additional_info'] = new_info
                        updated = True
                        logger.info(f"تم العثور على وسيلة الدفع {method_id} وتحديثها")
                    methods.append(row)
            
            if not updated:
                logger.error(f"لم يتم العثور على وسيلة الدفع {method_id}")
                return False
            
            # كتابة الملف المحدث
            with open('payment_methods.csv', 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['id', 'company_id', 'method_name', 'method_type', 'account_data', 'additional_info', 'status', 'created_date']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(methods)
            
            logger.info(f"✅ تم حفظ التحديث بنجاح - الوسيلة {method_id}: {new_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث وسيلة الدفع {method_id}: {e}")
            return False
    
    def show_payment_methods_management(self, message):
        """عرض لوحة إدارة وسائل الدفع"""
        methods_text = """💳 إدارة وسائل الدفع

🏢 هذا القسم يسمح لك بإدارة وسائل الدفع لكل شركة:
• إضافة وسائل دفع جديدة
• تعديل بيانات الوسائل الموجودة  
• حذف وسائل الدفع
• تشغيل/إيقاف وسائل الدفع
• عرض جميع الوسائل المتاحة

اختر العملية المطلوبة:"""
        
        keyboard = [
            [{'text': '➕ إضافة وسيلة دفع'}, {'text': '✏️ تعديل وسيلة دفع'}],
            [{'text': '🗑️ حذف وسيلة دفع'}, {'text': '⏹️ إيقاف وسيلة دفع'}],
            [{'text': '▶️ تشغيل وسيلة دفع'}, {'text': '📊 عرض وسائل الدفع'}],
            [{'text': '↩️ العودة للوحة الأدمن'}]
        ]
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
        
        self.send_message(message['chat']['id'], methods_text, reply_keyboard)
    
    def start_disable_payment_method_wizard(self, message):
        """معالج إيقاف وسيلة دفع"""
        methods = self.get_all_payment_methods()
        active_methods = [m for m in methods if m['status'] == 'active']
        
        if not active_methods:
            self.send_message(message['chat']['id'], "❌ لا توجد وسائل دفع نشطة لإيقافها", self.admin_keyboard())
            return
        
        methods_text = "⏹️ اختر وسيلة الدفع لإيقافها:\n\n"
        keyboard = []
        
        for method in active_methods:
            company = self.get_company_by_id(method['company_id'])
            company_name = company['name'] if company else 'غير محدد'
            
            methods_text += f"🆔 {method['id']} - {method['method_name']}\n"
            methods_text += f"   🏢 {company_name}\n"
            methods_text += f"   💳 {method['method_type']}\n\n"
            
            keyboard.append([{'text': f"إيقاف {method['id']}"}])
        
        keyboard.append([{'text': '🔙 العودة'}])
        
        self.user_states[message['from']['id']] = 'selecting_method_to_disable'
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(message['chat']['id'], methods_text, reply_keyboard)
    
    def start_enable_payment_method_wizard(self, message):
        """معالج تشغيل وسيلة دفع"""
        methods = self.get_all_payment_methods()
        inactive_methods = [m for m in methods if m['status'] != 'active']
        
        if not inactive_methods:
            self.send_message(message['chat']['id'], "❌ جميع وسائل الدفع نشطة بالفعل", self.admin_keyboard())
            return
        
        methods_text = "▶️ اختر وسيلة الدفع لتشغيلها:\n\n"
        keyboard = []
        
        for method in inactive_methods:
            company = self.get_company_by_id(method['company_id'])
            company_name = company['name'] if company else 'غير محدد'
            
            methods_text += f"🆔 {method['id']} - {method['method_name']}\n"
            methods_text += f"   🏢 {company_name}\n"
            methods_text += f"   💳 {method['method_type']}\n\n"
            
            keyboard.append([{'text': f"تشغيل {method['id']}"}])
        
        keyboard.append([{'text': '🔙 العودة'}])
        
        self.user_states[message['from']['id']] = 'selecting_method_to_enable'
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(message['chat']['id'], methods_text, reply_keyboard)
    
    def handle_method_disable_selection(self, message):
        """معالجة اختيار وسيلة الدفع للإيقاف"""
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        
        if text in ['🔙 العودة', '⬅️ العودة']:
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.show_payment_methods_management(message)
            return
        
        if text.startswith('إيقاف '):
            method_id = text.replace('إيقاف ', '').strip()
            success = self.toggle_payment_method_status(method_id, 'inactive')
            
            if success:
                method = self.get_payment_method_by_id(method_id)
                if method:
                    company = self.get_company_by_id(method['company_id'])
                    company_name = company['name'] if company else 'غير محدد'
                    
                    success_msg = f"""⏹️ تم إيقاف وسيلة الدفع بنجاح!

🆔 المعرف: {method_id}
🏢 الشركة: {company_name}
📋 الاسم: {method['method_name']}
💳 النوع: {method['method_type']}
📊 الحالة: متوقفة ❌"""
                    
                    self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
                else:
                    self.send_message(message['chat']['id'], f"❌ لم يتم العثور على وسيلة الدفع {method_id}", self.admin_keyboard())
            else:
                self.send_message(message['chat']['id'], f"❌ فشل في إيقاف وسيلة الدفع {method_id}", self.admin_keyboard())
            
            if user_id in self.user_states:
                del self.user_states[user_id]
    
    def handle_method_enable_selection(self, message):
        """معالجة اختيار وسيلة الدفع للتشغيل"""
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        
        if text in ['🔙 العودة', '⬅️ العودة']:
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.show_payment_methods_management(message)
            return
        
        if text.startswith('تشغيل '):
            method_id = text.replace('تشغيل ', '').strip()
            success = self.toggle_payment_method_status(method_id, 'active')
            
            if success:
                method = self.get_payment_method_by_id(method_id)
                if method:
                    company = self.get_company_by_id(method['company_id'])
                    company_name = company['name'] if company else 'غير محدد'
                    
                    success_msg = f"""▶️ تم تشغيل وسيلة الدفع بنجاح!

🆔 المعرف: {method_id}
🏢 الشركة: {company_name}
📋 الاسم: {method['method_name']}
💳 النوع: {method['method_type']}
📊 الحالة: نشطة ✅"""
                    
                    self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
                else:
                    self.send_message(message['chat']['id'], f"❌ لم يتم العثور على وسيلة الدفع {method_id}", self.admin_keyboard())
            else:
                self.send_message(message['chat']['id'], f"❌ فشل في تشغيل وسيلة الدفع {method_id}", self.admin_keyboard())
            
            if user_id in self.user_states:
                del self.user_states[user_id]
    
    def toggle_payment_method_status(self, method_id, new_status):
        """تغيير حالة وسيلة الدفع (تشغيل/إيقاف)"""
        try:
            methods = []
            updated = False
            
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == str(method_id):
                        row['status'] = new_status
                        updated = True
                        logger.info(f"تم تغيير حالة وسيلة الدفع {method_id} إلى {new_status}")
                    methods.append(row)
            
            if updated:
                with open('payment_methods.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['id', 'company_id', 'method_name', 'method_type', 'account_data', 'additional_info', 'status', 'created_date']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(methods)
                
                return True
            
            return False
        except Exception as e:
            logger.error(f"خطأ في تغيير حالة وسيلة الدفع {method_id}: {e}")
            return False
    
    def get_all_payment_methods(self):
        """الحصول على جميع وسائل الدفع"""
        methods = []
        try:
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    methods.append(row)
        except:
            pass
        return methods
    
    def get_payment_method_by_id(self, method_id):
        """الحصول على وسيلة دفع بالمعرف"""
        try:
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == str(method_id):
                        return row
        except Exception as e:
            logger.error(f"خطأ في البحث عن وسيلة الدفع {method_id}: {e}")
        return None
    
    def show_all_payment_methods(self, message):
        """عرض جميع وسائل الدفع المتاحة"""
        methods_text = "💳 جميع وسائل الدفع:\n\n"
        
        try:
            companies = self.get_companies()
            company_names = {c['id']: c['name'] for c in companies}
            
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                methods_by_company = {}
                
                for row in reader:
                    company_id = row['company_id']
                    if company_id not in methods_by_company:
                        methods_by_company[company_id] = []
                    methods_by_company[company_id].append(row)
                
                for company_id, methods in methods_by_company.items():
                    company_name = company_names.get(company_id, f"شركة #{company_id}")
                    methods_text += f"🏢 **{company_name}**:\n"
                    
                    for method in methods:
                        status_emoji = "✅" if method['status'] == 'active' else "⏹️"
                        status_text = "نشطة" if method['status'] == 'active' else "متوقفة"
                        methods_text += f"  {status_emoji} {method['method_name']} (#{method['id']}) - {status_text}\n"
                        methods_text += f"      📋 النوع: {method['method_type']}\n"
                        methods_text += f"      💳 البيانات: {method['account_data']}\n"
                        if method['additional_info']:
                            methods_text += f"      💡 ملاحظات: {method['additional_info']}\n"
                        methods_text += "\n"
                    methods_text += "▫️▫️▫️▫️▫️▫️▫️▫️\n\n"
        except:
            methods_text += "❌ خطأ في قراءة البيانات"
        
        # إضافة أوامر النسخ السريع
        methods_text += "\n📋 **أوامر إدارة سريعة:**\n"
        methods_text += "• `اضافة_وسيلة_دفع ID_الشركة اسم_الوسيلة نوع_الوسيلة البيانات`\n"
        methods_text += "• `تعديل_وسيلة_دفع ID_الوسيلة البيانات_الجديدة`\n"
        methods_text += "• `حذف_وسيلة_دفع ID_الوسيلة`\n\n"
        
        methods_text += "💡 **مثال:**\n"
        methods_text += "`اضافة_وسيلة_دفع 1 حساب_مدى bank_account رقم:1234567890`"
        
        keyboard = [
            [{'text': '➕ إضافة وسيلة دفع'}, {'text': '✏️ تعديل وسيلة دفع'}],
            [{'text': '🔄 تحديث القائمة'}, {'text': '↩️ العودة'}]
        ]
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
        
        self.send_message(message['chat']['id'], methods_text, reply_keyboard)
    
    def start_add_payment_method(self, message):
        """بدء إضافة وسيلة دفع جديدة"""
        user_id = message['from']['id']
        
        # عرض الشركات المتاحة
        companies = self.get_companies()
        if not companies:
            self.send_message(message['chat']['id'], 
                            "❌ لا توجد شركات متاحة. يجب إضافة شركة أولاً", 
                            self.admin_keyboard())
            return
        
        companies_text = "🏢 اختر الشركة لإضافة وسيلة دفع لها:\n\n"
        keyboard = []
        
        for company in companies:
            companies_text += f"🔹 {company['name']} (#{company['id']})\n"
            keyboard.append([{'text': f"{company['name']} (#{company['id']})"}])
        
        keyboard.append([{'text': '🔙 العودة'}])
        
        self.user_states[user_id] = {
            'step': 'adding_payment_method_select_company',
            'companies': companies
        }
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(message['chat']['id'], companies_text, reply_keyboard)
    
    def handle_payment_method_selection(self, message, text):
        """معالجة اختيار وسيلة الدفع"""
        user_id = message['from']['id']
        state = self.user_states.get(user_id, {})
        
        if text in ['🔙 العودة لاختيار الشركة', '🔙 العودة', '⬅️ العودة']:
            # العودة لاختيار الشركة
            transaction_type = state.get('transaction_type')
            if transaction_type == 'deposit':
                self.create_deposit_request(message)
            else:
                self.create_withdrawal_request(message)
            return
        
        # البحث عن وسيلة الدفع المختارة
        methods = state.get('methods', [])
        selected_method = None
        
        for method in methods:
            if method['method_name'] == text:
                selected_method = method
                break
        
        if not selected_method:
            self.send_message(message['chat']['id'], "❌ اختيار غير صحيح. يرجى اختيار وسيلة دفع من القائمة")
            return
        
        # حفظ الوسيلة المختارة والانتقال للمرحلة التالية
        transaction_type = state['transaction_type']
        company_id = state['company_id']
        company = self.get_company_by_id(company_id)
        
        # عرض تفاصيل الوسيلة وطلب رقم المحفظة مع خيار النسخ
        wallet_text = f"""✅ تم اختيار وسيلة الدفع: {selected_method['method_name']}

💳 تفاصيل الوسيلة:
📋 النوع: {selected_method['method_type']}
🏢 الشركة: {company['name'] if company else 'غير محدد'}
💰 رقم الحساب/المحفظة: `{selected_method['account_data']}`
💡 معلومات إضافية: {selected_method.get('additional_info', 'لا توجد')}

📋 يمكنك نسخ رقم الحساب أعلاه بسهولة
📝 برجاء كتابة معرف حسابك/ID والتأكد أنه صحيح:

💰 برجاء كتابة رقم محفظتك التي سوف تستقبل عليها الأموال:"""
        
        self.send_message(message['chat']['id'], wallet_text)
        
        # تحديث الحالة
        if transaction_type == 'deposit':
            self.user_states[user_id] = f'deposit_wallet_{company_id}_{company["name"] if company else "unknown"}_{selected_method["id"]}'
        else:
            self.user_states[user_id] = f'withdraw_wallet_{company_id}_{company["name"] if company else "unknown"}_{selected_method["id"]}'
    
    def get_company_by_id(self, company_id):
        """الحصول على شركة بواسطة ID"""
        companies = self.get_companies()
        for company in companies:
            if company['id'] == str(company_id):
                return company
        return None
    
    def start_send_user_message(self, message):
        """بدء إرسال رسالة لعميل محدد"""
        user_id = message['from']['id']
        
        instruction_text = """📧 إرسال رسالة لعميل محدد
        
📝 أدخل رقم العميل الذي تريد إرسال رسالة إليه:

مثال: C824717

💡 تأكد من كتابة الرقم بشكل صحيح (مع الحرف C)

⬅️ /cancel للإلغاء"""
        
        self.send_message(message['chat']['id'], instruction_text)
        self.user_states[user_id] = 'sending_user_message_id'
    
    def handle_user_message_id(self, message):
        """معالجة رقم العميل لإرسال الرسالة"""
        user_id = message['from']['id']
        customer_id = message.get('text', '').strip()
        
        if customer_id == '/cancel' or customer_id.lower() == 'cancel':
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.send_message(message['chat']['id'], "✅ تم إلغاء إرسال الرسالة", self.admin_keyboard())
            return
        
        # البحث عن العميل
        user_found = None
        try:
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['customer_id'] == customer_id:
                        user_found = row
                        break
        except:
            pass
        
        if not user_found:
            self.send_message(message['chat']['id'], 
                            f"❌ لم يتم العثور على عميل برقم: {customer_id}\n\nيرجى التحقق من الرقم والمحاولة مرة أخرى:\n\n⬅️ /cancel للإلغاء")
            return
        
        # عرض معلومات العميل وطلب الرسالة
        customer_info = f"""✅ تم العثور على العميل:

👤 الاسم: {user_found['name']}
📱 الهاتف: {user_found['phone']}
🆔 رقم العميل: {user_found['customer_id']}
📅 تاريخ التسجيل: {user_found.get('registration_date', 'غير محدد')}
🚫 الحالة: {'محظور' if user_found.get('is_banned') == 'yes' else 'نشط'}

📝 الآن أدخل الرسالة التي تريد إرسالها لهذا العميل:

⬅️ /cancel للإلغاء"""
        
        self.send_message(message['chat']['id'], customer_info)
        self.user_states[user_id] = f'sending_user_message_{customer_id}'
    
    def handle_user_message_content(self, message, customer_id):
        """معالجة محتوى الرسالة وإرسالها"""
        user_id = message['from']['id']
        message_content = message.get('text', '').strip()
        
        if message_content == '/cancel' or message_content.lower() == 'cancel':
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.send_message(message['chat']['id'], "✅ تم إلغاء إرسال الرسالة", self.admin_keyboard())
            return
        
        if not message_content:
            self.send_message(message['chat']['id'], "❌ الرسالة فارغة. يرجى كتابة الرسالة:")
            return
        
        # البحث عن معرف التليجرام للعميل
        target_telegram_id = None
        customer_name = ""
        
        try:
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['customer_id'] == customer_id:
                        target_telegram_id = row['telegram_id']
                        customer_name = row['name']
                        break
        except:
            pass
        
        if not target_telegram_id:
            self.send_message(message['chat']['id'], 
                            f"❌ لم يتم العثور على معرف التليجرام للعميل {customer_id}\n\n💡 تأكد من أن العميل مسجل في النظام", 
                            self.admin_keyboard())
            if user_id in self.user_states:
                del self.user_states[user_id]
            return
        
        # إرسال الرسالة للعميل بدون لوحة مفاتيح حتى لا تؤثر على الأزرار
        admin_info = self.find_user(user_id)
        admin_name = admin_info.get('name', 'الإدارة') if admin_info else 'الإدارة'
        
        customer_message = f"""📧 رسالة من الإدارة

من: {admin_name}
التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}

━━━━━━━━━━━━━━━━━━━━

{message_content}

━━━━━━━━━━━━━━━━━━━━

💬 للرد على هذه الرسالة، استخدم قسم الشكاوى في النظام"""
        
        # محاولة إرسال الرسالة بدون لوحة مفاتيح
        try:
            response = self.send_message(int(target_telegram_id), customer_message, None)
            
            # إشعار الأدمن بنجاح الإرسال
            success_msg = f"""✅ تم إرسال الرسالة بنجاح!

📧 إلى العميل: {customer_name} ({customer_id})
📅 وقت الإرسال: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📝 محتوى الرسالة:
{message_content}"""
            
            self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
            
        except Exception as e:
            # فشل في الإرسال
            error_msg = f"""❌ فشل في إرسال الرسالة!

🎯 العميل: {customer_name} ({customer_id})
⚠️ السبب: العميل قد يكون حظر البوت أو حذف المحادثة

💡 يمكنك التواصل معه عبر:
📱 الهاتف المسجل في النظام
📧 البريد الإلكتروني (إن وجد)"""
            
            self.send_message(message['chat']['id'], error_msg, self.admin_keyboard())
        
        # حذف الحالة
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    def start_edit_payment_method(self, message):
        """بدء تعديل وسيلة دفع"""
        user_id = message['from']['id']
        
        # عرض جميع وسائل الدفع للاختيار
        methods = self.get_all_payment_methods()
        
        if not methods:
            self.send_message(message['chat']['id'], 
                            "❌ لا توجد وسائل دفع في النظام حالياً", 
                            self.admin_keyboard())
            return
        
        methods_text = "✏️ اختر وسيلة الدفع للتعديل:\n\n"
        
        keyboard_buttons = []
        for method in methods:
            company = self.get_company_by_id(method['company_id'])
            company_name = company['name'] if company else 'غير محدد'
            
            method_info = f"🆔 {method['id']} | {method['method_name']} | {company_name}"
            methods_text += f"{method_info}\n"
            keyboard_buttons.append([{'text': f"تعديل {method['id']}"}])
        
        keyboard_buttons.append([{'text': '🔙 العودة'}])
        
        keyboard = {
            'keyboard': keyboard_buttons,
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(message['chat']['id'], methods_text, keyboard)
        self.user_states[user_id] = 'selecting_method_to_edit'
    
    def start_delete_payment_method(self, message):
        """بدء حذف وسيلة دفع"""
        user_id = message['from']['id']
        
        # عرض جميع وسائل الدفع للاختيار
        methods = self.get_all_payment_methods()
        
        if not methods:
            self.send_message(message['chat']['id'], 
                            "❌ لا توجد وسائل دفع في النظام حالياً", 
                            self.admin_keyboard())
            return
        
        methods_text = "🗑️ اختر وسيلة الدفع للحذف:\n\n"
        
        keyboard_buttons = []
        for method in methods:
            company = self.get_company_by_id(method['company_id'])
            company_name = company['name'] if company else 'غير محدد'
            
            method_info = f"🆔 {method['id']} | {method['method_name']} | {company_name}"
            methods_text += f"{method_info}\n"
            keyboard_buttons.append([{'text': f"حذف {method['id']}"}])
        
        keyboard_buttons.append([{'text': '🔙 العودة'}])
        
        keyboard = {
            'keyboard': keyboard_buttons,
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.send_message(message['chat']['id'], methods_text, keyboard)
        self.user_states[user_id] = 'selecting_method_to_delete'
    
    def get_all_payment_methods(self):
        """الحصول على جميع وسائل الدفع"""
        methods = []
        try:
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('status') == 'active':
                        methods.append(row)
        except:
            pass
        return methods
    
    def delete_payment_method(self, method_id):
        """حذف وسيلة دفع"""
        try:
            methods = []
            deleted = False
            deleted_method = None
            
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] != str(method_id):
                        methods.append(row)
                    else:
                        deleted = True
                        deleted_method = row
            
            if deleted:
                # إعادة كتابة الملف بدون الوسيلة المحذوفة
                with open('payment_methods.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['id', 'company_id', 'method_name', 'method_type', 'account_data', 'additional_info', 'status', 'created_date']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(methods)
                
                return True, deleted_method
            else:
                return False, None
        except Exception as e:
            return False, None
    
    def handle_method_edit_selection(self, message):
        """معالجة اختيار وسيلة الدفع للتعديل"""
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        
        if text in ['🔙 العودة', '⬅️ العودة', '↩️ العودة']:
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.send_message(message['chat']['id'], "تم الإلغاء", self.admin_keyboard())
            return
        
        if text.startswith('تعديل '):
            method_id = text.replace('تعديل ', '').strip()
            
            # البحث عن وسيلة الدفع
            method = self.get_payment_method_by_id(method_id)
            if not method:
                self.send_message(message['chat']['id'], f"❌ لم يتم العثور على وسيلة الدفع {method_id}")
                return
            
            company = self.get_company_by_id(method['company_id'])
            company_name = company['name'] if company else 'غير محدد'
            
            # عرض تفاصيل الوسيلة وطلب البيانات الجديدة
            edit_text = f"""✏️ تعديل وسيلة الدفع:

🆔 المعرف: {method['id']}
🏢 الشركة: {company_name}
📋 الاسم: {method['method_name']}
💳 النوع: {method['method_type']}
📊 البيانات الحالية: {method['account_data']}
💡 معلومات إضافية: {method['additional_info']}

📝 أدخل البيانات الجديدة (رقم الحساب/المحفظة):

⬅️ /cancel للإلغاء"""
            
            self.send_message(message['chat']['id'], edit_text)
            self.user_states[user_id] = f'editing_method_{method_id}'
    
    def handle_method_delete_selection(self, message):
        """معالجة اختيار وسيلة الدفع للحذف"""
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        
        if text in ['🔙 العودة', '⬅️ العودة', '↩️ العودة']:
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.send_message(message['chat']['id'], "تم الإلغاء", self.admin_keyboard())
            return
        
        if text.startswith('حذف '):
            method_id = text.replace('حذف ', '').strip()
            
            # حذف وسيلة الدفع
            success, deleted_method = self.delete_payment_method(method_id)
            
            if success:
                company = self.get_company_by_id(deleted_method['company_id'])
                company_name = company['name'] if company else 'غير محدد'
                
                success_msg = f"""✅ تم حذف وسيلة الدفع بنجاح!

🗑️ المحذوفة:
🆔 المعرف: {deleted_method['id']}
🏢 الشركة: {company_name}
📋 الاسم: {deleted_method['method_name']}
💳 النوع: {deleted_method['method_type']}"""
                
                self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
            else:
                self.send_message(message['chat']['id'], f"❌ فشل في حذف وسيلة الدفع {method_id}", self.admin_keyboard())
            
            del self.user_states[user_id]
    
    def handle_method_edit_data(self, message, method_id):
        """معالجة تعديل بيانات وسيلة الدفع"""
        user_id = message['from']['id']
        new_data = message.get('text', '').strip()
        
        if new_data == '/cancel':
            del self.user_states[user_id]
            self.send_message(message['chat']['id'], "تم إلغاء التعديل", self.admin_keyboard())
            return
        
        if not new_data:
            self.send_message(message['chat']['id'], "❌ البيانات فارغة. يرجى إدخال البيانات الجديدة:")
            return
        
        # تحديث وسيلة الدفع
        success = self.update_payment_method(method_id, new_data)
        
        if success:
            method = self.get_payment_method_by_id(method_id)
            company = self.get_company_by_id(method['company_id'])
            company_name = company['name'] if company else 'غير محدد'
            
            success_msg = f"""✅ تم تحديث وسيلة الدفع بنجاح!

📝 المُحدّثة:
🆔 المعرف: {method['id']}
🏢 الشركة: {company_name}
📋 الاسم: {method['method_name']}
💳 النوع: {method['method_type']}
📊 البيانات الجديدة: {new_data}"""
            
            self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
        else:
            self.send_message(message['chat']['id'], "❌ فشل في تحديث وسيلة الدفع", self.admin_keyboard())
        
        del self.user_states[user_id]
    
    def get_payment_method_by_id(self, method_id):
        """الحصول على وسيلة دفع بواسطة المعرف"""
        try:
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == str(method_id):
                        return row
        except:
            pass
        return None
    
    def update_payment_method(self, method_id, new_account_data):
        """تحديث بيانات وسيلة الدفع - تحديث قديم"""
        try:
            methods = []
            updated = False
            
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == str(method_id):
                        row['account_data'] = new_account_data
                        updated = True
                    methods.append(row)
            
            if updated:
                with open('payment_methods.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['id', 'company_id', 'method_name', 'method_type', 'account_data', 'additional_info', 'status', 'created_date']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(methods)
                
                return True
            return False
        except Exception as e:
            return False

    def update_payment_method_complete(self, method_id, new_data):
        """تحديث شامل لوسيلة الدفع - جميع الحقول"""
        try:
            methods = []
            updated = False
            
            with open('payment_methods.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == str(method_id):
                        # تحديث جميع الحقول المطلوبة
                        if 'method_name' in new_data:
                            row['method_name'] = new_data['method_name']
                        if 'method_type' in new_data:
                            row['method_type'] = new_data['method_type']
                        if 'account_data' in new_data:
                            row['account_data'] = new_data['account_data']
                        if 'additional_info' in new_data:
                            row['additional_info'] = new_data['additional_info']
                        updated = True
                    methods.append(row)
            
            if updated:
                with open('payment_methods.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['id', 'company_id', 'method_name', 'method_type', 'account_data', 'additional_info', 'status', 'created_date']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(methods)
                
                return True
            return False
        except Exception as e:
            logger.error(f"خطأ في تحديث وسيلة الدفع {method_id}: {e}")
            return False
    
    def start_backup_scheduler(self):
        """بدء نظام النسخ الاحتياطي التلقائي كل 6 ساعات"""
        def backup_worker():
            while True:
                try:
                    # انتظار 6 ساعات (21600 ثانية)
                    time.sleep(21600)  # 6 ساعات
                    self.send_backup_to_admins()
                except Exception as e:
                    logger.error(f"خطأ في نظام النسخ الاحتياطي: {e}")
                    
        # تشغيل النظام في خيط منفصل
        backup_thread = threading.Thread(target=backup_worker, daemon=True)
        backup_thread.start()
        logger.info("تم بدء نظام النسخ الاحتياطي التلقائي (كل 6 ساعات)")
    
    def create_backup_zip(self):
        """إنشاء ملف مضغوط يحتوي على جميع بيانات النظام"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"DUX_Backup_{timestamp}.zip"
        
        try:
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # إضافة ملفات البيانات الأساسية
                files_to_backup = [
                    'users.csv',
                    'transactions.csv', 
                    'companies.csv',
                    'complaints.csv',
                    'payment_methods.csv',
                    'exchange_addresses.csv',
                    'system_settings.csv'
                ]
                
                for file in files_to_backup:
                    if os.path.exists(file):
                        zipf.write(file)
                        
                # إنشاء تقرير ملخص
                self.create_summary_report(zipf, timestamp)
                
            logger.info(f"تم إنشاء النسخة الاحتياطية: {zip_filename}")
            return zip_filename
            
        except Exception as e:
            logger.error(f"فشل في إنشاء النسخة الاحتياطية: {e}")
            return None
    
    def create_summary_report(self, zipf, timestamp):
        """إنشاء تقرير ملخص للنسخة الاحتياطية"""
        report_content = f"""تقرير النسخة الاحتياطية - {timestamp}
{'=' * 50}

📊 إحصائيات النظام:
"""
        
        try:
            # إحصائيات المستخدمين
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                users_count = len(list(csv.DictReader(f)))
                report_content += f"• عدد المستخدمين المسجلين: {users_count}\n"
                
            # إحصائيات المعاملات
            with open('transactions.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                transactions = list(reader)
                total_transactions = len(transactions)
                pending = sum(1 for t in transactions if t['status'] == 'pending')
                approved = sum(1 for t in transactions if t['status'] == 'approved')
                rejected = sum(1 for t in transactions if t['status'] == 'rejected')
                
                report_content += f"• إجمالي المعاملات: {total_transactions}\n"
                report_content += f"  - معلقة: {pending}\n"
                report_content += f"  - موافقة: {approved}\n"
                report_content += f"  - مرفوضة: {rejected}\n"
                
            # إحصائيات الشركات
            with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                companies_count = len(list(csv.DictReader(f)))
                report_content += f"• عدد الشركات: {companies_count}\n"
                
        except Exception as e:
            report_content += f"خطأ في جمع الإحصائيات: {e}\n"
            
        report_content += f"\n📅 تاريخ النسخة: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report_content += f"🤖 البوت: @depositbettingbot\n"
        
        # حفظ التقرير كملف نصي داخل الـ ZIP
        zipf.writestr('backup_report.txt', report_content.encode('utf-8'))
    
    def send_document(self, chat_id, file_path, caption=""):
        """إرسال ملف لمحادثة معينة"""
        try:
            # قراءة الملف
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # إعداد البيانات للإرسال
            url = f"{self.api_url}/sendDocument"
            
            # إنشاء multipart/form-data
            boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
            
            # بناء البيانات
            data = []
            data.append(f'--{boundary}')
            data.append('Content-Disposition: form-data; name="chat_id"')
            data.append('')
            data.append(str(chat_id))
            
            if caption:
                data.append(f'--{boundary}')
                data.append('Content-Disposition: form-data; name="caption"')
                data.append('')
                data.append(caption)
            
            data.append(f'--{boundary}')
            data.append(f'Content-Disposition: form-data; name="document"; filename="{os.path.basename(file_path)}"')
            data.append('Content-Type: application/zip')
            data.append('')
            
            # تحويل إلى bytes
            body = '\r\n'.join(data).encode('utf-8')
            body += b'\r\n' + file_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')
            
            # إنشاء الطلب
            req = urllib.request.Request(url, data=body)
            req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
            
            # إرسال الطلب
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result
                
        except Exception as e:
            logger.error(f"فشل في إرسال الملف: {e}")
            return None
    
    def get_chat_id_by_username(self, username):
        """الحصول على معرف المحادثة من اسم المستخدم"""
        try:
            # إزالة علامة @ إذا كانت موجودة
            if username.startswith('@'):
                username = username[1:]
            
            # استخدام getChat API للحصول على معلومات المحادثة
            url = f"{self.api_url}/getChat"
            data = {'chat_id': f'@{username}'}
            
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'))
            req.add_header('Content-Type', 'application/json')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if result.get('ok') and 'result' in result:
                    return result['result']['id']
                    
        except Exception as e:
            logger.error(f"فشل في الحصول على معرف {username}: {e}")
            
        return None

    def send_backup_to_admins(self):
        """إرسال النسخة الاحتياطية لجميع الإدارة"""
        logger.info("بدء إرسال النسخة الاحتياطية للإدارة...")
        
        # إنشاء النسخة الاحتياطية
        backup_file = self.create_backup_zip()
        
        if not backup_file:
            logger.error("فشل في إنشاء النسخة الاحتياطية")
            return
            
        try:
            # رسالة مرافقة للنسخة الاحتياطية
            caption = f"""📦 نسخة احتياطية تلقائية

🤖 البوت: @depositbettingbot
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⏰ النسخ التلقائي: كل 6 ساعات

📋 المحتويات:
• بيانات المستخدمين
• المعاملات المالية
• الشركات ووسائل الدفع
• الشكاوى والإعدادات
• تقرير إحصائي شامل

🔒 البيانات آمنة ومشفرة"""

            # إرسال لحساب @Aba10o0 المحدد (إذا تم تفعيله)
            backup_recipients = [
                # إضافة المعرف الرقمي هنا عندما يصبح متاحاً
                # مثال: 123456789  # @Aba10o0
            ]
            
            for recipient_id in backup_recipients:
                try:
                    result = self.send_document(recipient_id, backup_file, caption)
                    if result and result.get('ok'):
                        logger.info(f"تم إرسال النسخة الاحتياطية بنجاح للمستلم: {recipient_id}")
                    else:
                        logger.error(f"فشل في إرسال النسخة للمستلم: {recipient_id}")
                except Exception as e:
                    logger.error(f"خطأ في إرسال النسخة للمستلم {recipient_id}: {e}")
                
            # إرسال للإدارة العادية أيضاً كنسخة احتياطية
            sent_count = 0
            for admin_id in self.admin_ids:
                try:
                    if str(admin_id).isdigit():  # إرسال فقط للمعرفات الرقمية
                        result = self.send_document(admin_id, backup_file, caption)
                        if result and result.get('ok'):
                            sent_count += 1
                            logger.info(f"تم إرسال النسخة الاحتياطية للإدارة: {admin_id}")
                        else:
                            logger.error(f"فشل في إرسال النسخة للإدارة: {admin_id}")
                except Exception as e:
                    logger.error(f"خطأ في إرسال النسخة للإدارة {admin_id}: {e}")
                    
            # حذف الملف المؤقت
            try:
                os.remove(backup_file)
                logger.info(f"تم حذف الملف المؤقت: {backup_file}")
            except:
                pass
                
            logger.info(f"تم إرسال النسخة الاحتياطية لـ @{target_username} + {sent_count} إدارة إضافية")
            
        except Exception as e:
            logger.error(f"خطأ في إرسال النسخة الاحتياطية: {e}")
    
    def manual_backup_command(self, message):
        """أمر يدوي لإنشاء وإرسال نسخة احتياطية فورية"""
        if not self.is_admin(message['from']['id']):
            return
            
        self.send_message(message['chat']['id'], "🔄 جاري إنشاء النسخة الاحتياطية...")
        
        # إنشاء وإرسال النسخة
        backup_file = self.create_backup_zip()
        
        if backup_file:
            caption = f"""📦 نسخة احتياطية يدوية

🤖 البوت: @depositbettingbot  
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👨‍💼 طلب من: الإدارة

📋 جميع بيانات النظام محفوظة في هذا الملف"""

            result = self.send_document(message['chat']['id'], backup_file, caption)
            
            if result and result.get('ok'):
                self.send_message(message['chat']['id'], "✅ تم إرسال النسخة الاحتياطية بنجاح!")
            else:
                self.send_message(message['chat']['id'], "❌ فشل في إرسال النسخة الاحتياطية")
                
            # حذف الملف المؤقت
            try:
                os.remove(backup_file)
            except:
                pass
        else:
            self.send_message(message['chat']['id'], "❌ فشل في إنشاء النسخة الاحتياطية")
    
    def handle_complaint_reply_buttons(self, message, complaint_id):
        """معالجة أزرار الرد على الشكاوى"""
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        
        if text == '🔙 العودة للشكاوى':
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.show_complaints_admin(message)
            return
        
        # تحديد نوع الرد
        reply_message = ""
        if text.startswith('✅ تم الحل'):
            reply_message = "شكراً لتواصلك معنا. تم حل مشكلتك بنجاح ونعتذر عن أي إزعاج."
        elif text.startswith('🔍 قيد المراجعة'):
            reply_message = "نحن نراجع طلبك بعناية وسنرد عليك خلال 24 ساعة. شكراً لصبرك."
        elif text.startswith('📞 سنتواصل معك'):
            reply_message = "سنتواصل معك قريباً عبر الهاتف أو الرسائل. شكراً لتواصلك معنا."
        elif text.startswith('💡 رد مخصص'):
            # طلب رد مخصص
            custom_text = """💡 اكتب ردك المخصص:
            
مثال: شكراً لتواصلك، تم حل المشكلة...

⬅️ /cancel للإلغاء"""
            
            self.send_message(message['chat']['id'], custom_text)
            self.user_states[user_id] = f'writing_custom_reply_{complaint_id}'
            return
        
        # حفظ الرد وإرساله للعميل
        if reply_message:
            success = self.save_complaint_reply(complaint_id, reply_message)
            if success:
                self.send_message(message['chat']['id'], f"✅ تم إرسال الرد للعميل!\n\n📝 الرد: {reply_message}", self.admin_keyboard())
                # إرسال الرد للعميل
                self.send_complaint_reply_to_customer(complaint_id, reply_message)
            else:
                self.send_message(message['chat']['id'], "❌ فشل في حفظ الرد", self.admin_keyboard())
        
        # تنظيف الحالة
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    def save_complaint_reply(self, complaint_id, reply_message):
        """حفظ رد الشكوى"""
        try:
            complaints = []
            updated = False
            
            with open('complaints.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == complaint_id:
                        row['status'] = 'resolved'
                        row['admin_response'] = reply_message
                        updated = True
                        logger.info(f"تم العثور على الشكوى {complaint_id} وتحديثها")
                    complaints.append(row)
            
            if updated:
                with open('complaints.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    fieldnames = ['id', 'customer_id', 'subject', 'message', 'status', 'date', 'admin_response']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    # تنظيف البيانات قبل الكتابة
                    clean_complaints = []
                    for complaint in complaints:
                        clean_complaint = {}
                        for field in fieldnames:
                            clean_complaint[field] = complaint.get(field, '')
                        clean_complaints.append(clean_complaint)
                    
                    writer.writerows(clean_complaints)
                
                return True
            
            return False
        except Exception as e:
            logger.error(f"خطأ في حفظ رد الشكوى {complaint_id}: {e}")
            return False
    
    def send_complaint_reply_to_customer(self, complaint_id, reply_message):
        """إرسال رد الشكوى للعميل"""
        try:
            # البحث عن بيانات العميل
            customer_telegram_id = None
            
            with open('complaints.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] == complaint_id:
                        customer_id = row['customer_id']
                        
                        # البحث عن التليجرام ID من ملف المستخدمين
                        with open('users.csv', 'r', encoding='utf-8-sig') as users_file:
                            users_reader = csv.DictReader(users_file)
                            for user_row in users_reader:
                                if user_row['customer_id'] == customer_id:
                                    customer_telegram_id = user_row['telegram_id']
                                    break
                        break
            
            if customer_telegram_id:
                customer_message = f"""📞 رد على شكواك:

🆔 رقم الشكوى: {complaint_id}
💬 الرد: {reply_message}

شكراً لتواصلك معنا ونتطلع لخدمتك دائماً 🙏"""
                
                # إرسال الرد للعميل بدون كيبورد لعدم التداخل
                result = self.send_message_without_keyboard(customer_telegram_id, customer_message)
                if result and result.get('ok'):
                    logger.info(f"✅ تم إرسال رد الشكوى {complaint_id} للعميل {customer_telegram_id} بنجاح")
                else:
                    logger.error(f"❌ فشل في إرسال رد الشكوى {complaint_id} للعميل {customer_telegram_id}")
                    # محاولة أخرى بالطريقة العادية
                    self.send_message(customer_telegram_id, customer_message)
                
        except Exception as e:
            logger.error(f"خطأ في إرسال رد الشكوى للعميل: {e}")
    
    def send_message_without_keyboard(self, chat_id, text):
        """إرسال رسالة بدون كيبورد"""
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            # تحويل البيانات إلى JSON
            json_data = json.dumps(data).encode('utf-8')
            
            # إنشاء الطلب
            req = urllib.request.Request(url, data=json_data, headers={
                'Content-Type': 'application/json',
                'Content-Length': len(json_data)
            })
            
            # إرسال الطلب
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result
                
        except Exception as e:
            logger.error(f"Error sending message without keyboard: {e}")
            # محاولة بديلة بالطريقة العادية
            try:
                return self.send_message(chat_id, text)
            except:
                return None
    
    def show_support_data_editor(self, message):
        """عرض محرر بيانات الدعم"""
        support_text = """🛠️ محرر بيانات الدعم

يمكنك تعديل بيانات الدعم والمساعدة من هنا:

📞 رقم الدعم الحالي: {self.get_support_setting('support_phone', '+966123456789')}
💬 رابط التليجرام: {self.get_support_setting('support_telegram', '@DUX_support')}
📧 البريد الإلكتروني: {self.get_support_setting('support_email', 'support@dux.com')}
🕒 ساعات العمل: {self.get_support_setting('support_hours', '9 صباحاً - 6 مساءً')}

استخدم الأوامر التالية للتعديل:

📞 `تعديل_رقم +966987654321`
💬 `تعديل_تليجرام @DUX_support`
📧 `تعديل_بريد support@dux.com`
🕒 `تعديل_ساعات 8 صباحاً - 10 مساءً`

أو استخدم الأزرار أدناه للتعديل التفاعلي:"""
        
        keyboard = [
            [{'text': '📞 تعديل رقم الهاتف'}],
            [{'text': '💬 تعديل حساب التليجرام'}],
            [{'text': '📧 تعديل البريد الإلكتروني'}],
            [{'text': '🕒 تعديل ساعات العمل'}],
            [{'text': '🔄 تحديث بيانات الدعم'}],
            [{'text': '↩️ العودة للوحة الأدمن'}]
        ]
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
        
        self.send_message(message['chat']['id'], support_text, reply_keyboard)
    
    def start_phone_edit_wizard(self, message):
        """بدء معالج تعديل رقم الهاتف"""
        edit_text = """📞 تعديل رقم الهاتف

الرقم الحالي: +966123456789

اكتب الرقم الجديد:
مثال: +966987654321

⬅️ /cancel للإلغاء"""
        
        self.send_message(message['chat']['id'], edit_text)
        self.user_states[message['from']['id']] = 'editing_support_phone'
    
    def start_telegram_edit_wizard(self, message):
        """بدء معالج تعديل حساب التليجرام"""
        edit_text = """💬 تعديل حساب التليجرام

الحساب الحالي: @DUX_support

اكتب اسم المستخدم الجديد:
مثال: @DUX_support

⬅️ /cancel للإلغاء"""
        
        self.send_message(message['chat']['id'], edit_text)
        self.user_states[message['from']['id']] = 'editing_support_telegram'
    
    def start_email_edit_wizard(self, message):
        """بدء معالج تعديل البريد الإلكتروني"""
        edit_text = """📧 تعديل البريد الإلكتروني

البريد الحالي: support@dux.com

اكتب البريد الجديد:
مثال: support@dux.com

⬅️ /cancel للإلغاء"""
        
        self.send_message(message['chat']['id'], edit_text)
        self.user_states[message['from']['id']] = 'editing_support_email'
    
    def start_hours_edit_wizard(self, message):
        """بدء معالج تعديل ساعات العمل"""
        edit_text = """🕒 تعديل ساعات العمل

الساعات الحالية: 9 صباحاً - 6 مساءً

اكتب ساعات العمل الجديدة:
مثال: 8 صباحاً - 10 مساءً

⬅️ /cancel للإلغاء"""
        
        self.send_message(message['chat']['id'], edit_text)
        self.user_states[message['from']['id']] = 'editing_support_hours'
    
    def handle_support_data_edit(self, message, state):
        """معالجة تعديل بيانات الدعم"""
        text = message.get('text', '').strip()
        user_id = message['from']['id']
        
        if text == '/cancel':
            if user_id in self.user_states:
                del self.user_states[user_id]
            self.show_support_data_editor(message)
            return
        
        # تحديد نوع التعديل
        if state == 'editing_support_phone':
            success_msg = f"✅ تم تحديث رقم الهاتف إلى: {text}"
            self.save_support_setting('support_phone', text)
        elif state == 'editing_support_telegram':
            success_msg = f"✅ تم تحديث حساب التليجرام إلى: {text}"
            self.save_support_setting('support_telegram', text)
        elif state == 'editing_support_email':
            success_msg = f"✅ تم تحديث البريد الإلكتروني إلى: {text}"
            self.save_support_setting('support_email', text)
        elif state == 'editing_support_hours':
            success_msg = f"✅ تم تحديث ساعات العمل إلى: {text}"
            self.save_support_setting('support_hours', text)
        else:
            success_msg = "❌ خطأ في تحديث البيانات"
        
        # إرسال رسالة التأكيد والعودة لمحرر البيانات
        self.send_message(message['chat']['id'], success_msg, self.admin_keyboard())
        
        # تنظيف الحالة
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    def save_support_setting(self, key, value):
        """حفظ إعداد الدعم"""
        try:
            # قراءة الإعدادات الموجودة
            settings = []
            setting_exists = False
            
            try:
                with open('system_settings.csv', 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['setting_key'] == key:
                            row['setting_value'] = value
                            setting_exists = True
                        settings.append(row)
            except FileNotFoundError:
                pass
            
            # إضافة الإعداد الجديد إذا لم يكن موجوداً
            if not setting_exists:
                descriptions = {
                    'support_phone': 'رقم هاتف الدعم الفني',
                    'support_telegram': 'حساب التليجرام للدعم',
                    'support_email': 'بريد إلكتروني للدعم',
                    'support_hours': 'ساعات عمل خدمة الدعم'
                }
                
                settings.append({
                    'setting_key': key,
                    'setting_value': value,
                    'description': descriptions.get(key, 'إعداد الدعم')
                })
            
            # حفظ الإعدادات
            with open('system_settings.csv', 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['setting_key', 'setting_value', 'description']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(settings)
                
            logger.info(f"تم حفظ إعداد الدعم: {key} = {value}")
            
        except Exception as e:
            logger.error(f"خطأ في حفظ إعداد الدعم: {e}")
    
    def get_support_setting(self, key, default='غير محدد'):
        """قراءة إعداد الدعم"""
        try:
            with open('system_settings.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['setting_key'] == key:
                        return row['setting_value']
        except:
            pass
        return default
    
    def show_currency_selection(self, message):
        """عرض قائمة العملات للاختيار"""
        currency_text = """💱 اختيار العملة
        
اختر العملة المفضلة لديك:
(ستؤثر على جميع المعاملات والمبالغ في النظام)

💰 العملات المتاحة:"""
        
        keyboard = []
        
        # تجميع العملات في مجموعات
        arab_currencies = ['SAR', 'AED', 'EGP', 'KWD', 'QAR', 'BHD', 'OMR', 'JOD', 'LBP', 'IQD', 'SYP', 'MAD', 'TND', 'DZD', 'LYD']
        international_currencies = ['USD', 'EUR', 'TRY']
        
        # العملات العربية
        for currency in arab_currencies:
            if currency in self.currencies:
                curr_info = self.currencies[currency]
                keyboard.append([{'text': f"{curr_info['flag']} {curr_info['name']} ({curr_info['symbol']})"}])
        
        # العملات الدولية
        for currency in international_currencies:
            if currency in self.currencies:
                curr_info = self.currencies[currency]
                keyboard.append([{'text': f"{curr_info['flag']} {curr_info['name']} ({curr_info['symbol']})"}])
        
        keyboard.append([{'text': '🔙 العودة للقائمة الرئيسية'}])
        
        reply_keyboard = {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        # حفظ حالة اختيار العملة
        self.user_states[message['from']['id']] = 'selecting_currency'
        
        self.send_message(message['chat']['id'], currency_text, reply_keyboard)
    
    def handle_currency_selection(self, message, currency_text):
        """معالجة اختيار العملة"""
        try:
            user_id = message['from']['id']
            
            # البحث عن العملة المحددة
            selected_currency = None
            for code, info in self.currencies.items():
                if currency_text.startswith(info['flag']):
                    selected_currency = code
                    break
            
            if not selected_currency:
                self.send_message(message['chat']['id'], "❌ عملة غير صحيحة، يرجى المحاولة مرة أخرى", self.main_keyboard())
                return
            
            # تحديث عملة المستخدم
            users = []
            updated = False
            
            with open('users.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['telegram_id'] == str(user_id):
                        row['currency'] = selected_currency
                        updated = True
                    # إضافة العملة للمستخدمين الذين لا يملكونها
                    if 'currency' not in row or not row['currency']:
                        row['currency'] = selected_currency if row['telegram_id'] == str(user_id) else 'SAR'
                    users.append(row)
            
            if updated:
                # إضافة عمود العملة إذا لم يكن موجوداً
                fieldnames = ['telegram_id', 'name', 'phone', 'customer_id', 'language', 'date', 'is_banned', 'ban_reason', 'currency']
                
                with open('users.csv', 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(users)
                
                curr_info = self.currencies[selected_currency]
                success_msg = f"""✅ تم تغيير العملة بنجاح!
                
💰 العملة الجديدة: {curr_info['name']}
🔣 الرمز: {curr_info['symbol']}
{curr_info['flag']} البلد/المنطقة

💡 ستظهر هذه العملة في جميع معاملاتك وطلباتك"""
                
                self.send_message(message['chat']['id'], success_msg, self.main_keyboard())
                logger.info(f"تم تغيير عملة المستخدم {user_id} إلى {selected_currency}")
            else:
                self.send_message(message['chat']['id'], "❌ حدث خطأ في تحديث العملة", self.main_keyboard())
            
            # تنظيف الحالة
            if user_id in self.user_states:
                del self.user_states[user_id]
                
        except Exception as e:
            logger.error(f"خطأ في تغيير العملة: {e}")
            self.send_message(message['chat']['id'], "❌ حدث خطأ في تغيير العملة", self.main_keyboard())
    
    def get_currency_symbol(self, user_currency='SAR'):
        """جلب رمز العملة"""
        return self.currencies.get(user_currency, self.currencies['SAR'])['symbol']
    
    def format_amount_with_currency(self, amount, user_currency='SAR'):
        """تنسيق المبلغ مع العملة"""
        symbol = self.get_currency_symbol(user_currency)
        return f"{amount} {symbol}"
    
    def generate_professional_excel_report(self, message):
        """إنشاء تقرير Excel احترافي"""
        chat_id = message['chat']['id']
        
        try:
            self.send_message(chat_id, "🔄 جاري إنشاء التقرير الاحترافي...")
            
            # إنشاء ملف تقرير احترافي
            filename = self.create_professional_excel_report()
            
            if filename and os.path.exists(filename):
                # إرسال الملف
                self.send_document(chat_id, filename, "📊 تقرير Excel احترافي للنظام")
                
                success_text = f"""✅ تم إنشاء التقرير الاحترافي بنجاح!

📊 الملف يحتوي على:
• بيانات المستخدمين مع تنسيق ملون
• المعاملات مع تمييز الحالات
• الشكاوى مع تصنيف الحالة  
• الشركات وبياناتها
• وسائل الدفع المتاحة
• إحصائيات شاملة ومفصلة

🎨 التنسيق الاحترافي:
• ملف CSV منسق ومرتب
• عناوين واضحة ومميزة
• فواصل جميلة بين الأقسام
• إحصائيات مفصلة ونسب مئوية
• دعم كامل للنصوص العربية"""
                
                self.send_message(chat_id, success_text, self.admin_keyboard())
            else:
                self.send_message(chat_id, "❌ فشل في إنشاء التقرير. يرجى المحاولة مرة أخرى.", self.admin_keyboard())
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء تقرير Excel: {e}")
            self.send_message(chat_id, f"❌ خطأ في إنشاء التقرير: {str(e)}", self.admin_keyboard())
    
    def create_professional_excel_report(self):
        """إنشاء ملف تقرير احترافي منسق"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"DUX_Professional_Report_{timestamp}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                # عنوان التقرير الرئيسي
                writer.writerow(['📊 تقرير نظام DUX المالي الشامل 📊'])
                writer.writerow([f'📅 تاريخ التقرير: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
                writer.writerow(['═══════════════════════════════════════════════════════════'])
                writer.writerow([''])
                
                # قسم 1: الإحصائيات الشاملة أولاً
                writer.writerow(['📊═══ الإحصائيات الشاملة ═══'])
                stats = self.calculate_comprehensive_statistics()
                for category, data in stats.items():
                    writer.writerow([f'📋 {category}'])
                    writer.writerow(['───────────────────────────'])
                    for key, value in data.items():
                        writer.writerow([f'• {key}', value])
                    writer.writerow([''])
                
                writer.writerow(['═══════════════════════════════════════════════════════════'])
                writer.writerow([''])
                
                # قسم 2: بيانات المستخدمين
                writer.writerow(['👥═══ بيانات المستخدمين ═══'])
                if os.path.exists('users.csv'):
                    with open('users.csv', 'r', encoding='utf-8-sig') as uf:
                        user_reader = csv.reader(uf)
                        for row in user_reader:
                            writer.writerow(row)
                else:
                    writer.writerow(['لا توجد بيانات مستخدمين'])
                writer.writerow([''])
                
                # قسم 3: بيانات المعاملات
                writer.writerow(['💳═══ بيانات المعاملات ═══'])
                if os.path.exists('transactions.csv'):
                    with open('transactions.csv', 'r', encoding='utf-8-sig') as tf:
                        trans_reader = csv.reader(tf)
                        for row in trans_reader:
                            writer.writerow(row)
                else:
                    writer.writerow(['لا توجد بيانات معاملات'])
                writer.writerow([''])
                
                # قسم 4: بيانات الشكاوى
                writer.writerow(['📨═══ بيانات الشكاوى ═══'])
                if os.path.exists('complaints.csv'):
                    with open('complaints.csv', 'r', encoding='utf-8-sig') as cf:
                        comp_reader = csv.reader(cf)
                        for row in comp_reader:
                            writer.writerow(row)
                else:
                    writer.writerow(['لا توجد بيانات شكاوى'])
                writer.writerow([''])
                
                # قسم 5: بيانات الشركات
                writer.writerow(['🏢═══ بيانات الشركات ═══'])
                if os.path.exists('companies.csv'):
                    with open('companies.csv', 'r', encoding='utf-8-sig') as compf:
                        comp_reader = csv.reader(compf)
                        for row in comp_reader:
                            writer.writerow(row)
                else:
                    writer.writerow(['لا توجد بيانات شركات'])
                writer.writerow([''])
                
                # قسم 6: وسائل الدفع
                writer.writerow(['💳═══ وسائل الدفع ═══'])
                if os.path.exists('payment_methods.csv'):
                    with open('payment_methods.csv', 'r', encoding='utf-8-sig') as pmf:
                        pm_reader = csv.reader(pmf)
                        for row in pm_reader:
                            writer.writerow(row)
                else:
                    writer.writerow(['لا توجد وسائل دفع'])
                writer.writerow([''])
                
                # خاتمة التقرير
                writer.writerow(['═══════════════════════════════════════════════════════════'])
                writer.writerow([f'📈 تم إنشاء التقرير بواسطة نظام DUX - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
                writer.writerow(['🔒 هذا التقرير سري ومخصص للإدارة فقط'])
            
            return filename
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء التقرير: {e}")
            return None
    
    def calculate_comprehensive_statistics(self):
        """حساب إحصائيات شاملة للنظام"""
        stats = {}
        
        try:
            # إحصائيات المستخدمين
            if os.path.exists('users.csv'):
                with open('users.csv', 'r', encoding='utf-8-sig') as f:
                    users = list(csv.DictReader(f))
                    
                    # تحليل العملات واللغات
                    currency_stats = {}
                    language_stats = {}
                    for user in users:
                        currency = user.get('currency', 'SAR')
                        language = user.get('language', 'ar')
                        currency_stats[currency] = currency_stats.get(currency, 0) + 1
                        language_stats[language] = language_stats.get(language, 0) + 1
                    
                    user_stats = {
                        'إجمالي المستخدمين': len(users),
                        'المستخدمين النشطين': len([u for u in users if u.get('is_banned', 'no').lower() != 'yes']),
                        'المستخدمين المحظورين': len([u for u in users if u.get('is_banned', 'no').lower() == 'yes']),
                        'نسبة المستخدمين النشطين': f"{(len([u for u in users if u.get('is_banned', 'no').lower() != 'yes'])/len(users)*100):.1f}%" if users else "0%"
                    }
                    
                    # إضافة إحصائيات العملات
                    for currency, count in currency_stats.items():
                        currency_name = self.currencies.get(currency, {}).get('name', currency)
                        user_stats[f'مستخدمي {currency_name}'] = f"{count} ({(count/len(users)*100):.1f}%)"
                    
                    stats['إحصائيات المستخدمين'] = user_stats
            
            # إحصائيات المعاملات
            if os.path.exists('transactions.csv'):
                with open('transactions.csv', 'r', encoding='utf-8-sig') as f:
                    transactions = list(csv.DictReader(f))
                    
                    approved = [t for t in transactions if t.get('status') == 'approved']
                    rejected = [t for t in transactions if t.get('status') == 'rejected']
                    pending = [t for t in transactions if t.get('status') == 'pending']
                    deposits = [t for t in transactions if t.get('type') == 'deposit']
                    withdrawals = [t for t in transactions if t.get('type') == 'withdraw']
                    
                    def safe_float(value):
                        try:
                            return float(str(value).replace(',', '')) if value else 0.0
                        except:
                            return 0.0
                    
                    total_approved_amount = sum(safe_float(t.get('amount', 0)) for t in approved)
                    total_deposit_amount = sum(safe_float(t.get('amount', 0)) for t in deposits if t.get('status') == 'approved')
                    total_withdrawal_amount = sum(safe_float(t.get('amount', 0)) for t in withdrawals if t.get('status') == 'approved')
                    
                    transaction_stats = {
                        'إجمالي المعاملات': len(transactions),
                        'المعاملات المُوافقة': f"{len(approved)} ({(len(approved)/len(transactions)*100):.1f}%)" if transactions else "0",
                        'المعاملات المرفوضة': f"{len(rejected)} ({(len(rejected)/len(transactions)*100):.1f}%)" if transactions else "0",
                        'المعاملات المعلقة': f"{len(pending)} ({(len(pending)/len(transactions)*100):.1f}%)" if transactions else "0",
                        'طلبات الإيداع': f"{len(deposits)} ({(len(deposits)/len(transactions)*100):.1f}%)" if transactions else "0",
                        'طلبات السحب': f"{len(withdrawals)} ({(len(withdrawals)/len(transactions)*100):.1f}%)" if transactions else "0",
                        'معدل الموافقة': f"{(len(approved)/len(transactions)*100):.1f}%" if transactions else "0%",
                        'إجمالي المبالغ المُوافقة': f"{total_approved_amount:,.2f}",
                        'إجمالي الإيداعات المُوافقة': f"{total_deposit_amount:,.2f}",
                        'إجمالي السحوبات المُوافقة': f"{total_withdrawal_amount:,.2f}",
                        'صافي الحركة': f"{total_deposit_amount - total_withdrawal_amount:,.2f}",
                        'متوسط قيمة المعاملة': f"{(total_approved_amount/len(approved)):,.2f}" if approved else "0"
                    }
                    
                    stats['إحصائيات المعاملات'] = transaction_stats
            
            # إحصائيات الشكاوى والشركات
            if os.path.exists('complaints.csv'):
                with open('complaints.csv', 'r', encoding='utf-8-sig') as f:
                    complaints = list(csv.DictReader(f))
                    resolved = [c for c in complaints if c.get('status') == 'resolved']
                    pending_complaints = [c for c in complaints if c.get('status') == 'pending']
                    
                    stats['إحصائيات الشكاوى'] = {
                        'إجمالي الشكاوى': len(complaints),
                        'الشكاوى المحلولة': f"{len(resolved)} ({(len(resolved)/len(complaints)*100):.1f}%)" if complaints else "0",
                        'الشكاوى المعلقة': f"{len(pending_complaints)} ({(len(pending_complaints)/len(complaints)*100):.1f}%)" if complaints else "0",
                        'معدل الحل': f"{(len(resolved)/len(complaints)*100):.1f}%" if complaints else "0%"
                    }
            
            if os.path.exists('companies.csv'):
                with open('companies.csv', 'r', encoding='utf-8-sig') as f:
                    companies = list(csv.DictReader(f))
                    active = [c for c in companies if c.get('is_active', '').lower() == 'active']
                    
                    stats['إحصائيات الشركات'] = {
                        'إجمالي الشركات': len(companies),
                        'الشركات النشطة': f"{len(active)} ({(len(active)/len(companies)*100):.1f}%)" if companies else "0",
                        'الشركات غير النشطة': f"{len(companies) - len(active)}"
                    }
        
        except Exception as e:
            logger.error(f"خطأ في حساب الإحصائيات: {e}")
        
        return stats

if __name__ == "__main__":
    # جلب التوكن
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN غير موجود في متغيرات البيئة")
        exit(1)
    
    # تشغيل البوت
    bot = ComprehensiveDUXBot(bot_token)
    bot.run()