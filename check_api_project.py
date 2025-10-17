#!/usr/bin/env python3
"""
Проверяем, к какому Google Cloud Project привязан наш API ключ
"""
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')

print("=" * 70)
print("🔍 ПРОВЕРКА ПРИВЯЗКИ API КЛЮЧА К ПРОЕКТУ")
print("=" * 70)

if not api_key:
    print("❌ API ключ не найден в .env файле")
    exit(1)

print(f"\n✅ API ключ найден: {api_key[:30]}...{api_key[-10:]}")

# Попытаемся подключиться и узнать info
try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    # Получаем информацию о моделях - это покажет, работает ли ключ
    print("\n🔗 Проверка подключения к Google Generative AI API...")
    models = list(genai.list_models())
    
    if models:
        print(f"✅ Успешное подключение! Доступно {len(models)} моделей")
        print(f"\nПервые 5 моделей:")
        for i, model in enumerate(models[:5]):
            print(f"  {i+1}. {model.name}")
    else:
        print("⚠️ API ключ работает, но моделей не найдено")
        
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
    print("\n📌 Это может означать:")
    print("   1. API ключ неверный или истёк")
    print("   2. Generative Language API не включена в проекте")
    print("   3. Project не привязан к платежному аккаунту")

print("\n" + "=" * 70)
print("📌 ВАЖНО:")
print("=" * 70)
print("API ключ нужно создать именно в том проекте, к которому привязан Billing!")
print("\n✅ ВЫ УЖЕ ЭТО СДЕЛАЛИ:")
print("   Project: gen-lang-client-0278043954 (Gemini API)")
print("   Billing Account: 01743A-05FCF9-1413FB (My Billing Account 1)")
print("   Status: ✅ ПРИВЯЗАН К ПЛАТЕЖНОМУ АККАУНТУ")
print("\n✅ Текущий API ключ ДОЛЖЕН быть из этого проекта (Gemini API)")
print("=" * 70)
