"""
Исследование правильного способа использования Code Execution Tool
"""
import google.generativeai as genai
from google.generativeai.types import Tool
from google.generativeai.types import content_types
import inspect

print("=" * 70)
print("🔍 ИССЛЕДОВАНИЕ content_types.FunctionLibraryType")
print("=" * 70)

# Проверим, что такое FunctionLibraryType
print(f"\n📚 content_types.FunctionLibraryType:")
try:
    print(f"   Тип: {content_types.FunctionLibraryType}")
    print(f"   Документация: {inspect.getdoc(content_types.FunctionLibraryType)}")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# Проверим функцию to_function_library
print(f"\n🔧 content_types.to_function_library:")
try:
    sig = inspect.signature(content_types.to_function_library)
    print(f"   Сигнатура: {sig}")
    print(f"   Документация: {inspect.getdoc(content_types.to_function_library)}")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# Попробуем создать Tool с code_execution
print(f"\n🧪 ТЕСТИРОВАНИЕ РАЗНЫХ ВАРИАНТОВ:")
print(f"\n1️⃣ Вариант: Tool(code_execution=True)")
try:
    tool1 = Tool(code_execution=True)
    print(f"   ✅ Успех! Тип: {type(tool1)}")
    print(f"   Значение: {tool1}")
except Exception as e:
    print(f"   ❌ Ошибка: {type(e).__name__}: {e}")

print("\n2️⃣ Вариант: Tool(code_execution={})")
try:
    tool2 = Tool(code_execution={})
    print(f"   ✅ Успех! Тип: {type(tool2)}")
    print(f"   Значение: {tool2}")
except Exception as e:
    print(f"   ❌ Ошибка: {type(e).__name__}: {e}")

print(f"\n3️⃣ Вариант: [Tool(code_execution=True)]")
try:
    tools_list = [Tool(code_execution=True)]
    print(f"   ✅ Успех! Тип: {type(tools_list)}")
    print(f"   Значение: {tools_list}")
except Exception as e:
    print(f"   ❌ Ошибка: {type(e).__name__}: {e}")

# Попробуем передать в GenerativeModel
print(f"\n4️⃣ Вариант: GenerativeModel(..., tools=[Tool(code_execution=True)])")
try:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        tools=[Tool(code_execution=True)]
    )
    print(f"   ✅ УСПЕХ! Модель создана!")
    print(f"   Тип модели: {type(model)}")
except Exception as e:
    print(f"   ❌ Ошибка: {type(e).__name__}: {e}")

print("\n5️⃣ Вариант: GenerativeModel(..., tools={'code_execution': True})")
try:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        tools={'code_execution': True}
    )
    print(f"   ✅ УСПЕХ! Модель создана!")
    print(f"   Тип модели: {type(model)}")
except Exception as e:
    print(f"   ❌ Ошибка: {type(e).__name__}: {e}")

print("\n6️⃣ Вариант: GenerativeModel(..., tools=[{'code_execution': {}}])")
try:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        tools=[{'code_execution': {}}]
    )
    print(f"   ✅ УСПЕХ! Модель создана!")
    print(f"   Тип модели: {type(model)}")
except Exception as e:
    print(f"   ❌ Ошибка: {type(e).__name__}: {e}")

print("\n" + "=" * 70)
