"""
Проверка, поддерживает ли ChatGoogle передачу tools
"""
import os
from dotenv import load_dotenv
from browser_use.llm.google import ChatGoogle
import inspect

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

print("=" * 70)
print("🔍 ИССЛЕДОВАНИЕ ChatGoogle")
print("=" * 70)

# Сигнатура ChatGoogle.__init__
print("\n📝 Сигнатура ChatGoogle.__init__:")
sig = inspect.signature(ChatGoogle.__init__)
print(f"   {sig}")

# Параметры
print("\n📋 Параметры:")
for param_name, param in sig.parameters.items():
    if param_name != 'self':
        print(f"   - {param_name}: {param.annotation} = {param.default}")

# Попробуем создать экземпляр с tools
print("\n🧪 ТЕСТ: ChatGoogle с параметром tools")
try:
    llm = ChatGoogle(
        model="gemini-2.5-computer-use-preview-10-2025",
        temperature=0.2,
        api_key=API_KEY,
        tools=[{'code_execution': {}}]
    )
    print("   ✅ УСПЕХ! ChatGoogle принимает параметр tools")
    print(f"   Тип: {type(llm)}")
    print(f"   Provider: {llm.provider if hasattr(llm, 'provider') else 'НЕТ АТРИБУТА'}")
except TypeError as e:
    print(f"   ❌ ОШИБКА: {e}")
    print("   ChatGoogle НЕ поддерживает параметр tools")

print("\n" + "=" * 70)
