@echo off
chcp 65001 > nul
echo ================================================================================
echo АНАЛИЗ ПРОБЛЕМЫ С ЦЕНООБРАЗОВАНИЕМ В СИСТЕМЕ СНАЙПИНГА ТЕНДЕРОВ
echo ================================================================================
echo.

REM Проверка наличия OPENAI_API_KEY
if "%OPENAI_API_KEY%"=="" (
    echo ❌ ОШИБКА: Переменная окружения OPENAI_API_KEY не установлена!
    echo.
    echo Для установки API ключа используйте:
    echo    set OPENAI_API_KEY=sk-ваш-ключ-здесь
    echo.
    echo Или установите его постоянно через:
    echo    setx OPENAI_API_KEY "sk-ваш-ключ-здесь"
    echo.
    pause
    exit /b 1
)

echo ✅ API ключ найден
echo.

REM Переход в рабочую директорию
cd /d "%~dp0"

echo 📂 Рабочая директория: %CD%
echo.

REM Проверка наличия виртуального окружения
if not exist ".venv\Scripts\python.exe" (
    echo ❌ ОШИБКА: Виртуальное окружение .venv не найдено!
    echo.
    echo Создайте виртуальное окружение:
    echo    python -m venv .venv
    echo    .venv\Scripts\pip.exe install -r requirements.txt
    echo.
    pause
    exit /b 2
)

echo ✅ Виртуальное окружение найдено
echo.

REM Проверка наличия промпт-файла
if not exist "price_analysis_prompt.txt" (
    echo ❌ ОШИБКА: Файл price_analysis_prompt.txt не найден!
    echo.
    pause
    exit /b 3
)

echo ✅ Промпт-файл найден
echo.

REM Проверка наличия скрипта анализа
if not exist "analyze_pricing_issue.py" (
    echo ❌ ОШИБКА: Скрипт analyze_pricing_issue.py не найден!
    echo.
    pause
    exit /b 4
)

echo ✅ Скрипт анализа найден
echo.

echo ================================================================================
echo ЗАПУСК АНАЛИЗА...
echo ================================================================================
echo.

REM Запуск анализа
".venv\Scripts\python.exe" analyze_pricing_issue.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ Анализ завершился с ошибкой (код: %ERRORLEVEL%)
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ================================================================================
echo ✅ АНАЛИЗ ЗАВЕРШЕН УСПЕШНО!
echo ================================================================================
echo.
echo Результаты сохранены в папке logs\
echo Проверьте файл pricing_analysis_result_*.txt для получения детального анализа.
echo.
pause
