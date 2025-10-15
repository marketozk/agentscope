import os
from dotenv import load_dotenv
from pathlib import Path
from google import genai
from google.genai import types

# Загружаем .env
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ GOOGLE_API_KEY не найден в .env")
    exit(1)

# Создаём клиента с новым SDK
client = genai.Client(api_key=api_key)

print("Доступные модели Gemini (через новый SDK):\n")
print("="*70)

try:
    for model in client.models.list():
        print(f"\n✅ {model.name}")
        if hasattr(model, 'display_name'):
            print(f"   Название: {model.display_name}")
        if hasattr(model, 'description'):
            print(f"   Описание: {model.description[:100]}")
except Exception as e:
    print(f"❌ Ошибка при получении списка моделей: {e}")
    print("\n💡 Попробуем использовать известные модели напрямую:\n")
    
    # Известные модели из документации
    known_models = [
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
        "gemini-2.5-flash",
    ]
    
    for model_name in known_models:
        try:
            # Пробуем создать модель
            test_model = client.models.get(model_name)
            print(f"✅ {model_name} - доступна")
        except Exception as e:
            print(f"❌ {model_name} - недоступна: {str(e)[:50]}")
