"""
Проверка доступных моделей Gemini 1.5 через API
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Загружаем .env
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Получаем API ключ
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ GOOGLE_API_KEY не найден в .env")
    exit(1)

# Настраиваем API
genai.configure(api_key=api_key)

print("\n📋 ДОСТУПНЫЕ МОДЕЛИ GEMINI:\n")
print("="*80)

try:
    # Получаем список всех моделей
    models = genai.list_models()
    
    gemini_models = []
    for model in models:
        if 'gemini' in model.name.lower() and 'generateContent' in model.supported_generation_methods:
            gemini_models.append(model)
    
    # Сортируем по версии (1.5 сначала)
    gemini_models.sort(key=lambda m: m.name)
    
    for model in gemini_models:
        name = model.name.replace('models/', '')
        
        # Определяем версию
        version = "неизвестно"
        if '1.5' in name or '1-5' in name:
            version = "1.5"
        elif '2.0' in name or '2-0' in name:
            version = "2.0"
        elif '2.5' in name or '2-5' in name:
            version = "2.5"
        
        print(f"\n🤖 {name}")
        print(f"   Версия: {version}")
        print(f"   Display Name: {model.display_name}")
        print(f"   Description: {model.description[:100] if model.description else 'N/A'}...")
        
        # Лимиты (если доступны)
        if hasattr(model, 'rate_limit'):
            print(f"   Rate Limit: {model.rate_limit}")
        
        # Методы генерации
        print(f"   Методы: {', '.join(model.supported_generation_methods)}")
    
    print("\n" + "="*80)
    print(f"\n✅ Найдено {len(gemini_models)} моделей Gemini\n")
    
    # Рекомендации
    print("💡 РЕКОМЕНДАЦИИ:")
    print("   - gemini-1.5-flash: Быстрая, стабильная, хорошие лимиты")
    print("   - gemini-1.5-pro: Мощная, для сложных задач")
    print("   - gemini-2.0-flash-exp: Экспериментальная, может быть нестабильна")
    print("   - gemini-2.5-flash: Новейшая, но меньше лимит на free tier")
    
except Exception as e:
    print(f"❌ Ошибка при получении списка моделей: {e}")
    print("\nВозможные причины:")
    print("  1. Неверный API ключ")
    print("  2. Нет доступа к API")
    print("  3. Превышен дневной лимит")
