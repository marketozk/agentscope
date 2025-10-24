"""
Запуск анализа с GPT-4 Turbo (более доступная модель).
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
    from coolprompt.assistant import PromptTuner

from langchain_openai import ChatOpenAI
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
    # API ключ
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("[ERROR] OPENAI_API_KEY не установлен")
        return 2

    # Чтение промпта
    prompt_file = Path("price_analysis_prompt.txt")
    if not prompt_file.exists():
        print(f"[ERROR] Файл не найден: {prompt_file}")
        return 3

    prompt = prompt_file.read_text(encoding="utf-8")

    print("=" * 80)
    print("АНАЛИЗ ПРОБЛЕМЫ С ЦЕНООБРАЗОВАНИЕМ")
    print("=" * 80)
    print(f"\n📋 Промпт: {prompt_file}")
    print(f"🤖 Модель: gpt-4-turbo-preview")
    print(f"🔥 Temperature: 0.7")
    print(f"📝 Max tokens: 4000\n")

    # Инициализация с GPT-4
    llm = ChatOpenAI(
        model="gpt-4-turbo-preview",
        temperature=0.7,
        max_tokens=4000,
        api_key=api_key,
    )
    tuner = PromptTuner(target_model=llm)

    print("⚙️  Запуск анализа через GPT-4...\n")
    
    try:
        tuner.run(prompt)
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print("\nПопытка использовать GPT-3.5-turbo...")
        
        # Попытка с GPT-3.5
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=4000,
            api_key=api_key,
        )
        tuner = PromptTuner(target_model=llm)
        tuner.run(prompt)

    # Сохранение результатов
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    result_file = logs_dir / f"pricing_analysis_{ts}.txt"
    final = getattr(tuner, "final_prompt", "") or ""
    result_file.write_text(final, encoding="utf-8")

    print("\n" + "=" * 80)
    print("✅ АНАЛИЗ ЗАВЕРШЕН")
    print("=" * 80)
    print(f"\n📁 Результат: {result_file}\n")
    print("=" * 80)
    print("РЕЗУЛЬТАТ АНАЛИЗА:")
    print("=" * 80)
    print(final)
    print("=" * 80)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
