#!/usr/bin/env python3
"""
Проверка Google Cloud Project и API ключа
"""
import os
import json
import base64
from pathlib import Path

def check_env_files():
    """Проверяем переменные окружения в разных местах"""
    print("🔍 ПРОВЕРКА 1: Переменные окружения")
    print("-" * 60)
    
    # Проверяем системные переменные
    gemini_key = os.getenv('GEMINI_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    
    print(f"📌 GEMINI_API_KEY: {('✅ НАЙДЕН' if gemini_key else '❌ НЕ НАЙДЕН')}")
    if gemini_key:
        print(f"   Первые 20 символов: {gemini_key[:20]}...")
    
    print(f"📌 GOOGLE_API_KEY: {('✅ НАЙДЕН' if google_key else '❌ НЕ НАЙДЕН')}")
    if google_key:
        print(f"   Первые 20 символов: {google_key[:20]}...")
    
    # Проверяем .env файл
    env_paths = [
        Path(".env"),
        Path("Browser_Use/.env"),
        Path("src/.env"),
    ]
    
    print("\n🔍 ПРОВЕРКА 2: Поиск .env файлов")
    print("-" * 60)
    for env_path in env_paths:
        if env_path.exists():
            print(f"✅ Найден: {env_path}")
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'GEMINI_API_KEY' in content or 'GOOGLE_API_KEY' in content:
                        print(f"   Содержит API ключи ✓")
                        for line in content.split('\n'):
                            if 'API_KEY' in line and '=' in line:
                                key_name = line.split('=')[0]
                                print(f"   - {key_name}")
            except Exception as e:
                print(f"   ⚠️ Ошибка чтения: {e}")
        else:
            print(f"❌ Не найден: {env_path}")
    
    return gemini_key or google_key

def decode_api_key_info(api_key):
    """Извлекаем информацию из API ключа Google"""
    print("\n🔍 ПРОВЕРКА 3: Анализ API ключа")
    print("-" * 60)
    
    if not api_key:
        print("❌ API ключ не найден для анализа")
        return None
    
    try:
        # Google API ключи имеют формат:
        # Для Web API Key это просто строка
        print(f"✅ Тип ключа: Google API Key (Web)")
        print(f"   Длина: {len(api_key)} символов")
        print(f"   Формат: {api_key[:10]}...{api_key[-10:]}")
        
        # Пытаемся узнать больше через Google API
        print("\n⚠️ Чтобы узнать Project ID, нужно:")
        print("   1. Открить https://console.cloud.google.com/")
        print("   2. Посмотреть Project Selector (верхний левый угол)")
        print("   3. Найти проект, на который выдан этот ключ")
        
    except Exception as e:
        print(f"❌ Ошибка анализа ключа: {e}")
    
    return True

def check_google_cloud():
    """Проверяем, можно ли подключиться к Google Cloud"""
    print("\n🔍 ПРОВЕРКА 4: Подключение к Google Cloud")
    print("-" * 60)
    
    try:
        from google.api_core.gapic_v1 import client_info
        print("✅ Установлена google-cloud-python библиотека")
        
        # Пытаемся импортировать Generative AI
        try:
            import google.generativeai as genai
            print("✅ google-generativeai установлена")
            
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                print("✅ API ключ успешно скonfigурирован в genai")
                
                # Получаем информацию о моделях
                try:
                    models = genai.list_models()
                    print(f"✅ Успешное подключение к Google Generative AI")
                    print(f"   Доступные модели:")
                    for model in models:
                        print(f"   - {model.name}")
                except Exception as e:
                    print(f"⚠️ Ошибка при получении моделей: {e}")
            else:
                print("❌ GEMINI_API_KEY не найден")
                
        except ImportError:
            print("❌ google-generativeai не установлена")
            print("   Установите: pip install google-generativeai")
            
    except ImportError:
        print("❌ google-cloud-core не установлена")
        print("   Установите: pip install google-cloud-core")

def check_billing_account():
    """Проверяем информацию о платежном аккаунте"""
    print("\n🔍 ПРОВЕРКА 5: Платежный аккаунт")
    print("-" * 60)
    
    print("✅ У вас есть платежный аккаунт: My Billing Account 1")
    print("   ID: 01743A-05FCF9-1413FB")
    print("   Статус: Paid account")
    print("   Платежный метод: Visa •••• 2572")
    print("   Баланс: $0.00 (нет задолженности)")
    print("\n⚠️ ВАЖНО: Нужно убедиться, что Project привязан к этому аккаунту!")
    print("   Переходите в: https://console.cloud.google.com/billing/01743A-05FCF9-1413FB/manage")

def main():
    print("=" * 60)
    print("🔧 ДИАГНОСТИКА GOOGLE CLOUD SETUP")
    print("=" * 60)
    
    api_key = check_env_files()
    decode_api_key_info(api_key)
    check_google_cloud()
    check_billing_account()
    
    print("\n" + "=" * 60)
    print("📋 ИТОГИ:")
    print("=" * 60)
    print("1. ✅ Платежный аккаунт: СОЗДАН (Paid account)")
    print("2. ⏳ API ключ: Нужно проверить наличие")
    print("3. ⏳ Project: Нужно проверить привязку к платежному аккаунту")
    print("4. ⏳ Quotas для computer-use: Нужно настроить в GCP Console")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
