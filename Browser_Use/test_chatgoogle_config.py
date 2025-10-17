"""
Проверка передачи tools через параметр config в ChatGoogle
"""
import os
from dotenv import load_dotenv
from browser_use.llm.google import ChatGoogle
import inspect

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

print("=" * 70)
print("🔍 ТЕСТ: ChatGoogle с tools через config")
print("=" * 70)

# Попытка 1: передать tools через config как dict
print("\n1️⃣ Вариант: config={'tools': [{'code_execution': {}}]}")
try:
    llm = ChatGoogle(
        model="gemini-2.5-computer-use-preview-10-2025",
        temperature=0.2,
        api_key=API_KEY,
        config={'tools': [{'code_execution': {}}]}
    )
    print("   ✅ УСПЕХ! Модель создана")
    print(f"   Тип: {type(llm)}")
    print(f"   Provider: {llm.provider if hasattr(llm, 'provider') else 'НЕТ АТРИБУТА'}")
except Exception as e:
    print(f"   ❌ ОШИБКА: {type(e).__name__}: {e}")

# Попытка 2: через google.genai.types
print("\n2️⃣ Вариант: Используем google.genai.types.Tool")
try:
    from google.genai import types
    
    config_dict = types.GenerateContentConfig(
        tools=[types.Tool(code_execution=types.ToolCodeExecution)]
    )
    
    llm = ChatGoogle(
        model="gemini-2.5-computer-use-preview-10-2025",
        temperature=0.2,
        api_key=API_KEY,
        config=config_dict
    )
    print("   ✅ УСПЕХ! Модель создана")
    print(f"   Тип: {type(llm)}")
    print(f"   Provider: {llm.provider if hasattr(llm, 'provider') else 'НЕТ АТРИБУТА'}")
except Exception as e:
    print(f"   ❌ ОШИБКА: {type(e).__name__}: {e}")

print("\n" + "=" * 70)
