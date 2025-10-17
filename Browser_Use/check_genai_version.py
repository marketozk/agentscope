"""
Проверка версии google-generativeai и правильного синтаксиса для Code Execution Tool
"""
import google.generativeai as genai
from google.generativeai.types import Tool
import inspect

print("=" * 70)
print("📦 ИНФОРМАЦИЯ О БИБЛИОТЕКЕ google-generativeai")
print("=" * 70)

# Версия
print(f"\n🔢 Версия: {genai.__version__}")

# Проверка доступных атрибутов Tool
print(f"\n🔧 Атрибуты класса Tool:")
tool_attrs = [attr for attr in dir(Tool) if not attr.startswith('_')]
for attr in tool_attrs:
    obj = getattr(Tool, attr)
    print(f"   - {attr}: {type(obj).__name__}")

# Проверка code_execution
print(f"\n🎯 Tool.code_execution:")
print(f"   Тип: {type(Tool.code_execution)}")
print(f"   Значение: {Tool.code_execution}")

# Попробуем понять, как его использовать
if isinstance(Tool.code_execution, property):
    print(f"\n   ⚠️  code_execution - это property!")
    print(f"   Возможно, нужно использовать Tool.code_execution напрямую")

# Проверка сигнатуры GenerativeModel
print(f"\n📝 Сигнатура GenerativeModel.__init__:")
sig = inspect.signature(genai.GenerativeModel.__init__)
print(f"   {sig}")

print(f"\n💡 Параметр 'tools' ожидает:")
if 'tools' in sig.parameters:
    param = sig.parameters['tools']
    print(f"   Тип аннотации: {param.annotation}")
    print(f"   Значение по умолчанию: {param.default}")

print("\n" + "=" * 70)
