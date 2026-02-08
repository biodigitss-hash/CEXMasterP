@echo off
REM Start Backend Server for Crypto Arbitrage Bot
REM Uses MySQL on port 3307

echo ============================================
echo Starting Backend Server (MySQL port 3307)
echo ============================================
echo.

cd backend

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Virtual environment activated
) else (
    echo WARNING: Virtual environment not found
    echo Run setup-windows.bat first
    pause
    exit /b 1
)

REM Check if .env exists
if not exist .env (
    echo WARNING: .env file not found
    echo Creating default .env file...
    (
        echo # Database Configuration - MySQL on port 3307
        echo MYSQL_HOST=localhost
        echo MYSQL_PORT=3307
        echo MYSQL_USER=root
        echo MYSQL_PASSWORD=your_mysql_password_here
        echo MYSQL_DATABASE=crypto_arbitrage
        echo.
        echo # App Configuration
        echo CORS_ORIGINS="*"
        echo ENCRYPTION_KEY="GENERATE_YOUR_KEY_HERE"
        echo TELEGRAM_BOT_TOKEN=""
    ) > .env
    echo.
    echo IMPORTANT: Edit .env file with your MySQL password and encryption key!
    echo See MYSQL_WINDOWS_SETUP.md for details
    echo.
)

echo Starting server on http://localhost:8001
echo MySQL configured on port 3307
echo Press Ctrl+C to stop
echo.

python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload

pause
