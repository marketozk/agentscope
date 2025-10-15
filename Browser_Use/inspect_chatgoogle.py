import inspect
from browser_use.llm.google import ChatGoogle

print("Сигнатура ChatGoogle.__init__:\n")
print(inspect.signature(ChatGoogle.__init__))

print("\n" + "="*60)
print("Документация:\n")
print(ChatGoogle.__doc__)

print("\n" + "="*60)
print("Попытка создать с model параметром:\n")

try:
    model = ChatGoogle(model="gemini-1.5-flash")
    print(f"✅ Успешно создана модель")
    print(f"   {model}")
except Exception as e:
    print(f"❌ Ошибка: {e}")

print("\n" + "="*60)
print("Попытка создать без параметров:\n")

try:
    model = ChatGoogle()
    print(f"✅ Успешно создана модель по умолчанию")
    print(f"   {model}")
    if hasattr(model, 'model'):
        print(f"   Модель: {model.model}")
except Exception as e:
    print(f"❌ Ошибка: {e}")
