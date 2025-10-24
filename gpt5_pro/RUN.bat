@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo   ЗАПУСК АНАЛИЗА GPT-5 PRO
echo ========================================
echo.

REM Копируем правильный промпт
echo Подготовка промпта...
copy /Y "..\price_analysis_prompt.txt" "0_prompt.txt" >nul

REM Запускаем скрипт
echo Отправка в GPT-5 Pro...
echo.
"..\.venv\Scripts\python.exe" "1_send_request.py"

echo.
echo ========================================
echo   ГОТОВО
echo ========================================
pause
