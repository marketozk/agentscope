import os
from dotenv import load_dotenv
from pathlib import Path
import google.generativeai as genai

# Загружаем .env
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ GOOGLE_API_KEY не найден в .env")
    exit(1)

genai.configure(api_key=api_key)

print("Доступные модели Gemini:\n")
print("="*70)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"\n✅ {model.name}")
        print(f"   Описание: {model.display_name}")
        print(f"   Методы: {', '.join(model.supported_generation_methods)}")
