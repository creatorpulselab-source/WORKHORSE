@echo off
title Prism — AI Social Media Content Studio
cd /d "%~dp0"

echo.
echo  Prism — AI Social Media Content Studio
echo  ----------------------------------

if not exist ".venv\Scripts\python.exe" (
    echo  Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 ( echo  ERROR: Python not found. & pause & exit /b 1 )
    echo  Installing dependencies...
    .venv\Scripts\pip install -r requirements.txt --quiet
    echo  Done!
)

echo.
echo  Starting server on port 7861...
echo  Local:   http://localhost:7861
echo  Network: http://YOUR-LAN-IP:7861
echo.
echo  Press Ctrl+C to stop.
echo.

.venv\Scripts\python.exe main.py
pause
