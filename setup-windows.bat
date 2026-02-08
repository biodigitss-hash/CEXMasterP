@echo off
REM Crypto Arbitrage Bot - Windows Setup Script
REM This script helps you set up the bot on Windows with MySQL

echo ============================================
echo Crypto Arbitrage Bot - Windows Setup
echo ============================================
echo.

REM Check Python
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
echo SUCCESS: Python is installed
echo.

REM Check MySQL
echo [2/5] Checking MySQL service...
sc query MySQL80 >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: MySQL service not found
    echo Please install MySQL from https://dev.mysql.com/downloads/installer/
    echo See MYSQL_WINDOWS_SETUP.md for detailed installation guide
    echo.
    echo Press any key to continue anyway or Ctrl+C to exit...
    pause >nul
) else (
    echo SUCCESS: MySQL service found
)
echo.

REM Check Node.js
echo [3/5] Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed
    echo Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)
echo SUCCESS: Node.js is installed
echo.

REM Install backend dependencies
echo [4/5] Installing backend dependencies...
cd backend
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing Python packages (including MySQL drivers)...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)
echo SUCCESS: Backend dependencies installed (including aiomysql, PyMySQL)
cd ..
echo.

REM Install frontend dependencies
echo [5/5] Installing frontend dependencies...
cd frontend

REM Check if yarn is installed, if not use npm
yarn --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Yarn not found, installing with npm...
    npm install -g yarn
)

echo Installing Node packages...
yarn install
if %errorlevel% neq 0 (
    echo ERROR: Failed to install frontend dependencies
    pause
    exit /b 1
)
echo SUCCESS: Frontend dependencies installed
cd ..
echo.

echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo IMPORTANT: Database Configuration
echo ================================
echo 1. Install MySQL (if not already installed)
echo    Download: https://dev.mysql.com/downloads/installer/
echo.
echo 2. Create database:
echo    mysql -u root -p
echo    CREATE DATABASE crypto_arbitrage;
echo    source database_schema.sql;
echo.
echo 3. Configure backend\.env file:
echo    - Set MYSQL_PASSWORD to your MySQL root password
echo    - Generate ENCRYPTION_KEY with:
echo      python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
echo.
echo 4. Run the application:
echo    - Double-click start-backend.bat
echo    - Double-click start-frontend.bat (in new window)
echo.
echo For detailed instructions, see:
echo - MYSQL_WINDOWS_SETUP.md (MySQL setup guide)
echo - WINDOWS_SETUP_GUIDE.md (General Windows setup)
echo.
pause
