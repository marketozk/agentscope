"""
Запуск PromptTuner на составном тексте (без изменений):
- first_prompt + "\n\n" + model_answer + "\n\n" + next_prompt

Использование (Windows CMD):
  set OPENAI_API_KEY=sk-...
  .\.venv\Scripts\python.exe coolprompt_run_with_context.py --first path\to\first.txt --answer path\to\answer.txt --next path\to\next.txt

Результаты сохраняются в папку logs/:
- logs/composite_prompt_YYYYmmdd_HHMMSS.txt — исходный составной промпт
- logs/coolprompt_final_prompt_YYYYmmdd_HHMMSS.txt — оптимизированный промпт от PromptTuner
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from io import StringIO

# Поддержка локального репозитория coolprompt_repo, если пакет не установлен глобально
try:
    from coolprompt.assistant import PromptTuner
except Exception:
    import sys as _sys
    _ROOT = Path(__file__).resolve().parent
    _LOCAL_CP = _ROOT / "coolprompt_repo"
    if _LOCAL_CP.exists():
        _sys.path.insert(0, str(_LOCAL_CP))
    from coolprompt.assistant import PromptTuner  # type: ignore

from langchain_openai import ChatOpenAI


# Тихая загрузка необходимых пакетов NLTK (как в тестовом файле)
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
        # Если NLTK отсутствует или офлайн, просто продолжаем
        pass


def _read_text(path: Path) -> str:
    data = path.read_text(encoding="utf-8", errors="ignore")
    # Возвращаем текст без каких-либо модификаций
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PromptTuner with composite prompt (first + answer + next) verbatim")
    parser.add_argument("--first", required=True, type=Path, help="Path to the original first prompt text file")
    parser.add_argument("--answer", required=True, type=Path, help="Path to the model answer text file")
    parser.add_argument("--next", required=True, type=Path, help="Path to the follow-up prompt text file")
    parser.add_argument("--model", default="gpt-5-chat-latest", help="Target model for PromptTuner (default: gpt-5-chat-latest)")
    parser.add_argument("--temperature", type=float, default=0.8, help="Sampling temperature for LLM (default: 0.8)")
    parser.add_argument("--max_tokens", type=int, default=4000, help="Max tokens for LLM generation (default: 4000)")
    args = parser.parse_args()

    # Проверка ключа API
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("[ERROR] Переменная окружения OPENAI_API_KEY не установлена или имеет плейсхолдер.")
        return 2

    # Читаем три части без модификаций
    first_text = _read_text(args.first)
    answer_text = _read_text(args.answer)
    next_text = _read_text(args.next)

    # Строгое объединение без добавления служебных заголовков
    composite_prompt = f"{first_text}\n\n{answer_text}\n\n{next_text}"

    # Инициализируем модель и PromptTuner
    llm = ChatOpenAI(
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        api_key=api_key,
    )
    tuner = PromptTuner(target_model=llm)

    print("=" * 70)
    print("PromptTuner: запуск на составном тексте (без изменений)")
    print("=" * 70)

    # Запускаем тюнинг; метод не задаем — будет использован дефолт (обычно 'hype')
    tuner.run(composite_prompt)

    # Подготовка путей сохранения
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    composite_path = logs_dir / f"composite_prompt_{ts}.txt"
    final_path = logs_dir / f"coolprompt_final_prompt_{ts}.txt"

    # Сохраняем оба артефакта
    composite_path.write_text(composite_prompt, encoding="utf-8")
    final_prompt = getattr(tuner, "final_prompt", "") or ""
    final_path.write_text(final_prompt, encoding="utf-8")

    # Выводим краткий отчет
    print("\n✅ УСПЕХ! Результаты:")
    print(f"- Составной промпт: {composite_path}")
    print(f"- Оптимизированный промпт: {final_path}")

    print("\n" + "=" * 70)
    print("ОПТИМИЗИРОВАННЫЙ ПРОМПТ:")
    print("=" * 70)
    print(final_prompt)
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
