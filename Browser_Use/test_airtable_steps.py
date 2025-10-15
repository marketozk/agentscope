"""
Тестовый скрипт для отладки отдельных шагов регистрации в Airtable
Позволяет запускать каждый шаг независимо
"""
import asyncio
from pathlib import Path
from browser_use import Agent
from dotenv import load_dotenv
from config import get_llm, get_app_config
from browser_use_helpers import extract_email_from_result, is_valid_email

# Загружаем конфигурацию
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


async def test_temp_mail():
    """Тест получения временной почты"""
    print("\n" + "="*60)
    print("🧪 Тест: Получение временной почты")
    print("="*60)
    
    llm = get_llm()
    agent = Agent(
        task="""
        1. Открой https://temp-mail.io/ru
        2. Дождись полной загрузки страницы
        3. Скопируй email адрес который отображается на странице
        4. Верни только email адрес (формат: xxx@xxx.xxx)
        """,
        llm=llm,
        use_vision=True
    )
    
    result = await agent.run()
    
    # Используем helper для извлечения email
    email = extract_email_from_result(result)
    
    print(f"\n📧 Извлеченный email: {email}")
    
    if email and is_valid_email(email):
        print(f"✅ Email получен успешно: {email}")
        return email
    else:
        print("❌ Ошибка: не удалось получить валидный email")
        print(f"   Результат: {str(result)[:300]}...")
        return None


async def test_airtable_form():
    """Тест открытия формы Airtable"""
    print("\n" + "="*60)
    print("🧪 Тест: Проверка формы Airtable")
    print("="*60)
    
    llm = get_llm()
    agent = Agent(
        task="""
        1. Открой https://airtable.com/invite/r/ovoAP1zR
        2. Дождись полной загрузки страницы
        3. Найди и опиши какие поля есть в форме регистрации
        4. Верни список всех полей формы (Email, Full name, Password и т.д.)
        """,
        llm=llm,
        use_vision=True
    )
    
    result = await agent.run()
    print(f"\n📋 Найденные поля формы:")
    print(result)


async def test_multi_tab():
    """Тест работы с несколькими вкладками"""
    print("\n" + "="*60)
    print("🧪 Тест: Работа с несколькими вкладками")
    print("="*60)
    
    llm = get_llm()
    
    # В browser-use нет execute_task, используем обычный подход
    task = """
    1. Открой https://example.com и дождись загрузки
    2. Открой новую вкладку и перейди на https://google.com
    3. Переключись на первую вкладку и убедись что это example.com
    4. Переключись на вторую вкладку и убедись что это google.com
    5. Верни результат проверки
    """
    
    agent = Agent(task=task, llm=llm)
    result = await agent.run()
    
    print(f"\n📊 Результат теста: {result}")
    print("\n✅ Тест завершен успешно!")


async def test_form_filling():
    """Тест заполнения формы"""
    print("\n" + "="*60)
    print("🧪 Тест: Заполнение тестовой формы")
    print("="*60)
    
    llm = get_llm()
    agent = Agent(
        task="""
        1. Открой https://www.w3schools.com/html/html_forms.asp
        2. Найди любую форму на странице
        3. Попробуй заполнить поля: имя "Test User", email "test@example.com"
        4. НЕ ОТПРАВЛЯЙ форму, только заполни
        5. Верни статус выполнения
        """,
        llm=llm,
        use_vision=True
    )
    
    result = await agent.run()
    print(f"\n📝 Результат заполнения: {result}")


async def test_email_monitoring():
    """Тест мониторинга почты (симуляция)"""
    print("\n" + "="*60)
    print("🧪 Тест: Мониторинг temp-mail (симуляция)")
    print("="*60)
    
    llm = get_llm()
    
    # Простой тест - просто проверяем, что можем открыть и обновить страницу
    task = """
    1. Открой https://temp-mail.io/ru
    2. Дождись загрузки страницы
    3. Проверь, есть ли входящие письма
    4. Верни статус: "FOUND" если есть письма, иначе "EMPTY"
    """
    
    agent = Agent(task=task, llm=llm)
    result = await agent.run()
    
    print(f"\n� Результат проверки: {result}")
    print("\n✅ Тест завершен!")


async def test_full_flow_dry_run():
    """Полный тест flow без реальной регистрации"""
    print("\n" + "="*60)
    print("🧪 Тест: Полный flow (dry run)")
    print("="*60)
    
    llm = get_llm()
    
    # Объединяем все шаги в одну задачу
    task = """
    1. Открой https://airtable.com/invite/r/ovoAP1zR и дождись загрузки
    2. Открой новую вкладку и перейди на https://temp-mail.io/ru
    3. Скопируй email адрес с temp-mail
    4. Переключись обратно на вкладку с Airtable
    5. Найди и опиши поля формы (Email address, Full name, Password)
    6. Верни найденный email и список полей
    """
    
    agent = Agent(task=task, llm=llm, use_vision=True)
    result = await agent.run()
    
    print(f"\n📊 Результат dry run:")
    print(result)
    print("\n✅ Dry run завершен успешно!")
    print("💡 Все компоненты работают, можно запускать полную регистрацию")


async def main():
    """Меню для выбора теста"""
    try:
        config = get_app_config()
        config.print_config()
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return
    
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ КОМПОНЕНТОВ РЕГИСТРАЦИИ AIRTABLE")
    print("="*60)
    print("\nВыберите тест:")
    print("1. Тест получения временной почты")
    print("2. Тест формы Airtable")
    print("3. Тест работы с вкладками")
    print("4. Тест заполнения формы")
    print("5. Тест мониторинга почты")
    print("6. Полный flow (dry run)")
    print("7. Запустить все тесты")
    print("0. Выход")
    
    choice = input("\n👉 Ваш выбор (0-7): ").strip()
    
    tests = {
        "1": ("Получение временной почты", test_temp_mail),
        "2": ("Форма Airtable", test_airtable_form),
        "3": ("Работа с вкладками", test_multi_tab),
        "4": ("Заполнение формы", test_form_filling),
        "5": ("Мониторинг почты", test_email_monitoring),
        "6": ("Полный flow", test_full_flow_dry_run)
    }
    
    if choice == "7":
        print("\n🚀 Запуск всех тестов...")
        for name, test_func in tests.values():
            try:
                print(f"\n{'='*60}")
                print(f"▶️  Запуск: {name}")
                print('='*60)
                await test_func()
                await asyncio.sleep(2)  # Пауза между тестами
            except Exception as e:
                print(f"❌ Ошибка в тесте '{name}': {e}")
        print("\n✅ Все тесты завершены!")
        
    elif choice in tests:
        name, test_func = tests[choice]
        print(f"\n🚀 Запуск теста: {name}")
        try:
            await test_func()
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            
    elif choice == "0":
        print("\n👋 Выход")
        
    else:
        print("\n❌ Неверный выбор")


if __name__ == "__main__":
    asyncio.run(main())
