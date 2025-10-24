@echo off
chcp 65001 > nul

set "OPENAI_API_KEY=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"

echo ================================================================================
echo АНАЛИЗ ПРОБЛЕМЫ С ЦЕНООБРАЗОВАНИЕМ - ЗАПУСК
echo ================================================================================
echo.

cd /d "%~dp0"

.venv\Scripts\python.exe coolprompt_run_with_context.py --first price_analysis_prompt.txt --answer empty.txt --next empty.txt

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ Ошибка при выполнении (код: %ERRORLEVEL%)
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ================================================================================
echo ✅ ГОТОВО! Проверьте папку logs\
echo ================================================================================
pause
