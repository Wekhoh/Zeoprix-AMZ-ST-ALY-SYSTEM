@echo off
title AMZ Search Term Analyzer

echo ========================================
echo   AMZ Search Term Analyzer - Launcher
echo ========================================
echo.

:: Switch to script directory
cd /d "%~dp0"

:: Check Python
echo [1/3] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python found

:: Check dependencies
echo [2/3] Checking dependencies...
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)
echo [OK] Dependencies ready

:: Check .env file
echo [3/3] Checking config...
if not exist ".env" (
    echo [INFO] Creating .env file...
    copy .env.example .env >nul
    echo [WARNING] Please edit .env and set GEMINI_API_KEY
    notepad .env
)
echo [OK] Config ready

:: Set Python path
set PYTHONPATH=%~dp0

:: Start application
echo.
echo Starting application...
echo Browser will open at: http://localhost:8501
echo Press Ctrl+C to stop
echo.

streamlit run src/app.py

pause
