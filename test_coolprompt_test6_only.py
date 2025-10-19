"""
Быстрый тест только Теста 6 - Продвинутая конфигурация
"""
import os
import sys
from io import StringIO
try:
    from coolprompt.assistant import PromptTuner
except Exception:
    import sys as _sys
    from pathlib import Path as _Path
    _ROOT = _Path(__file__).resolve().parent
    _LOCAL_CP = _ROOT / "coolprompt_repo"
    if _LOCAL_CP.exists():
        _sys.path.insert(0, str(_LOCAL_CP))
    from coolprompt.assistant import PromptTuner  # type: ignore
from langchain_openai import ChatOpenAI

# Подавляем NLTK
import nltk
class SuppressOutput:
    def __enter__(self):
        self._original = sys.stderr
        sys.stderr = StringIO()
    def __exit__(self, *args):
        sys.stderr = self._original

with SuppressOutput():
    nltk.download('wordnet', quiet=True)
    nltk.download('punkt_tab', quiet=True) 
    nltk.download('omw-1.4', quiet=True)

API_KEY = os.environ.get("OPENAI_API_KEY", "your-api-key-here")

print("=" * 70)
print("ТЕСТ 6: ПРОДВИНУТАЯ КОНФИГУРАЦИЯ (исправленный)")
print("=" * 70)

try:
    llm = ChatOpenAI(
        model="gpt-5-chat-latest",
        temperature=0.8,
        max_tokens=4000,  # Увеличено!
        api_key=API_KEY
    )
    
    prompt_tuner = PromptTuner(target_model=llm)
    
    task = "Generate creative product names for a new eco-friendly water bottle"
    
    print(f"\n📝 Задача: {task}")
    print("🔄 Запуск с max_tokens=4000...")
    
    # Если нужно запустить на составном тексте (первый промпт + ответ + следующий промпт)
    # используйте скрипт coolprompt_run_with_context.py
    # либо раскомментируйте код ниже и задайте путь к файлам.
    #
    # from pathlib import Path
    # def _read(p: str) -> str:
    #     return Path(p).read_text(encoding="utf-8", errors="ignore")
    # composite_prompt = _read("first.txt") + "\n\n" + _read("answer.txt") + "\n\n" + _read("next.txt")
    # prompt_tuner.run(composite_prompt)
    #
    # По умолчанию выполняем тестовую задачу
    prompt_tuner.run(task)
    
    print("\n✅ УСПЕХ!")
    print("\n" + "=" * 70)
    print("ОПТИМИЗИРОВАННЫЙ ПРОМПТ:")
    print("=" * 70)
    print(prompt_tuner.final_prompt)
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
