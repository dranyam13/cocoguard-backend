@echo off
setlocal enabledelayedexpansion

REM CocoGuard Backend Startup Script for Windows

echo.
echo ================================================
echo     CocoGuard Backend - Startup Script
echo ================================================
echo.

REM Get the local IP address
set "LOCAL_IP="
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set "IP_TEMP=%%a"
    REM Remove leading space
    set "IP_TEMP=!IP_TEMP:~1!"
    REM Only take the first valid IP (skip 127.x.x.x)
    if "!LOCAL_IP!"=="" (
        echo !IP_TEMP! | findstr /r "^127\." >nul
        if errorlevel 1 (
            set "LOCAL_IP=!IP_TEMP!"
        )
    )
)

if "!LOCAL_IP!"=="" (
    echo [!] Could not detect IP address, using localhost
    set "LOCAL_IP=localhost"
)

echo [+] Detected IP Address: !LOCAL_IP!

REM Check if virtual environment exists
if not exist "venv" (
    echo [!] Virtual environment not found!
    echo [*] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        exit /b 1
    )
    echo [+] Virtual environment created
)

REM Activate virtual environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    exit /b 1
)

REM Check if requirements are installed
echo [*] Checking dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [*] Installing dependencies...
    pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        exit /b 1
    )
    echo [+] Dependencies installed
)

REM Create .env if not exists
if not exist ".env" (
    echo [*] Creating .env file from template...
    copy .env.example .env
    echo [+] Created .env file - please review and update if needed
)

REM Create uploads directory
if not exist "uploads" (
    echo [*] Creating uploads directory...
    mkdir uploads
    echo [+] Uploads directory created
)

REM Kill any process using port 8000
echo [*] Checking if port 8000 is in use...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo [!] Port 8000 is in use by PID %%a - terminating...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

REM Start the server
echo.
echo [+] Starting CocoGuard Backend API...
echo [+] API will be available at:
echo     - http://localhost:8000 (local)
echo     - http://!LOCAL_IP!:8000 (network)
echo.
echo [+] API Documentation at: http://!LOCAL_IP!:8000/docs
echo.
echo [*] Press Ctrl+C to stop the server
echo.

REM Open browser after a short delay (runs in background)


set "OPEN_URL=http://!LOCAL_IP!/cocoguard_web/"
echo [*] Will open browser at: !OPEN_URL!

REM Create a temp script to open the browser
echo @echo off > "%TEMP%\open_cocoguard.bat"
echo timeout /t 3 /nobreak ^>nul >> "%TEMP%\open_cocoguard.bat"
echo start "" "!OPEN_URL!" >> "%TEMP%\open_cocoguard.bat"
start /b "" cmd /c "%TEMP%\open_cocoguard.bat"

REM Start the uvicorn server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

endlocal
pause
