"""
Быстрый тест только Теста 6 - Продвинутая конфигурация
"""
import os
import sys
from io import StringIO
from coolprompt.assistant import PromptTuner
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
