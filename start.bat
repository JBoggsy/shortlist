@echo off
REM Job Application Helper - Unified Startup Script for Windows
REM This script checks dependencies, starts the backend and frontend, and opens your browser

setlocal enabledelayedexpansion

echo.
echo ╔═══════════════════════════════════════╗
echo ║   Job Application Helper Startup     ║
echo ╚═══════════════════════════════════════╝
echo.

echo → Checking dependencies...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python 3 is not installed
    echo   Please install Python 3.12 or higher from:
    echo   https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python %PYTHON_VERSION%

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Node.js is not installed
    echo   Please install Node.js 18 or higher from:
    echo   https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=1" %%i in ('node --version') do set NODE_VERSION=%%i
echo ✓ Node.js %NODE_VERSION%

REM Check uv
uv --version >nul 2>&1
if errorlevel 1 (
    echo ✗ uv is not installed
    echo   Installing uv...
    pip install uv
    if errorlevel 1 (
        echo   Failed to install uv. Please install manually:
        echo   pip install uv
        pause
        exit /b 1
    )
)

echo ✓ uv
echo.

REM Check if dependencies are installed
echo → Checking if dependencies are installed...
echo.

if not exist ".venv" (
    echo   Installing Python dependencies ^(this may take a minute^)...
    uv sync
    if errorlevel 1 (
        echo   Failed to install Python dependencies
        pause
        exit /b 1
    )
    echo   ✓ Python dependencies installed
) else (
    echo   ✓ Python dependencies already installed
)

if not exist "frontend\node_modules" (
    echo   Installing Node dependencies ^(this may take a minute^)...
    cd frontend
    call npm install
    cd ..
    if errorlevel 1 (
        echo   Failed to install Node dependencies
        pause
        exit /b 1
    )
    echo   ✓ Node dependencies installed
) else (
    echo   ✓ Node dependencies already installed
)

echo.

REM Check configuration
if not exist "config.json" (
    if "%LLM_API_KEY%"=="" (
        echo ⚠ No configuration found
        echo   The app will start, but you'll need to configure your LLM API key
        echo   in the Settings panel ^(gear icon in the top right^).
        echo.
    )
)

echo → Starting Job Application Helper...
echo.

REM Start backend in a new window
echo   Starting backend server...
start "Job App Helper - Backend" cmd /c "uv run python main.py"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in a new window
echo   Starting frontend dev server...
start "Job App Helper - Frontend" cmd /c "cd frontend && npm run dev"

REM Wait for frontend to start
timeout /t 3 /nobreak >nul

echo.
echo ╔═══════════════════════════════════════╗
echo ║          🚀 App is running!          ║
echo ╚═══════════════════════════════════════╝
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:5000
echo.
echo   Close the backend and frontend windows to stop the app
echo.

REM Open browser
timeout /t 2 /nobreak >nul
start http://localhost:3000

echo Press any key to exit this window...
pause >nul
