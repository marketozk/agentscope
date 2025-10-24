"""
Скрипт для проверки готовности системы анализа проблемы с ценообразованием.
Проверяет все необходимые компоненты перед запуском.
"""

import os
import sys
from pathlib import Path


def check_api_key():
    """Проверка наличия OPENAI_API_KEY"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        return False, "❌ OPENAI_API_KEY не установлен"
    if not api_key.startswith("sk-"):
        return False, "⚠️  OPENAI_API_KEY имеет неправильный формат"
    return True, f"✅ OPENAI_API_KEY установлен ({api_key[:10]}...)"


def check_venv():
    """Проверка наличия виртуального окружения"""
    venv_python = Path(".venv/Scripts/python.exe")
    if not venv_python.exists():
        return False, "❌ Виртуальное окружение .venv не найдено"
    return True, "✅ Виртуальное окружение найдено"


def check_coolprompt():
    """Проверка наличия coolprompt_repo"""
    coolprompt_dir = Path("coolprompt_repo")
    if not coolprompt_dir.exists():
        return False, "❌ Папка coolprompt_repo не найдена"
    
    assistant_file = coolprompt_dir / "coolprompt" / "assistant.py"
    if not assistant_file.exists():
        return False, "❌ coolprompt/assistant.py не найден"
    
    return True, "✅ coolprompt_repo найден и настроен"


def check_files():
    """Проверка наличия необходимых файлов"""
    files = {
        "Промпт": "price_analysis_prompt.txt",
        "Скрипт анализа": "analyze_pricing_issue.py",
        "Bat-файл": "run_pricing_analysis.bat",
        "Инструкция": "PRICING_ANALYSIS_INSTRUCTION.md"
    }
    
    results = []
    all_ok = True
    
    for name, filename in files.items():
        filepath = Path(filename)
        if filepath.exists():
            results.append((True, f"✅ {name}: {filename}"))
        else:
            results.append((False, f"❌ {name}: {filename} не найден"))
            all_ok = False
    
    return all_ok, results


def check_requirements():
    """Проверка установленных пакетов"""
    try:
        import langchain_openai
        import nltk
        return True, "✅ Необходимые пакеты установлены"
    except ImportError as e:
        return False, f"❌ Не хватает пакетов: {e}"


def main():
    print("=" * 80)
    print("ПРОВЕРКА ГОТОВНОСТИ СИСТЕМЫ АНАЛИЗА ПРОБЛЕМЫ С ЦЕНООБРАЗОВАНИЕМ")
    print("=" * 80)
    print()
    
    # Проверка API ключа
    print("1. Проверка OPENAI_API_KEY...")
    ok, msg = check_api_key()
    print(f"   {msg}")
    if not ok:
        print("   💡 Установите: set OPENAI_API_KEY=sk-ваш-ключ-здесь")
    print()
    
    # Проверка виртуального окружения
    print("2. Проверка виртуального окружения...")
    venv_ok, msg = check_venv()
    print(f"   {msg}")
    if not venv_ok:
        print("   💡 Создайте: python -m venv .venv")
        print("   💡 Установите зависимости: .venv\\Scripts\\pip.exe install -r requirements.txt")
    print()
    
    # Проверка coolprompt
    print("3. Проверка coolprompt_repo...")
    cp_ok, msg = check_coolprompt()
    print(f"   {msg}")
    if not cp_ok:
        print("   💡 Убедитесь, что папка coolprompt_repo находится в рабочей директории")
    print()
    
    # Проверка файлов
    print("4. Проверка необходимых файлов...")
    files_ok, results = check_files()
    for ok, msg in results:
        print(f"   {msg}")
    print()
    
    # Проверка зависимостей
    print("5. Проверка установленных пакетов...")
    req_ok, msg = check_requirements()
    print(f"   {msg}")
    if not req_ok:
        print("   💡 Установите: .venv\\Scripts\\pip.exe install -r requirements.txt")
    print()
    
    # Итоговый статус
    print("=" * 80)
    all_ok = ok and venv_ok and cp_ok and files_ok and req_ok
    
    if all_ok:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
        print()
        print("🚀 Система готова к работе!")
        print()
        print("Для запуска анализа используйте:")
        print("   run_pricing_analysis.bat")
        print()
        print("Или:")
        print("   .venv\\Scripts\\python.exe analyze_pricing_issue.py")
        print("=" * 80)
        return 0
    else:
        print("⚠️  ОБНАРУЖЕНЫ ПРОБЛЕМЫ!")
        print()
        print("Исправьте указанные проблемы и запустите проверку снова:")
        print("   .venv\\Scripts\\python.exe check_readiness.py")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
