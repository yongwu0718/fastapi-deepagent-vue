@echo off
title Index RAG Starting...
cd /d "%~dp0"

echo ============================================
echo          Index RAG - Desktop Shell
echo ============================================
echo.

echo [1/3] Checking Python environment...
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run: uv sync
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat >nul 2>nul

echo [2/3] Stopping old processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>nul

echo [3/3] Checking Electron dependencies...
if not exist "desktop\node_modules\electron" (
    echo First run, installing Electron via mirror...
    set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
    cd desktop
    call npm install
    if errorlevel 1 (
        cd ..
        echo [ERROR] Electron install failed
        pause
        exit /b 1
    )
    cd ..
)

echo [4/4] Launching desktop app...
echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo.
echo ============================================

cd desktop
call npm start

if errorlevel 1 (
    cd ..
    echo.
    echo [ERROR] Desktop app failed to start
    pause
)
