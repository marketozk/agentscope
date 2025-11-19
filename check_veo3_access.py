#!/usr/bin/env python3
"""
Проверка доступа к Veo3 и анализ использования GEMINI_API_KEY в проекте
"""
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')

print("=" * 80)
print("🔍 АНАЛИЗ ИСПОЛЬЗОВАНИЯ GEMINI API В ПРОЕКТЕ")
print("=" * 80)

# Проверка наличия ключа
if not api_key:
    print("\n❌ GEMINI_API_KEY не найден в переменных окружения!")
    print("📁 Убедитесь, что файл .env существует и содержит GEMINI_API_KEY=...")
else:
    print(f"\n✅ API ключ найден: {api_key[:30]}...{api_key[-10:]}")

# Анализ файлов, использующих GEMINI_API_KEY
print("\n" + "=" * 80)
print("📂 ФАЙЛЫ, ИСПОЛЬЗУЮЩИЕ GEMINI_API_KEY:")
print("=" * 80)

files_using_key = {
    "main.py": "Основной файл запуска системы регистрации (загрузка конфига)",
    "src/registration_orchestrator.py": "Координатор регистрации (предположительно)",
    "src/page_analyzer_agent.py": "Агент анализа страниц с помощью Gemini",
    "src/element_finder_agent.py": "Агент поиска элементов (возможно с AI)",
    "check_api_project.py": "Проверка подключения к Google Generative AI",
    "check_gcp_project.py": "Проверка проекта Google Cloud Platform",
    "Browser_Use/*": "Браузерная автоматизация (использует gemini-2.5-computer-use)",
    "WhatsApp/*": "WhatsApp интеграция (использует gemini-2.5-computer-use)",
}

for file_path, description in files_using_key.items():
    print(f"  • {file_path:40} → {description}")

# Проверка доступа к API
print("\n" + "=" * 80)
print("🔗 ПРОВЕРКА ДОСТУПА К GEMINI API")
print("=" * 80)

if not api_key:
    print("❌ Пропускаем проверку - нет API ключа")
else:
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        print("\n🔄 Получение списка доступных моделей...")
        models = list(genai.list_models())
        
        if models:
            print(f"✅ Подключение успешно! Доступно {len(models)} моделей")
            
            # Ищем модели для генерации видео
            video_models = [m for m in models if 'veo' in m.name.lower() or 'video' in m.name.lower()]
            image_models = [m for m in models if 'imagen' in m.name.lower() or 'image' in m.name.lower()]
            gemini_models = [m for m in models if 'gemini' in m.name.lower()]
            
            print(f"\n📊 Статистика по типам моделей:")
            print(f"  • Gemini модели: {len(gemini_models)}")
            print(f"  • Image модели: {len(image_models)}")
            print(f"  • Video модели (Veo): {len(video_models)}")
            
            # Проверяем Veo3 специально
            print("\n" + "=" * 80)
            print("🎬 ПРОВЕРКА ДОСТУПА К VEO3")
            print("=" * 80)
            
            veo3_models = [m for m in models if 'veo-3' in m.name.lower() or m.name == 'veo-3.0-generate-001']
            
            if veo3_models:
                print(f"✅ VEO3 ДОСТУПЕН! Найдено {len(veo3_models)} моделей:")
                for model in veo3_models:
                    print(f"  • {model.name}")
                    print(f"    - Display name: {model.display_name}")
                    print(f"    - Description: {model.description[:100]}...")
                    print(f"    - Supported generation methods: {model.supported_generation_methods}")
                    print()
            else:
                print("❌ VEO3 НЕ ДОСТУПЕН в текущем проекте")
                print("\n📌 Возможные причины:")
                print("  1. Veo3 еще не доступен в вашем регионе")
                print("  2. Требуется особый доступ (waitlist/whitelist)")
                print("  3. API ключ привязан к проекту без доступа к Veo")
                print("\n💡 Используемые модели в проекте:")
                print("  • browser-use-repo/examples/apps/ad-use/ использует veo-3.0-generate-001")
                print("  • Это может не работать без специального доступа")
            
            # Показываем все доступные Gemini модели
            print("\n" + "=" * 80)
            print("🤖 ДОСТУПНЫЕ GEMINI МОДЕЛИ:")
            print("=" * 80)
            
            for i, model in enumerate(gemini_models[:10], 1):
                print(f"{i:2}. {model.name:60} | {model.display_name}")
            
            if len(gemini_models) > 10:
                print(f"    ... и еще {len(gemini_models) - 10} моделей")
            
        else:
            print("⚠️ API работает, но моделей не найдено")
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        print("\n📌 Возможные причины:")
        print("  1. API ключ неверный или истёк")
        print("  2. Generative Language API не включена")
        print("  3. Нет доступа к биллингу в проекте")

# Информация о Veo3 в проекте
print("\n" + "=" * 80)
print("📁 VEO3 В ВАШЕМ ПРОЕКТЕ:")
print("=" * 80)

veo_files = [
    "browser-use-repo/examples/apps/ad-use/ad_generator.py",
    "browser-use-repo/examples/apps/ad-use/README.md",
    "browser-use-repo/docs/examples/apps/ad-use.mdx",
]

print("\nVeo3 упоминается в следующих файлах:")
for file in veo_files:
    full_path = Path(file)
    if full_path.exists():
        print(f"  ✅ {file}")
    else:
        print(f"  ⚠️  {file} (не найден)")

print("\n📌 Основной файл с Veo3:")
print("  • browser-use-repo/examples/apps/ad-use/ad_generator.py")
print("  • Функция: generate_ad_video()")
print("  • Модель: veo-3.0-generate-001")
print("  • Назначение: Генерация TikTok видео-рекламы")

print("\n" + "=" * 80)
print("📝 РЕКОМЕНДАЦИИ:")
print("=" * 80)
print("1. Если Veo3 недоступен - подайте заявку на доступ через Google AI Studio")
print("2. Используйте gemini-2.5-computer-use для браузерной автоматизации")
print("3. Проверьте, что Billing включен в вашем GCP проекте")
print("4. API ключ должен быть из проекта с включенным Vertex AI API")
print("=" * 80)
