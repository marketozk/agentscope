"""
Демонстрация возможностей анализа интерфейса
"""
import asyncio
import os
from src.intelligent_agent import IntelligentRegistrationAgent

async def demo_interface_analysis():
    """Демонстрация анализа интерфейса"""
    print("🚀 Демонстрация анализа веб-интерфейса")
    print("=" * 50)
    
    # Получаем API ключ
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Не найден GOOGLE_API_KEY или GEMINI_API_KEY в переменных окружения")
        print("Проверьте файл .env")
        return
    
    # Создаем агента
    agent = IntelligentRegistrationAgent(api_key)
    
    # Примеры URL для тестирования
    test_urls = [
        "https://example.com/register",
        "https://httpbin.org/forms/post",
        "https://www.google.com/accounts/signup",
    ]
    
    print("Выберите URL для анализа:")
    for i, url in enumerate(test_urls, 1):
        print(f"{i}. {url}")
    print("4. Ввести свой URL")
    
    try:
        choice = input("\nВведите номер варианта (1-4): ").strip()
        
        if choice == "4":
            url = input("Введите URL: ").strip()
        elif choice in ["1", "2", "3"]:
            url = test_urls[int(choice) - 1]
        else:
            print("❌ Неверный выбор")
            return
        
        print(f"\n🔍 Анализируем интерфейс: {url}")
        print("-" * 50)
        
        # Выполняем анализ
        success = await agent.execute(url)
        
        if success:
            print("\n✅ Анализ завершен успешно!")
        else:
            print("\n❌ Анализ завершен с ошибками")
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Остановлено пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

def main():
    """Главная функция"""
    asyncio.run(demo_interface_analysis())

if __name__ == "__main__":
    main()
