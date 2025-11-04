@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Определяем директорию скрипта (корень репозитория)
set "SCRIPT_DIR=%~dp0"
set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "APP=%SCRIPT_DIR%flet_demo.py"

if exist "%VENV_PY%" (
    echo Запуск через виртуальное окружение: "%VENV_PY%"
    "%VENV_PY%" "%APP%"
) else (
    echo Виртуальное окружение не найдено, пробуем системный python
    python "%APP%"
)

endlocal
