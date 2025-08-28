# Telegram Finance Bot / بوت الخدمات المالية

## نظرة عامة / Overview

**العربية:**
بوت تليجرام شامل للخدمات المالية يدعم إدارة الودائع والسحوبات، نظام الشكاوى، لوحة تحكم المدير، إدارة الشركات وطرق الدفع، النشرات والإعلانات، والتقارير والنسخ الاحتياطية.

**English:**
A comprehensive Telegram financial services bot supporting deposits/withdrawals management, complaints system, admin panel, companies and payment methods management, broadcasts and announcements, reports and backups.

## المتطلبات / Requirements

- Python 3.10+
- Telegram Bot Token (من BotFather / from BotFather)
- SQLite (افتراضي / default) أو PostgreSQL (اختياري / optional)

## التثبيت السريع / Quick Installation

### Windows

1. قم بتحميل وفك ضغط الملفات / Download and extract files
2. افتح موجه الأوامر في مجلد البوت / Open command prompt in bot folder
3. انقر نقراً مزدوجاً على `run_windows.bat` / Double-click `run_windows.bat`

### Linux/macOS

```bash
# قم بفك ضغط الملفات أولاً / Extract files first
cd tg_finance_bot/

# اجعل الملف قابلاً للتنفيذ / Make script executable
chmod +x run_linux.sh

# قم بتشغيل البوت / Run the bot
./run_linux.sh
```

## الإعداد اليدوي / Manual Setup

### 1. إنشاء البيئة الافتراضية / Create Virtual Environment

```bash
# إنشاء البيئة الافتراضية / Create virtual environment
python3 -m venv venv

# تفعيل البيئة الافتراضية / Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 2. تثبيت المتطلبات / Install Requirements

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. إعداد ملف البيئة / Environment Setup

```bash
# انسخ ملف المثال / Copy example file
cp .env.example .env

# قم بتحرير الملف / Edit the file
nano .env  # أو أي محرر نصوص / or any text editor
```

**إعدادات مطلوبة / Required Settings:**
```bash
BOT_TOKEN=your_bot_token_here
ADMINS=123456789,987654321
```

### 4. تشغيل البوت / Run the Bot

```bash
python run.py
```

## الميزات / Features

### للمستخدمين / For Users
- ✅ التسجيل التلقائي عبر /start / Auto registration via /start
- 👤 إدارة الحساب الشخصي / Personal account management
- 💰 طلبات الإيداع والسحب / Deposit and withdrawal requests
- 🗣️ تغيير اللغة (عربي/إنجليزي) / Language change (Arabic/English)
- 📢 نظام الشكاوى / Complaints system
- 🆔 رمز عميل فريد / Unique customer code
- 🔄 إعادة تعيين الحالة / State reset functionality

### للمديرين / For Admins
- 🔐 لوحة تحكم شاملة / Comprehensive admin panel
- 📋 إدارة الطلبات المعلقة / Pending requests management
- 📢 إدارة الشكاوى / Complaints management
- 🏢 إدارة الشركات وطرق الدفع / Companies and payment methods management
- 📣 نظام الإعلانات والبث / Announcements and broadcast system
- 📊 تقارير CSV/Excel / CSV/Excel reports
- 💾 نظام النسخ الاحتياطية / Backup system
- ⚡ بث محدود السرعة / Rate-limited broadcasting

## الأوامر / Commands

### أوامر المستخدمين / User Commands
- `/start` - بدء البوت والتسجيل / Start bot and register
- أزرار القائمة / Menu buttons:
  - `حسابي / My Account` - معلومات الحساب / Account information
  - `إيداع / Deposit` - طلب إيداع / Deposit request
  - `سحب / Withdraw` - طلب سحب / Withdrawal request
  - `تغيير اللغة / Change Language` - تغيير اللغة / Change language
  - `الدعم / Support` - معلومات الدعم / Support information
  - `إعادة التعيين / Reset` - إعادة تعيين الحالة / Reset state

### أوامر المديرين / Admin Commands
- `/admin` - لوحة التحكم / Admin panel
- `/add_company` - إضافة شركة / Add company
- `/list_companies` - عرض الشركات / List companies
- `/add_payment_method` - إضافة طريقة دفع / Add payment method
- `/broadcast` - بث رسالة (رد على رسالة) / Broadcast message (reply to message)
- `/announce` - إنشاء إعلان / Create announcement

## هيكل المشروع / Project Structure

```
tg_finance_bot/
├── README.md                 # هذا الملف / This file
├── requirements.txt          # متطلبات Python / Python requirements
├── .env.example             # مثال إعدادات البيئة / Environment settings example
├── run_windows.bat          # سكريبت تشغيل Windows / Windows run script
├── run_linux.sh             # سكريبت تشغيل Linux/macOS / Linux/macOS run script
├── main.py                  # تطبيق Aiogram الرئيسي / Main Aiogram app
├── run.py                   # سكريبت بدء التشغيل / Startup script
├── config.py                # إعدادات التطبيق / App configuration
├── db.py                    # إعداد قاعدة البيانات / Database setup
├── models.py                # نماذج SQLAlchemy / SQLAlchemy models
├── middleware.py            # وسطاء Aiogram / Aiogram middleware
├── services/
│   ├── broadcast_service.py # خدمة البث / Broadcast service
│   ├── reports.py           # خدمة التقارير / Reports service
│   └── backup.py            # خدمة النسخ الاحتياطية / Backup service
├── utils/
│   ├── i18n.py              # نظام الترجمة / Translation system
│   └── keyboards.py         # لوحات المفاتيح / Keyboards
├── handlers/
│   ├── __init__.py          # تجميع المعالجات / Handlers aggregation
│   ├── start.py             # معالج البداية والتسجيل / Start and registration handler
│   ├── user_settings.py     # معالج إعدادات المستخدم / User settings handler
│   ├── finance.py           # معالج العمليات المالية / Finance operations handler
│   ├── complaints.py        # معالج الشكاوى / Complaints handler
│   ├── admin.py             # معالج لوحة المدير / Admin panel handler
│   ├── companies.py         # معالج إدارة الشركات / Companies management handler
│   ├── broadcast.py         # معالج البث / Broadcast handler
│   ├── announcements.py     # معالج الإعلانات / Announcements handler
│   ├── reports.py           # معالج التقارير / Reports handler
│   └── backups.py           # معالج النسخ الاحتياطية / Backups handler
├── translations/
│   ├── ar.json              # ترجمات عربية / Arabic translations
│   └── en.json              # ترجمات إنجليزية / English translations
└── data/
    ├── .gitkeep             # مجلد البيانات / Data folder
    ├── db.sqlite3           # قاعدة البيانات (يتم إنشاؤها تلقائياً) / Database (auto-created)
    ├── reports/             # مجلد التقارير / Reports folder
    └── backups/             # مجلد النسخ الاحتياطية / Backups folder
