"""
Демонстрация интеллектуального агента с анализом интерфейса
"""
import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.intelligent_agent_new import IntelligentRegistrationAgent

async def demo_interface_analysis():
    """Демонстрация анализа интерфейса"""
    
    # ВАЖНО: Вставьте сюда ваш Gemini API ключ
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
    
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("❌ Необходимо указать Gemini API ключ в переменной GEMINI_API_KEY")
        print("Получить ключ можно здесь: https://makersuite.google.com/app/apikey")
        return
    
    # Создаем агента
    agent = IntelligentRegistrationAgent(GEMINI_API_KEY)
    
    # Собираем данные пользователя
    print("🔧 Настройка данных пользователя...")
    await agent.collect_user_data()
    
    # Список сайтов для тестирования
    test_sites = [
        "https://example.com/register",  # Замените на реальный URL
        "https://httpbin.org/forms/post",  # Тестовая форма
    ]
    
    print("\n🚀 Начинаю демонстрацию интеллектуального анализа интерфейса...")
    
    for site_url in test_sites:
        print(f"\n{'='*60}")
        print(f"🌐 Тестирую сайт: {site_url}")
        print(f"{'='*60}")
        
        try:
            # Запускаем интеллектуальную регистрацию
            success = await agent.execute(site_url)
            
            if success:
                print(f"✅ Регистрация на {site_url} завершена успешно!")
            else:
                print(f"❌ Регистрация на {site_url} не удалась")
            
            # Получаем отчет
            report = agent.get_registration_report()
            
            print(f"\n📊 Отчет о регистрации:")
            print(f"  📍 Всего шагов: {report['total_steps']}")
            print(f"  ✅ Успешных: {report['successful_steps']}")
            print(f"  ❌ Неудачных: {report['failed_steps']}")
            print(f"  📈 Успешность: {report['success_rate']:.1%}")
            print(f"  🌐 Типы страниц: {', '.join(report['pages_visited'])}")
            
            interface_summary = report['interface_summary']
            print(f"\n🧠 Сводка по интерфейсу:")
            print(f"  🔄 Успешных действий: {interface_summary['successful_actions']}")
            print(f"  ❌ Неудачных действий: {interface_summary['failed_actions']}")
            print(f"  📝 Запомненных паттернов: {interface_summary['remembered_patterns']}")
            
            if interface_summary['last_errors']:
                print(f"  🚨 Последние ошибки: {interface_summary['last_errors']}")
                
        except Exception as e:
            print(f"❌ Ошибка при тестировании {site_url}: {e}")
        
        # Пауза между сайтами
        print("\n⏸️ Пауза перед следующим сайтом...")
        await asyncio.sleep(3)
    
    print(f"\n{'='*60}")
    print("🏁 Демонстрация завершена!")
    print(f"{'='*60}")

async def demo_interface_analysis_manual():
    """Демонстрация с ручным вводом URL"""
    
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
    
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("❌ Необходимо указать Gemini API ключ в переменной GEMINI_API_KEY")
        return
    
    agent = IntelligentRegistrationAgent(GEMINI_API_KEY)
    
    print("🤖 Интеллектуальный агент с анализом интерфейса")
    print("=" * 50)
    
    # Сбор данных пользователя
    await agent.collect_user_data()
    
    while True:
        print("\n🌐 Введите URL для анализа и регистрации:")
        print("(или 'quit' для выхода)")
        
        url = input("URL: ").strip()
        
        if url.lower() in ['quit', 'exit', 'q']:
            break
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        print(f"\n🔍 Анализирую интерфейс: {url}")
        
        try:
            success = await agent.execute(url)
            
            if success:
                print("🎉 Процесс завершен успешно!")
            else:
                print("⚠️ Процесс завершился с ошибками")
            
            # Показываем детальный отчет
            report = agent.get_registration_report()
            
            print(f"\n📋 Детальный отчет:")
            for i, step in enumerate(report['steps_detail'], 1):
                action_desc = step['action'].get('description', step['action'].get('action'))
                result_status = "✅" if step['result'].success else "❌"
                print(f"  {i}. {result_status} {action_desc}")
                if not step['result'].success and step['result'].errors:
                    print(f"     Ошибка: {step['result'].errors[0]}")
                    
        except KeyboardInterrupt:
            print("\n⏸️ Прервано пользователем")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    print("\n👋 До свидания!")

if __name__ == "__main__":
    print("🤖 Демонстрация интеллектуального агента с анализом интерфейса")
    print("\nВыберите режим:")
    print("1. Автоматическое тестирование")
    print("2. Ручной ввод URL")
    
    choice = input("Введите номер (1 или 2): ").strip()
    
    if choice == "1":
        asyncio.run(demo_interface_analysis())
    elif choice == "2":
        asyncio.run(demo_interface_analysis_manual())
    else:
        print("❌ Неверный выбор")
