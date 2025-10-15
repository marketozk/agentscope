from browser_use.llm.google import ChatGoogle

print("Попытка создать модели Gemini:\n")

# Попробуем разные варианты имён
model_names = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "models/gemini-1.5-flash",
    "models/gemini-2.0-flash-exp",
]

for name in model_names:
    try:
        model = ChatGoogle(model_name=name)
        print(f"✅ {name} - OK")
        print(f"   Model: {model}")
        break
    except Exception as e:
        print(f"❌ {name} - Ошибка: {str(e)[:100]}")
