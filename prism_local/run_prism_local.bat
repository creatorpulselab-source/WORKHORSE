@echo off
title Prism Studio (Local Copy - Port 7862)
cd /d "F:\WORKHORSE\prism_local"

echo ================================================================
echo   PRISM STUDIO ? ISOLATED LOCAL COPY (PORT 7862)
echo   Note: Runs independently without modifying or touching F:\QUE
echo ================================================================
echo.

set PYTHON_EXE=C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe

start "" "http://127.0.0.1:7862"
"%PYTHON_EXE%" -m uvicorn main:app --host 127.0.0.1 --port 7862 --reload

pause