```

## قاعدة البيانات / Database

### الجداول / Tables
- **users** - بيانات المستخدمين / User data
- **companies** - الشركات / Companies
- **payment_methods** - طرق الدفع / Payment methods
- **requests** - طلبات الإيداع والسحب / Deposit/withdrawal requests
- **complaints** - الشكاوى / Complaints
- **ads** - الإعلانات / Announcements

### التكوين / Configuration
- **افتراضي / Default**: SQLite في `data/db.sqlite3`
- **PostgreSQL**: قم بتعديل `DATABASE_URL` في `.env`

## الأمان / Security

- 🔐 التحقق من صلاحيات المدير / Admin authorization verification
- 🛡️ حماية من SQL Injection عبر SQLAlchemy / SQL Injection protection via SQLAlchemy
- ⚡ محدود السرعة للبث / Rate limiting for broadcasts
- 🔄 معالجة الأخطاء الشاملة / Comprehensive error handling

## التخصيص / Customization

### إضافة لغات جديدة / Adding New Languages
1. أنشئ ملف `translations/xx.json` / Create `translations/xx.json` file
2. أضف المفاتيح المترجمة / Add translated keys
3. قم بتحديث الأكواد حسب الحاجة / Update code as needed

### إضافة ميزات جديدة / Adding New Features
1. أنشئ معالج جديد في `handlers/` / Create new handler in `handlers/`
2. أضفه إلى `handlers/__init__.py` / Add it to `handlers/__init__.py`
3. أضف ترجمات في `translations/` / Add translations in `translations/`

## استكشاف الأخطاء / Troubleshooting

### مشاكل شائعة / Common Issues

**"BOT_TOKEN environment variable is required"**
- تأكد من إعداد `BOT_TOKEN` في ملف `.env` / Ensure `BOT_TOKEN` is set in `.env` file

**"Database initialization failed"**
- تحقق من صلاحيات الكتابة في مجلد `data/` / Check write permissions for `data/` folder
- تأكد من وجود مجلد `data/` / Ensure `data/` folder exists

**"Module not found" errors**
- قم بتفعيل البيئة الافتراضية / Activate virtual environment
- قم بإعادة تثبيت المتطلبات / Reinstall requirements: `pip install -r requirements.txt`

**البوت لا يجيب / Bot not responding**
- تحقق من صحة Bot Token / Verify Bot Token is correct
- تأكد من عدم تشغيل البوت في مكان آخر / Ensure bot is not running elsewhere
- تحقق من سجلات الأخطاء في `bot.log` / Check error logs in `bot.log`

### السجلات / Logs
- يتم حفظ السجلات في `bot.log` / Logs are saved to `bot.log`
- مستوى السجل افتراضياً INFO / Default log level is INFO
- قم بتغيير `LOG_LEVEL` في `.env` للحصول على مزيد من التفاصيل / Change `LOG_LEVEL` in `.env` for more detail

## الدعم / Support

للحصول على الدعم والتقارير حول الأخطاء:
For support and bug reports:

- تحقق من سجل الأخطاء `bot.log` أولاً / Check `bot.log` error log first
- تأكد من اتباع تعليمات التثبيت / Ensure installation instructions were followed
- قم بإعادة إنشاء المشكلة مع الحد الأدنى من الإعدادات / Try to reproduce issue with minimal setup

## الترخيص / License

هذا المشروع مفتوح المصدر. يمكنك استخدامه وتعديله بحرية.
This project is open source. You can use and modify it freely.

---

**ملاحظة / Note**: تأكد من اتباع قوانين وأنظمة المنطقة عند استخدام هذا البوت للخدمات المالية.
Make sure to comply with local laws and regulations when using this bot for financial services.