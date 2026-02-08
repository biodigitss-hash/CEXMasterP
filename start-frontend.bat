@echo off
REM Start Frontend for Crypto Arbitrage Bot

echo ============================================
echo Starting Frontend...
echo ============================================
echo.

cd frontend

REM Check if node_modules exists
if not exist node_modules (
    echo ERROR: Dependencies not installed
    echo Run setup-windows.bat first
    pause
    exit /b 1
)

REM Check if .env exists
if not exist .env (
    echo WARNING: .env file not found
    echo Creating default .env file...
    echo REACT_APP_BACKEND_URL=http://localhost:8001 > .env
)

echo Starting frontend on http://localhost:3000
echo Browser will open automatically
echo Press Ctrl+C to stop
echo.

yarn start

pause
