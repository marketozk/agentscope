"""
Примеры программного использования multi_scenario.py

Этот файл демонстрирует, как использовать сценарии из multi_scenario.py
в ваших собственных скриптах без интерактивного меню.
"""

import asyncio
from multi_scenario import (
    get_llm,
    get_profile_path,
    NewsSearchScenario,
    RegistrationScenario,
    PriceMonitoringScenario,
    WikipediaScenario
)


# ==================== ПРИМЕР 1: Простой запуск сценария ====================

async def example_1_simple_news_search():
    """Простой поиск новостей в режиме единого промпта"""
    
    print("\n" + "="*60)
    print("ПРИМЕР 1: Простой поиск новостей")
    print("="*60 + "\n")
    
    # Инициализация
    llm = get_llm()
    profile_path = get_profile_path()
    
    # Создание и запуск сценария
    scenario = NewsSearchScenario(llm, profile_path)
    result = await scenario.run(
        query="искусственный интеллект",
        mode="single_prompt"
    )
    
    print("\n✅ Результат:", result)


# ==================== ПРИМЕР 2: Пошаговый режим ====================

async def example_2_step_by_step():
    """Пошаговое выполнение задачи"""
    
    print("\n" + "="*60)
    print("ПРИМЕР 2: Пошаговый поиск в Википедии")
    print("="*60 + "\n")
    
    llm = get_llm()
    profile_path = get_profile_path()
    
    scenario = WikipediaScenario(llm, profile_path)
    results = await scenario.run(
        topic="Квантовые компьютеры",
        mode="step_by_step"
    )
    
    print(f"\n✅ Выполнено шагов: {len(results) if isinstance(results, list) else 1}")


# ==================== ПРИМЕР 3: Последовательное выполнение ====================

async def example_3_sequential():
    """Последовательное выполнение нескольких сценариев"""
    
    print("\n" + "="*60)
    print("ПРИМЕР 3: Последовательное выполнение задач")
    print("="*60 + "\n")
    
    llm = get_llm()
    profile_path = get_profile_path()
    
    # Задача 1: Поиск новостей
    print("\n--- Задача 1: Новости ---")
    news_scenario = NewsSearchScenario(llm, profile_path)
    await news_scenario.run("технологии", mode="single_prompt")
    
    # Пауза между задачами
    await asyncio.sleep(3)
    
    # Задача 2: Википедия
    print("\n--- Задача 2: Википедия ---")
    wiki_scenario = WikipediaScenario(llm, profile_path)
    await wiki_scenario.run("Python", mode="single_prompt")
    
    print("\n✅ Все задачи выполнены!")


# ==================== ПРИМЕР 4: Обработка ошибок ====================

async def example_4_error_handling():
    """Пример с обработкой ошибок"""
    
    print("\n" + "="*60)
    print("ПРИМЕР 4: Обработка ошибок")
    print("="*60 + "\n")
    
    try:
        llm = get_llm()
        profile_path = get_profile_path()
        
        scenario = NewsSearchScenario(llm, profile_path)
        result = await scenario.run("тестовый запрос", mode="single_prompt")
        
        print("✅ Успешно!")
        
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()


# ==================== ПРИМЕР 5: Пользовательские данные ====================

async def example_5_custom_data():
    """Регистрация с пользовательскими данными"""
    
    print("\n" + "="*60)
    print("ПРИМЕР 5: Регистрация с пользовательскими данными")
    print("="*60 + "\n")
    
    llm = get_llm()
    profile_path = get_profile_path()
    
    # Подготовка данных пользователя
    user_data = {
        "first_name": "Алексей",
        "last_name": "Смирнов",
        "email": "alexey.smirnov@example.com",
        "mobile": "9171234567",
        "gender": "Male"
    }
    
    scenario = RegistrationScenario(llm, profile_path)
    result = await scenario.run(user_data, mode="single_prompt")
    
    print("\n✅ Форма заполнена!")


# ==================== ПРИМЕР 6: Мониторинг нескольких товаров ====================

