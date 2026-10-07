@echo off
title WORKHORSE AI Command Center
cd /d "F:\WORKHORSE"

echo ================================================================
echo   WORKHORSE AI COMMAND CENTER ? PHASE 1
echo   Dual RTX 3060 Orchestration + Local Ollama / Whisper
echo ================================================================
echo.

set PYTHON_EXE=C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe

echo [1/2] Verifying Python runtime...
if not exist "%PYTHON_EXE%" (
    echo Python executable not found at %PYTHON_EXE%! Falling back to system python.
    set PYTHON_EXE=python
)

echo [2/2] Launching Command Center on http://127.0.0.1:8800 ...
start "" "http://127.0.0.1:8800"

"%PYTHON_EXE%" "F:\WORKHORSE\dashboard\server.py"

pause
