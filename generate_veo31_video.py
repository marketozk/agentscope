#!/usr/bin/env python3
"""
Генерация тестового видео с помощью Veo 3.1 через Vertex AI
"""
import os
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

async def generate_veo31_video():
    """Генерация видео с Veo 3.1"""
    
    print("=" * 80)
    print("🎬 ГЕНЕРАЦИЯ ВИДЕО С VEO 3.1")
    print("=" * 80)
    
    # Создаем директорию для видео
    output_dir = Path("veo_videos")
    output_dir.mkdir(exist_ok=True)
    
    # Промпт для видео
    prompt = """
    A breathtaking aerial view of a futuristic cyberpunk city at night.
    Neon lights in pink, blue and purple illuminate towering skyscrapers.
    Flying vehicles with glowing trails weave between buildings.
    Rain falls creating reflections on wet surfaces below.
    The camera slowly rotates revealing the vast cityscape.
    Cinematic, photorealistic, blade runner atmosphere, 4K quality.
    """
    
    print(f"\n📝 Промпт для видео:")
    print(prompt.strip())
    print()
    
    try:
        # Инициализируем Vertex AI
        import vertexai
        from vertexai.preview.vision_models import VideoGenerationModel
        
        # Получаем project_id из переменных окружения или используем дефолтный
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0004253759")
        location = "us-central1"  # Регион где доступен Veo
        
        print(f"🔧 Инициализация Vertex AI:")
        print(f"   Project: {project_id}")
        print(f"   Location: {location}")
        
        vertexai.init(project=project_id, location=location)
        
        print("\n🚀 Загрузка модели veo-3.1-generate-preview...")
        model = VideoGenerationModel.from_pretrained("veo-3.1-generate-preview")
        
        print("⏳ Запуск генерации видео...")
        print("   Это может занять 5-10 минут...\n")
        
        # Генерируем видео
        response = model.generate_videos(
            prompt=prompt,
            aspect_ratio="16:9",  # Широкоформатное
            resolution="1080p",    # Full HD
        )
        
        print("✅ Генерация завершена!")
        
        # Сохраняем видео
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for idx, video in enumerate(response):
            output_path = output_dir / f"veo31_cyberpunk_{timestamp}_{idx + 1}.mp4"
            
            print(f"\n💾 Сохранение видео #{idx + 1}...")
            
            # Получаем данные видео
            video_data = video.video_bytes
            
            # Сохраняем в файл
            with open(output_path, 'wb') as f:
                f.write(video_data)
            
            file_size_mb = len(video_data) / (1024 * 1024)
            print(f"✅ Видео сохранено: {output_path}")
            print(f"📊 Размер: {file_size_mb:.2f} МБ")
        
        print("\n" + "=" * 80)
        print("🎉 ВИДЕО УСПЕШНО СОЗДАНО!")
        print("=" * 80)
        print(f"📁 Папка с видео: {output_dir.absolute()}")
        print(f"🎬 Всего видео: {len(response)}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("\n📦 Убедитесь, что установлены пакеты:")
        print("   pip install google-cloud-aiplatform")
        return False
        
    except Exception as e:
        print(f"\n❌ Ошибка генерации: {e}")
        print(f"📌 Тип ошибки: {type(e).__name__}")
        
        # Детальная информация об ошибке
        if "permission" in str(e).lower() or "credentials" in str(e).lower():
            print("\n💡 Проблема с доступом:")
            print("   1. Убедитесь что у вас настроены Application Default Credentials")
            print("   2. Запустите: gcloud auth application-default login")
            print("   3. Или установите GOOGLE_APPLICATION_CREDENTIALS с путем к JSON ключу")
            
        elif "quota" in str(e).lower():
            print("\n💡 Превышена квота:")
            print("   Veo 3.1 имеет ограничения на количество генераций")
            print("   Попробуйте позже или используйте другую модель")
            
        elif "not found" in str(e).lower() or "does not exist" in str(e).lower():
            print("\n💡 Проект или модель не найдены:")
            print("   1. Проверьте GOOGLE_CLOUD_PROJECT в .env")
            print("   2. Убедитесь что Vertex AI API включен в проекте")
            print("   3. Проверьте доступ к Veo 3.1 в вашем регионе")
            
        else:
            print("\n💡 Общие рекомендации:")
            print("   1. Проверьте настройки GCP проекта")
            print("   2. Убедитесь что Vertex AI API включен")
            print("   3. Проверьте доступ к Veo в us-central1")
        
        return False

if __name__ == "__main__":
    print("\n🎬 Veo 3.1 Video Generator (Vertex AI)")
    print("=" * 80)
    
    success = asyncio.run(generate_veo31_video())
    
    if success:
        print("\n✅ Программа успешно завершена")
    else:
        print("\n❌ Возникли проблемы при генерации")
