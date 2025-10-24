"""
Скрипт для анализа проблемы с ценообразованием в системе снайпинга тендеров.
Использует PromptTuner для глубокого анализа кода и логов.

Использование (Windows CMD):
  set OPENAI_API_KEY=sk-...
  .\.venv\Scripts\python.exe analyze_pricing_issue.py

Результаты сохраняются в папку logs/:
- logs/pricing_analysis_prompt_YYYYmmdd_HHMMSS.txt — исходный промпт
- logs/pricing_analysis_result_YYYYmmdd_HHMMSS.txt — результат анализа от GPT-5
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from io import StringIO

# Поддержка локального репозитория coolprompt_repo
try:
    from coolprompt.assistant import PromptTuner
except Exception:
    _ROOT = Path(__file__).resolve().parent
    _LOCAL_CP = _ROOT / "coolprompt_repo"
    if _LOCAL_CP.exists():
        sys.path.insert(0, str(_LOCAL_CP))
    from coolprompt.assistant import PromptTuner  # type: ignore

from langchain_openai import ChatOpenAI

# Тихая загрузка NLTK
import nltk


class _SuppressStderr:
    def __enter__(self):
        self._orig = sys.stderr
        sys.stderr = StringIO()
    def __exit__(self, *args):
        sys.stderr = self._orig


with _SuppressStderr():
    try:
        nltk.download('wordnet', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        nltk.download('omw-1.4', quiet=True)
    except Exception:
        pass


def main() -> int:
    # Проверка ключа API
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("[ERROR] Переменная окружения OPENAI_API_KEY не установлена.")
        print("\nДля установки используйте:")
        print("  set OPENAI_API_KEY=sk-your-key-here")
        return 2

    # Путь к промпту
    prompt_path = Path("price_analysis_prompt.txt").resolve()
    if not prompt_path.exists():
        print(f"[ERROR] Не найден файл промпта: {prompt_path}")
        print("\nСоздайте файл price_analysis_prompt.txt с описанием задачи.")
        return 3

    # Читаем промпт
    analysis_prompt = prompt_path.read_text(encoding="utf-8", errors="ignore")

    # Инициализируем модель GPT-5
    print("=" * 80)
    print("АНАЛИЗ ПРОБЛЕМЫ С ЦЕНООБРАЗОВАНИЕМ В СИСТЕМЕ СНАЙПИНГА ТЕНДЕРОВ")
    print("=" * 80)
    print(f"\n📋 Промпт загружен из: {prompt_path}")
    print(f"📊 Модель: gpt-5-chat-latest")
    print(f"🌡️  Temperature: 0.7 (для точного анализа)")
    print(f"📝 Max tokens: 16000 (для детального ответа)")
    
    llm = ChatOpenAI(
        model="gpt-5-chat-latest",
        temperature=0.7,  # Немного ниже для более точного анализа
        max_tokens=16000,  # Увеличено для детального анализа
        api_key=api_key,
    )
    
    tuner = PromptTuner(target_model=llm)

    print("\n⚙️  Запуск PromptTuner для анализа...")
    print("-" * 80)
    
    # Запускаем анализ
    tuner.run(analysis_prompt)

    # Подготовка путей сохранения
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    prompt_backup_path = logs_dir / f"pricing_analysis_prompt_{ts}.txt"
    result_path = logs_dir / f"pricing_analysis_result_{ts}.txt"

    # Сохраняем результаты
    prompt_backup_path.write_text(analysis_prompt, encoding="utf-8")
    
    final_result = getattr(tuner, "final_prompt", "") or ""
    result_path.write_text(final_result, encoding="utf-8")

    # Выводим результаты
    print("\n" + "=" * 80)
    print("✅ АНАЛИЗ ЗАВЕРШЕН УСПЕШНО!")
    print("=" * 80)
    print(f"\n📁 Результаты сохранены:")
    print(f"   • Исходный промпт: {prompt_backup_path}")
    print(f"   • Результат анализа: {result_path}")

    print("\n" + "=" * 80)
    print("РЕЗУЛЬТАТ АНАЛИЗА ОТ GPT-5:")
    print("=" * 80)
    print(final_result)
    print("=" * 80)

    print("\n💡 Следующие шаги:")
    print("   1. Изучите результат анализа выше")
    print("   2. Проверьте код SNIFFER_BIG_NEW_STAVROPOL_3-5-3_LIB.py")
    print("   3. Примените предложенные исправления")
    print("   4. Протестируйте на проблемных тендерах")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
