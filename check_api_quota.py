#!/usr/bin/env python3
"""
Простая проверка квоты API на разных моделях Gemini
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def check_quota_on_models():
    """Проверяем квоту на разных моделях"""
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY не найден")
        return
    
    print("=" * 80)
    print("🔍 ПРОВЕРКА КВОТЫ API НА РАЗНЫХ МОДЕЛЯХ")
    print("=" * 80)
    print(f"✅ API ключ: {api_key[:30]}...{api_key[-10:]}\n")
    
    genai.configure(api_key=api_key)
    
    # Модели для тестирования
    test_models = [
        "gemini-2.0-flash-exp",
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]
    
    prompt = "Say 'Hello' in one word only."
    
    for model_name in test_models:
        print(f"📡 Тестирование модели: {model_name}")
        
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            print(f"   ✅ Успешно! Ответ: {response.text.strip()}")
            
            # Проверяем usage metadata
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                print(f"   📊 Токены: prompt={usage.prompt_token_count}, " 
                      f"response={usage.candidates_token_count}, "
                      f"total={usage.total_token_count}")
            
        except Exception as e:
            error_str = str(e)
            
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print(f"   ❌ КВОТА ИСЧЕРПАНА: {error_str[:100]}...")
            elif "403" in error_str:
                print(f"   ❌ НЕТ ДОСТУПА: {error_str[:100]}...")
            elif "404" in error_str:
                print(f"   ⚠️  МОДЕЛЬ НЕ НАЙДЕНА: {model_name}")
            else:
                print(f"   ❌ Ошибка: {error_str[:100]}...")
        
        print()
    
    # Проверяем доступные модели
    print("=" * 80)
    print("📋 СПИСОК ВСЕХ ДОСТУПНЫХ МОДЕЛЕЙ:")
    print("=" * 80)
    
    try:
        models = list(genai.list_models())
        
        # Группируем по типам
        gemini_text = [m for m in models if 'gemini' in m.name.lower() and 'vision' not in m.name.lower()]
        veo_models = [m for m in models if 'veo' in m.name.lower()]
        imagen_models = [m for m in models if 'imagen' in m.name.lower()]
        
        print(f"\n🤖 Gemini текстовые модели ({len(gemini_text)}):")
        for m in gemini_text[:10]:
            print(f"   • {m.name}")
        if len(gemini_text) > 10:
            print(f"   ... и еще {len(gemini_text) - 10}")
        
        print(f"\n🎬 Veo видео модели ({len(veo_models)}):")
        for m in veo_models:
            print(f"   • {m.name}")
            # Показываем методы генерации
            if hasattr(m, 'supported_generation_methods'):
                print(f"     Методы: {m.supported_generation_methods}")
        
        print(f"\n🎨 Imagen модели ({len(imagen_models)}):")
        for m in imagen_models:
            print(f"   • {m.name}")
        
    except Exception as e:
        print(f"❌ Ошибка получения списка моделей: {e}")
    
    print("\n" + "=" * 80)
    print("💡 ИНФОРМАЦИЯ О КВОТАХ:")
    print("=" * 80)
    print("• Free tier Gemini: 15 запросов/минуту, 1500 запросов/день")
    print("• Veo (генерация видео): ОЧЕНЬ ограниченная квота в free tier")
    print("• Veo может требовать оплачиваемый план или специальный доступ")
    print("• Проверьте использование: https://ai.dev/usage?tab=rate-limit")
    print("=" * 80)

if __name__ == "__main__":
    check_quota_on_models()
