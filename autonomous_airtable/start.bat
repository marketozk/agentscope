@echo off
chcp 65001 > nul
echo ============================================================
echo   🤖 АВТОНОМНАЯ СИСТЕМА РЕГИСТРАЦИИ AIRTABLE
echo ============================================================
echo.
cd /d "%~dp0.."
.venv\Scripts\python.exe autonomous_airtable\autonomous_registration_loop.py
pause
