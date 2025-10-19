"""
Подаёт в PromptTuner единый высокоуровневый промпт (без модификаций),
основанный на последнем описании системы и принципе: один общий policy-промпт,
низкоуровневое самообучение остаётся как есть.
"""
from __future__ import annotations

import os
from pathlib import Path
from io import StringIO
import sys

# Локальный импорт coolprompt при необходимости
try:
    from coolprompt.assistant import PromptTuner
except Exception:
    from pathlib import Path as _Path
    _ROOT = _Path(__file__).resolve().parent
    _LOCAL_CP = _ROOT / "coolprompt_repo"
    if _LOCAL_CP.exists():
        sys.path.insert(0, str(_LOCAL_CP))
    from coolprompt.assistant import PromptTuner  # type: ignore

from langchain_openai import ChatOpenAI

import nltk

class _Suppress:
    def __enter__(self):
        self._orig = sys.stderr
        sys.stderr = StringIO()
    def __exit__(self, *args):
        sys.stderr = self._orig

with _Suppress():
    try:
        nltk.download('wordnet', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        nltk.download('omw-1.4', quiet=True)
    except Exception:
        pass


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("[ERROR] OPENAI_API_KEY не задан.")
        return 2

    prompt_path = Path("Browser_Use/prompt_highlevel_single.txt").resolve()
    if not prompt_path.exists():
        print(f"[ERROR] Не найден файл: {prompt_path}")
        return 3

    start_prompt = prompt_path.read_text(encoding="utf-8", errors="ignore")

    llm = ChatOpenAI(
        model="gpt-5-chat-latest",
        temperature=0.8,
        max_tokens=4000,
        api_key=api_key,
    )
    tuner = PromptTuner(target_model=llm)

    print("=" * 70)
    print("Запуск PromptTuner на едином high-level промпте (без изменений)")
    print("=" * 70)
    tuner.run(start_prompt)

    out = tuner.final_prompt or ""
    out_path = Path("logs")
    out_path.mkdir(exist_ok=True)
    (out_path / "highlevel_single_final.txt").write_text(out, encoding="utf-8")
    print("\nГотово. Итоговый промпт сохранён в logs/highlevel_single_final.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