async def example_6_multiple_products():
    """Мониторинг цен на несколько товаров"""
    
    print("\n" + "="*60)
    print("ПРИМЕР 6: Мониторинг нескольких товаров")
    print("="*60 + "\n")
    
    llm = get_llm()
    profile_path = get_profile_path()
    
    products = ["iPhone 15", "Samsung Galaxy S24", "Xiaomi 14"]
    
    scenario = PriceMonitoringScenario(llm, profile_path)
    
    for i, product in enumerate(products, 1):
        print(f"\n--- Товар {i}/{len(products)}: {product} ---")
        
        try:
            await scenario.run(product, mode="single_prompt")
            print(f"✅ {product} - цена получена")
        except Exception as e:
            print(f"❌ {product} - ошибка: {e}")
        
        # Пауза между запросами
        if i < len(products):
            await asyncio.sleep(5)
    
    print("\n✅ Мониторинг завершён!")


# ==================== ПРИМЕР 7: Создание собственного сценария ====================

async def example_7_custom_scenario():
    """Создание собственного сценария на основе базового класса"""
    
    from multi_scenario import ScenarioRunner
    
    class CustomScenario(ScenarioRunner):
        """Собственный сценарий: поиск на GitHub"""
        
        async def run(self, repo_name: str, mode: str = "single_prompt"):
            print(f"\n🔧 CUSTOM: Поиск репозитория {repo_name}")
            
            if mode == "single_prompt":
                task = f"""
                1. Открой github.com
                2. Найди репозиторий "{repo_name}"
                3. Открой первый репозиторий из результатов
                4. Прочитай описание репозитория
                5. Посмотри количество звёзд
                """
                return await self.run_single_prompt(task)
            
            elif mode == "step_by_step":
                steps = [
                    "Открой сайт github.com",
                    f"Введи в поиск '{repo_name}'",
                    "Открой первый репозиторий из результатов",
                    "Прочитай описание репозитория",
                    "Найди и прочитай количество звёзд",
                ]
                return await self.run_step_by_step(steps)
    
    print("\n" + "="*60)
    print("ПРИМЕР 7: Собственный сценарий (GitHub)")
    print("="*60 + "\n")
    
    llm = get_llm()
    profile_path = get_profile_path()
    
    scenario = CustomScenario(llm, profile_path)
    await scenario.run("python/cpython", mode="single_prompt")
    
    print("\n✅ Собственный сценарий выполнен!")


# ==================== ГЛАВНОЕ МЕНЮ ПРИМЕРОВ ====================

async def run_examples():
    """Запуск всех примеров"""
    
    print("\n" + "="*70)
    print(" "*20 + "ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ")
    print("="*70)
    
    examples = {
        "1": ("Простой поиск новостей", example_1_simple_news_search),
        "2": ("Пошаговый режим", example_2_step_by_step),
        "3": ("Последовательное выполнение", example_3_sequential),
        "4": ("Обработка ошибок", example_4_error_handling),
        "5": ("Пользовательские данные", example_5_custom_data),
        "6": ("Мониторинг нескольких товаров", example_6_multiple_products),
        "7": ("Собственный сценарий", example_7_custom_scenario),
    }
    
    print("\nДоступные примеры:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  0. Выход")
    print("  all. Запустить все примеры")
    
    choice = input("\n👉 Выберите пример (0-7, all): ").strip().lower()
    
    if choice == "0":
        print("👋 До свидания!")
        return
    
    if choice == "all":
        print("\n🚀 Запуск всех примеров...\n")
        for name, func in examples.values():
            print(f"\n{'='*70}")
            print(f"▶️  {name}")
            print("="*70)
            try:
                await func()
            except Exception as e:
                print(f"\n❌ Ошибка в примере: {e}")
            await asyncio.sleep(2)
        print("\n✅ Все примеры выполнены!")
    
    elif choice in examples:
        name, func = examples[choice]
        print(f"\n🚀 Запуск: {name}\n")
        await func()
    
    else:
        print("❌ Неверный выбор!")


# ==================== ТОЧКА ВХОДА ====================

if __name__ == "__main__":
    try:
        asyncio.run(run_examples())
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
