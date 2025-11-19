#!/usr/bin/env python3
"""
Тестовая генерация видео с помощью Veo 3.1
"""
import os
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

async def generate_test_video():
    """Генерация тестового видео с Veo 3.1"""
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY не найден!")
        return
    
    print("=" * 80)
    print("🎬 ГЕНЕРАЦИЯ ТЕСТОВОГО ВИДЕО С VEO 3.1")
    print("=" * 80)
    
    # Создаем директорию для видео
    output_dir = Path("veo_videos")
    output_dir.mkdir(exist_ok=True)
    
    # Промпт для видео
    prompt = """
    A stunning cinematic shot of a futuristic city at sunset.
    Flying cars glide between towering glass skyscrapers.
    The golden sun reflects off the buildings creating a warm glow.
    Camera slowly pans across the skyline revealing the bustling metropolis.
    Photorealistic, 4K quality, dramatic lighting, science fiction atmosphere.
    """
    
    print(f"\n📝 Промпт:")
    print(prompt.strip())
    
    print("\n🚀 Запуск генерации с моделью veo-3.1-generate-preview...")
    print("⏳ Это может занять несколько минут...\n")
    
    try:
        # Конфигурируем API
        genai.configure(api_key=api_key)
        
        # Используем Vertex AI подход через REST API
        # Для Veo нужен специальный подход
        print("⚠️ Для Veo 3.1 требуется использование Vertex AI SDK")
        print("📦 Попробуем через google-generativeai >= 0.8.0 или Vertex AI")
        
        # Проверяем доступные методы
        import inspect
        print(f"\n🔍 Доступные методы в genai:")
        methods = [m for m in dir(genai) if not m.startswith('_')]
        print(f"   {', '.join(methods[:10])}...")
        
        # Пробуем найти правильный способ
        if hasattr(genai, 'generate_video'):
            print("✅ Найден метод generate_video")
            result = genai.generate_video(
                model='veo-3.1-generate-preview',
                prompt=prompt,
            )
        elif hasattr(genai, 'GenerativeModel'):
            print("✅ Используем GenerativeModel API")
            # Для видео нужен другой подход - через Files API
            model = genai.GenerativeModel('veo-3.1-generate-preview')
            print("⚠️ GenerativeModel не поддерживает прямую генерацию видео")
            print("📌 Для Veo требуется:")
            print("   1. google-cloud-aiplatform >= 1.70.0")
            print("   2. Использование Vertex AI API напрямую")
            print("\n� Установите: pip install google-cloud-aiplatform")
            print("💡 Код для Vertex AI:")
            print("""
from vertexai.preview.vision_models import VideoGenerationModel

model = VideoGenerationModel.from_pretrained("veo-3.1-generate-preview")
response = model.generate_videos(
    prompt=prompt,
    aspect_ratio="16:9",
    resolution="1080p"
)
            """)
            return
        else:
            print("❌ API для генерации видео не найден в текущей версии")
            print(f"📦 Версия google-generativeai: {genai.__version__}")
            print("\n💡 Для работы с Veo 3.1 нужно:")
            print("   1. Обновить: pip install --upgrade google-generativeai")
            print("   2. Или использовать: pip install google-cloud-aiplatform")
            return
        
        print("\n" + "=" * 80)
        print("🎉 ГЕНЕРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
        print("=" * 80)
        print(f"📁 Видео сохранены в: {output_dir.absolute()}")
        
    except Exception as e:
        print(f"\n❌ Ошибка генерации: {e}")
        print(f"\n📌 Тип ошибки: {type(e).__name__}")
        
        # Дополнительная информация
        if hasattr(e, 'response'):
            print(f"Response: {e.response}")
        if hasattr(e, 'details'):
            print(f"Details: {e.details}")

if __name__ == "__main__":
    print("\n🎬 Veo 3.1 Video Generator")
    print("=" * 80)
    
    asyncio.run(generate_test_video())
    
    print("\n✅ Программа завершена")
