@echo off
setlocal ENABLEDELAYEDEXPANSION
set "SCRIPT_DIR=%~dp0"
set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "APP=%SCRIPT_DIR%flet_dashboard_mock.py"
if exist "%VENV_PY%" (
  "%VENV_PY%" "%APP%"
) else (
  python "%APP%"
)
endlocal
