"""
🚀 Быстрый запуск анализа WhatsApp скриншота
"""

from analyze_whatsapp_screenshot import WhatsAppAnalyzer
from pathlib import Path


def main():
    print("\n" + "="*70)
    print("🤖 WhatsApp Screenshot Analyzer - Быстрый запуск")
    print("="*70 + "\n")
    
    # Инициализация анализатора
    try:
        analyzer = WhatsAppAnalyzer()
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        print("\n💡 Проверьте:")
        print("   1. Наличие GOOGLE_API_KEY в .env файле")
        print("   2. Установлен ли пакет: pip install google-genai>=0.3.0")
        return
    
    # Параметры анализа
    # ВАЖНО: Замените на путь к вашему скриншоту!
    screenshot_file = "whatsapp_main.jpg"  # Имя файла в папке screenshots/
    target_chat = "Т В"  # Имя чата из скриншота
    
    # Полный путь к скриншоту
    screenshot_path = Path(__file__).parent / "screenshots" / screenshot_file
    
    # Проверка наличия файла
    if not screenshot_path.exists():
        print(f"❌ Скриншот не найден: {screenshot_path}")
        print(f"\n📋 Инструкция:")
        print(f"   1. Сделайте скриншот WhatsApp на телефоне")
        print(f"   2. Перенесите файл в папку: {screenshot_path.parent}")
        print(f"   3. Переименуйте в: {screenshot_file}")
        print(f"   4. Или измените переменную screenshot_file в этом файле")
        print(f"\n📂 Текущие файлы в screenshots/:")
        
        screenshots_dir = Path(__file__).parent / "screenshots"
        if screenshots_dir.exists():
            files = list(screenshots_dir.glob("*"))
            if files:
                for f in files:
                    print(f"   - {f.name}")
            else:
                print("   (папка пуста)")
        else:
            print("   (папка не существует)")
        
        return
    
    print(f"✅ Скриншот найден: {screenshot_file}")
    print(f"💬 Целевой чат: {target_chat}")
    print(f"\n{'─'*70}\n")
    
    # Запуск анализа
    result = analyzer.analyze_screenshot(
        image_path=str(screenshot_path),
        target_chat=target_chat,
        save_log=True
    )
    
    # Результат
    print(f"\n{'='*70}")
    
    if result.get("status") == "success":
        print("✅ АНАЛИЗ ЗАВЕРШЕН УСПЕШНО!")
        print(f"{'='*70}")
        print(f"\n📊 Результаты сохранены:")
        print(f"   📁 Папка: {analyzer.results_dir}")
        print(f"   📄 JSON: analysis_{result['timestamp']}.json")
        print(f"   📝 TXT: analysis_{result['timestamp']}.txt")
        
        # Краткая статистика
        analysis_text = result.get('analysis', '')
        print(f"\n📈 Статистика:")
        print(f"   Длина анализа: {len(analysis_text)} символов")
        print(f"   Строк: {analysis_text.count(chr(10)) + 1}")
        
    else:
        print("❌ АНАЛИЗ ЗАВЕРШИЛСЯ С ОШИБКОЙ")
        print(f"{'='*70}")
        if "error" in result:
            print(f"\n⚠️  Ошибка: {result['error']}")
        
        print(f"\n💡 Возможные причины:")
        print(f"   1. Недействительный API ключ")
        print(f"   2. Проблемы с подключением к интернету")
        print(f"   3. Квота API исчерпана")
        print(f"   4. Неподдерживаемый формат изображения")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
