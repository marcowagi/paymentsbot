@echo off
echo ========================================
echo LangSense Telegram Bot - Windows Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python is installed ✓
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created ✓
) else (
    echo Virtual environment already exists ✓
)

echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo Virtual environment activated ✓
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo Pip upgraded ✓
echo.

REM Install required packages
echo Installing required packages...
pip install aiogram sqlalchemy aiosqlite asyncpg python-dotenv aiohttp pydantic psutil requests aiofiles pillow cryptography apscheduler babel
if errorlevel 1 (
    echo ERROR: Failed to install packages
    pause
    exit /b 1
)

echo Packages installed successfully ✓
echo.

REM Check if .env file exists
if not exist ".env" (
    echo WARNING: .env file not found!
    echo.
    echo Please create a .env file with the following content:
    echo BOT_TOKEN=your_bot_token_here
    echo ADMIN_USER_IDS=your_telegram_user_id_here
    echo DATABASE_URL=sqlite+aiosqlite:///./langsense.db
    echo.
    echo You can copy .env.example to .env and modify the values.
    echo.
    pause
) else (
    echo .env file found ✓
)

echo.

REM Create translations directory if it doesn't exist
if not exist "translations" (
    mkdir translations
    echo Created translations directory ✓
)

REM Create handlers directory if it doesn't exist
if not exist "handlers" (
    mkdir handlers
    echo Created handlers directory ✓
)

REM Create services directory if it doesn't exist
if not exist "services" (
    mkdir services
    echo Created services directory ✓
)

REM Create utils directory if it doesn't exist
if not exist "utils" (
    mkdir utils
    echo Created utils directory ✓
)

echo.
echo ========================================
echo Setup completed successfully! 🎉
echo ========================================
echo.

REM Start the bot
echo Starting LangSense Bot...
echo Press Ctrl+C to stop the bot
echo.

python main.py

echo.
echo Bot stopped.
pause
