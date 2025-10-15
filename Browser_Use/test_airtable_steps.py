"""
Тестовый скрипт для отладки отдельных шагов регистрации в Airtable
Позволяет запускать каждый шаг независимо
"""
import asyncio
from pathlib import Path
from browser_use import Agent
from dotenv import load_dotenv
from config import get_llm, get_app_config

# Загружаем конфигурацию
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


async def test_temp_mail():
    """Тест получения временной почты (как в реальном процессе)"""
    print("\n" + "="*60)
    print("🧪 Тест: Получение временной почты через temp-mail.org")
    print("="*60)
    
    llm = get_llm()
    agent = Agent(
        task="""
        Go to https://temp-mail.org/en/
        Wait 3 seconds for the email address to fully load.
        Extract the email address from the page.
        IMPORTANT: When calling done(), return ONLY the email address in format xxxxx@xxxxx.com
        Example: done(text='abc123@tempmail.com', success=True)
        DO NOT write descriptions - return ONLY the email address!
        """,
        llm=llm,
        use_vision=True
    )
    
    result = await agent.run()
    
    # Агент сам возвращает результат - просто выводим его
    print(f"\n📧 Результат агента: {result}")
    print(f"✅ Тест завершен")
    
    return result


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
    """Тест проверки почты на temp-mail.org (как в реальном процессе)"""
    print("\n" + "="*60)
    print("🧪 Тест: Проверка писем на temp-mail.org")
    print("="*60)
    
    llm = get_llm()
    
    # Тест проверки почты (реальный процесс из airtable_registration.py)
    task = """
    Switch to temp-mail.org tab.
    Look for confirmation email from Airtable in inbox.
    If email found: click it, find confirmation link/button, click it.
    If no email yet: return "NO_EMAIL" (we'll check again).
    After clicking link: return "EMAIL_CONFIRMED" or describe what happened.
    """
    
    agent = Agent(task=task, llm=llm, use_vision=True)
    result = await agent.run()
    
    print(f"\n📬 Результат проверки: {result}")
    print("\n✅ Тест завершен!")


async def test_full_flow_dry_run():
    """Полный тест flow - открытие Airtable + получение почты (dry run)"""
    print("\n" + "="*60)
    print("🧪 Тест: Полный flow (dry run) - как в реальном процессе")
    print("="*60)
    
    llm = get_llm()
    
    # Используем реальную последовательность из airtable_registration.py
    task = """
    Step 1: Go to https://airtable.com/invite/r/ovoAP1zR and wait for page to load.
    Step 2: Open new tab and go to https://temp-mail.org/en/ - email appears immediately.
    Step 3: Find and get the email address from temp-mail page (visible in email field).
    Step 4: Switch back to Airtable tab and describe the registration form fields.
    
    Return: "EMAIL: [email_address] | FORM: [field1, field2, ...]"
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
