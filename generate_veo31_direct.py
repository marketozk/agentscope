#!/usr/bin/env python3
"""
Генерация видео с Veo 3.1 через прямое API Google Generative AI
Использует google-genai SDK
"""
import os
import asyncio
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

async def generate_veo_video_direct():
    """Генерация видео напрямую через Google Generative AI API"""
    
    print("=" * 80)
    print("🎬 ГЕНЕРАЦИЯ ВИДЕО С VEO 3.1 (Direct API)")
    print("=" * 80)
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY не найден в .env")
        return False
    
    print(f"✅ API ключ найден: {api_key[:30]}...{api_key[-10:]}\n")
    
    # Создаем директорию для видео
    output_dir = Path("veo_videos")
    output_dir.mkdir(exist_ok=True)
    
    # Промпт для видео
    prompt = """
    A stunning time-lapse of a modern city skyline transitioning from day to night.
    The sun sets painting the sky in orange and purple hues.
    Lights gradually turn on in skyscrapers and streets.
    Traffic flows smoothly creating light trails.
    Stars begin to appear in the darkening sky.
    Smooth cinematic camera movement, photorealistic, 4K quality.
    Duration: 5-8 seconds.
    """
    
    print("📝 Промпт для видео:")
    print(prompt.strip())
    print()
    
    try:
        # Импортируем google-genai (новый SDK)
        from google import genai
        from google.genai import types
        
        print("🔧 Инициализация Google Generative AI Client...")
        client = genai.Client(api_key=api_key)
        
        print("🚀 Запуск генерации с моделью veo-3.1-generate-preview...")
        print("⏳ Ожидание генерации (это может занять 5-10 минут)...\n")
        
        # Конфигурация видео (правильное название)
        config = types.GenerateVideosConfig(
            aspect_ratio="16:9",
            resolution="1080p",
        )
        
        # Запускаем генерацию (асинхронная операция)
        operation = client.models.generate_videos(
            model='veo-3.1-generate-preview',
            prompt=prompt,
            config=config,
        )
        
        print(f"✅ Операция запущена: {operation.name}")
        
        # Ждем завершения
        check_count = 0
        start_time = time.time()
        
        while not operation.done:
            check_count += 1
            elapsed = int(time.time() - start_time)
            print(f"⏳ Проверка #{check_count} ({elapsed}с): Генерация продолжается...")
            
            await asyncio.sleep(10)
            
            # Обновляем статус операции
            operation = client.operations.get(name=operation.name)
        
        elapsed_total = int(time.time() - start_time)
        print(f"\n✅ Генерация завершена за {elapsed_total} секунд!")
        
        # Проверяем результат
        if not hasattr(operation, 'response') or not operation.response:
            print("❌ Ошибка: Нет ответа от сервера")
            if hasattr(operation, 'error'):
                print(f"Ошибка операции: {operation.error}")
            return False
        
        response = operation.response
        
        # Получаем сгенерированные видео
        if not hasattr(response, 'generated_videos'):
            print("❌ Ошибка: Нет видео в ответе")
            print(f"Response содержит: {dir(response)}")
            return False
        
        videos = response.generated_videos
        if not videos:
            print("❌ Ошибка: Пустой список видео")
            return False
        
        print(f"📦 Получено видео: {len(videos)} файл(ов)\n")
        
        # Сохраняем видео
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for idx, video_obj in enumerate(videos):
            # Получаем файл видео
            if not hasattr(video_obj, 'video'):
                print(f"⚠️ Видео #{idx + 1}: Нет атрибута 'video'")
                continue
            
            video_file = video_obj.video
            
            print(f"💾 Скачивание видео #{idx + 1}...")
            
            # Скачиваем файл
            video_data = client.files.download(file=video_file)
            
            # Сохраняем
            output_path = output_dir / f"veo31_city_{timestamp}_{idx + 1}.mp4"
            
            with open(output_path, 'wb') as f:
                f.write(video_data)
            
            file_size_mb = len(video_data) / (1024 * 1024)
            print(f"✅ Видео сохранено: {output_path}")
            print(f"📊 Размер: {file_size_mb:.2f} МБ\n")
        
        print("=" * 80)
        print("🎉 ВИДЕО УСПЕШНО СОЗДАНО!")
        print("=" * 80)
        print(f"📁 Папка с видео: {output_dir.absolute()}")
        print(f"🎬 Всего видео: {len(videos)}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("\n📦 Установите: pip install google-genai")
        return False
        
    except Exception as e:
        print(f"\n❌ Ошибка генерации: {e}")
        print(f"📌 Тип ошибки: {type(e).__name__}")
        
        # Детальная информация
        import traceback
        print("\n🔍 Полная трассировка:")
        traceback.print_exc()
        
        # Подсказки по типу ошибки
        error_str = str(e).lower()
        
        if "permission" in error_str or "403" in error_str:
            print("\n💡 Проблема с доступом:")
            print("   • Veo 3.1 может требовать специального доступа")
            print("   • Проверьте что ваш проект whitelisted для Veo")
            print("   • Попробуйте модель veo-3.0-generate-001")
            
        elif "quota" in error_str or "429" in error_str:
            print("\n💡 Превышена квота:")
            print("   • Veo имеет строгие лимиты генерации")
            print("   • Подождите несколько минут и попробуйте снова")
            
        elif "not found" in error_str or "404" in error_str:
            print("\n💡 Модель не найдена:")
            print("   • veo-3.1-generate-preview может быть недоступна")
            print("   • Попробуйте veo-3.0-generate-001")
            
        return False

if __name__ == "__main__":
    print("\n🎬 Veo 3.1 Video Generator (Direct API)")
    print("=" * 80)
    
    success = asyncio.run(generate_veo_video_direct())
    
    if success:
        print("\n✅ Программа успешно завершена")
        print("🎬 Откройте папку veo_videos/ чтобы увидеть результат")
    else:
        print("\n❌ Возникли проблемы при генерации")
        print("\n💡 Альтернативы:")
        print("   • Используйте veo-3.0-generate-001 вместо veo-3.1")
        print("   • Проверьте доступ к Veo через Google AI Studio")
        print("   • Убедитесь что API ключ имеет права на Veo")
