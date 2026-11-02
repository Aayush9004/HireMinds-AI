@echo off
setlocal enabledelayedexpansion
title HireMinds AI Launcher

cd /d "%~dp0"

if exist "%~dp0HireMinds-AI_sprint_1\backend" (
    set "PROJECT_DIR=%~dp0HireMinds-AI_sprint_1"
) else if exist "%~dp0backend" (
    set "PROJECT_DIR=%~dp0"
) else (
    echo [ERROR] Could not locate backend directory.
    pause
    exit /b 1
)

echo ===================================================
echo             HireMinds AI Launcher
echo ===================================================
echo Base directory: %PROJECT_DIR%
echo.

echo [1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "HireMinds Backend" cmd /k "cd /d "%PROJECT_DIR%\backend" && (if exist venv\Scripts\activate.bat (call venv\Scripts\activate.bat) else (echo [INFO] Using global python)) && set PYTHONPATH=%PROJECT_DIR%\backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo [2/2] Starting React Frontend on http://localhost:5173 ...
start "HireMinds Frontend" cmd /k "cd /d "%PROJECT_DIR%\frontend" && npm run dev"

echo.
echo Waiting for services to initialize...
timeout /t 3 >nul

echo Opening browser at http://localhost:5173 ...
start http://localhost:5173

echo ===================================================
echo Backend and Frontend have been started in separate windows!
echo Keep those terminal windows open while using the app.
echo ===================================================
pause
