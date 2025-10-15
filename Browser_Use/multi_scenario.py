"""
Многосценарный скрипт Browser-Use + Gemini

Реализует несколько практических сценариев автоматизации браузера:
1. Поиск новостей на Яндекс
2. Заполнение формы регистрации
3. Мониторинг цен на товар
4. Публикация поста в социальной сети

Поддерживает два режима работы:
- Единый промпт (single_prompt): вся задача в одной инструкции
- Пошаговый (step_by_step): разбиение задачи на отдельные шаги
"""

import asyncio
import os
from pathlib import Path
from browser_use import Agent, Browser, llm as bu_llm
from dotenv import load_dotenv
from datetime import datetime

# Импорт конфигурации с rate limiting
from config import (
    get_app_config,
    get_llm,
    get_profile_path,
    wait_for_rate_limit,
    register_api_request,
    print_api_stats
)

# Загружаем переменные окружения
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


# ==================== КОНФИГУРАЦИЯ ====================

# Эти функции теперь используют централизованную конфигурацию из config.py
# get_llm() - возвращает LLM с учётом выбранной модели
# get_profile_path() - возвращает путь к профилю браузера


# ==================== СЦЕНАРИИ ====================

class ScenarioRunner:
    """Базовый класс для запуска сценариев"""
    
    def __init__(self, llm, profile_path):
        self.llm = llm
        self.profile_path = profile_path
    
    async def run_single_prompt(self, task: str):
        """Режим: единый промпт"""
        print(f"\n{'='*60}")
        print(f"🚀 РЕЖИМ: Единый промпт")
        print(f"📋 ЗАДАЧА: {task}")
        print(f"{'='*60}\n")
        
        # Ожидание если нужно для соблюдения rate limit
        if not await wait_for_rate_limit():
            print("⛔ Достигнут дневной лимит API. Попробуйте позже.")
            return None
        
        agent = Agent(
            task=task,
            llm=self.llm,
            use_vision=False,
        )
        
        # Регистрируем запрос
        register_api_request()
        
        result = await agent.run()
        return result
    
    async def run_step_by_step(self, steps: list):
        """Режим: пошаговое выполнение"""
        print(f"\n{'='*60}")
        print(f"🚀 РЕЖИМ: Пошаговое выполнение")
        print(f"📋 ШАГОВ: {len(steps)}")
        print(f"{'='*60}\n")
        
        results = []
        for i, step in enumerate(steps, 1):
            print(f"\n--- Шаг {i}/{len(steps)} ---")
            print(f"📌 {step}")
            
            # Ожидание если нужно для соблюдения rate limit
            if not await wait_for_rate_limit():
                print("⛔ Достигнут дневной лимит API. Остановка.")
                break
            
            agent = Agent(
                task=step,
                llm=self.llm,
                use_vision=False,
            )
            
            # Регистрируем запрос
            register_api_request()
            
            result = await agent.run()
            results.append(result)
            
            # Небольшая пауза между шагами
            if i < len(steps):
                await asyncio.sleep(2)
        
        return results


# ==================== СЦЕНАРИЙ 1: ПОИСК НОВОСТЕЙ ====================

class NewsSearchScenario(ScenarioRunner):
    """Поиск и извлечение новостей"""
    
    async def run(self, query: str, mode: str = "single_prompt"):
        print(f"\n{'#'*60}")
        print(f"📰 СЦЕНАРИЙ: Поиск новостей")
        print(f"🔍 Запрос: {query}")
        print(f"{'#'*60}")
        
        if mode == "single_prompt":
            task = f"""
            1. Открой yandex.ru/news
            2. Найди новости по запросу "{query}"
            3. Открой первую новость из результатов
            4. Прочитай заголовок и первый абзац новости
            5. Сделай скриншот страницы
            """
            return await self.run_single_prompt(task)
        
        elif mode == "step_by_step":
            steps = [
                "Открой сайт yandex.ru/news",
                f"Введи в поиск новостей запрос '{query}' и нажми Enter",
                "Найди и открой первую новость из результатов поиска",
                "Прочитай заголовок новости и первые два абзаца текста",
            ]
            return await self.run_step_by_step(steps)


# ==================== СЦЕНАРИЙ 2: ФОРМА РЕГИСТРАЦИИ ====================

class RegistrationScenario(ScenarioRunner):
    """Заполнение формы регистрации"""
    
    async def run(self, user_data: dict, mode: str = "single_prompt"):
        print(f"\n{'#'*60}")
        print(f"📝 СЦЕНАРИЙ: Регистрация пользователя")
        print(f"👤 Имя: {user_data.get('name', 'N/A')}")
        print(f"{'#'*60}")
        
        if mode == "single_prompt":
            task = f"""
            1. Открой тестовый сайт для практики: https://demoqa.com/automation-practice-form
            2. Заполни форму следующими данными:
               - First Name: {user_data.get('first_name', 'Test')}
               - Last Name: {user_data.get('last_name', 'User')}
               - Email: {user_data.get('email', 'test@example.com')}
               - Mobile: {user_data.get('mobile', '1234567890')}
               - Gender: {user_data.get('gender', 'Male')}
            3. Прокрути страницу вниз чтобы увидеть все поля
            4. НЕ нажимай кнопку Submit
            """
            return await self.run_single_prompt(task)
        
        elif mode == "step_by_step":
            steps = [
                "Открой сайт https://demoqa.com/automation-practice-form",
                f"Заполни поле First Name значением {user_data.get('first_name', 'Test')}",
                f"Заполни поле Last Name значением {user_data.get('last_name', 'User')}",
                f"Заполни поле Email значением {user_data.get('email', 'test@example.com')}",
                f"Выбери Gender: {user_data.get('gender', 'Male')}",
                f"Заполни поле Mobile Number значением {user_data.get('mobile', '1234567890')}",
                "Прокрути страницу вниз чтобы увидеть остальные поля",
            ]
            return await self.run_step_by_step(steps)


# ==================== СЦЕНАРИЙ 3: МОНИТОРИНГ ЦЕН ====================

class PriceMonitoringScenario(ScenarioRunner):
    """Мониторинг цен на товары"""
    
    async def run(self, product: str, mode: str = "single_prompt"):
        print(f"\n{'#'*60}")
        print(f"💰 СЦЕНАРИЙ: Мониторинг цен")
        print(f"🛍️ Товар: {product}")
        print(f"{'#'*60}")
        
        if mode == "single_prompt":
            task = f"""
            1. Открой market.yandex.ru
            2. Найди товар "{product}"
            3. Открой карточку первого товара из результатов
            4. Найди и запомни цену товара
            5. Найди название товара и его основные характеристики
            """
            return await self.run_single_prompt(task)
        
        elif mode == "step_by_step":
            steps = [
                "Открой сайт market.yandex.ru",
                f"Введи в поиск товар '{product}'",
                "Нажми кнопку поиска или Enter",
                "Открой карточку первого товара из результатов",
                "Найди и прочитай цену товара",
                "Найди название товара и его основные характеристики",
            ]
            return await self.run_step_by_step(steps)


# ==================== СЦЕНАРИЙ 4: РАБОТА С ВИКИПЕДИЕЙ ====================

class WikipediaScenario(ScenarioRunner):
    """Поиск и извлечение информации из Википедии"""
    
    async def run(self, topic: str, mode: str = "single_prompt"):
        print(f"\n{'#'*60}")
        print(f"📚 СЦЕНАРИЙ: Поиск в Википедии")
        print(f"📖 Тема: {topic}")
        print(f"{'#'*60}")
        
        if mode == "single_prompt":
            task = f"""
            1. Открой ru.wikipedia.org
            2. Найди статью по теме "{topic}"
            3. Прочитай первый абзац статьи (введение)
            4. Найди и прочитай содержание (оглавление) статьи
            5. Прокрути до раздела "История" если он есть
            """
            return await self.run_single_prompt(task)
        
        elif mode == "step_by_step":
            steps = [
                "Открой сайт ru.wikipedia.org",
                f"Введи в поиск тему '{topic}' и нажми Enter",
                "Прочитай первый абзац статьи (введение перед содержанием)",
                "Найди блок 'Содержание' и прочитай список разделов",
                "Прокрути страницу и найди раздел 'История' если он существует",
            ]
            return await self.run_step_by_step(steps)


# ==================== ГЛАВНОЕ МЕНЮ ====================

async def show_menu_and_run():
    """Интерактивное меню выбора сценария"""
    
    print("\n" + "="*60)
    print("🤖 BROWSER-USE + GEMINI: Многосценарный запуск")
    print("="*60)
    
    # Инициализация с выводом конфигурации
    try:
        config = get_app_config()
        config.print_config()
        
        llm = get_llm()
        profile_path = get_profile_path()
    except ValueError as e:
        print(f"\n{e}")
        return
    
    # Выбор сценария
    print("\n" + "-"*60)
    print("📋 ДОСТУПНЫЕ СЦЕНАРИИ:")
    print("-"*60)
    print("1. 📰 Поиск новостей на Яндекс")
    print("2. 📝 Заполнение формы регистрации (DemoQA)")
    print("3. 💰 Мониторинг цен на товар (Яндекс.Маркет)")
    print("4. 📚 Поиск информации в Википедии")
    print("0. ❌ Выход")
    
    choice = input("\n👉 Выберите сценарий (0-4): ").strip()
    
    if choice == "0":
        print("👋 До свидания!")
        return
    
    # Выбор режима
    print("\n" + "-"*60)
    print("⚙️ РЕЖИМ ВЫПОЛНЕНИЯ:")
    print("-"*60)
    print("1. 🎯 Единый промпт (вся задача сразу)")
    print("2. 👣 Пошаговое выполнение (каждый шаг отдельно)")
    
    mode_choice = input("\n👉 Выберите режим (1-2): ").strip()
    mode = "single_prompt" if mode_choice == "1" else "step_by_step"
    
    # Запуск выбранного сценария
    print(f"\n⏳ Запуск сценария...")
    
    try:
        if choice == "1":
            # Поиск новостей
            query = input("\n🔍 Введите поисковый запрос (или Enter для 'искусственный интеллект'): ").strip()
            query = query or "искусственный интеллект"
            
            scenario = NewsSearchScenario(llm, profile_path)
            result = await scenario.run(query, mode)
            
        elif choice == "2":
            # Регистрация
            print("\n👤 Введите данные для регистрации (или Enter для тестовых):")
            first_name = input("  First Name: ").strip() or "Иван"
            last_name = input("  Last Name: ").strip() or "Тестов"
            email = input("  Email: ").strip() or "ivan.testov@example.com"
            mobile = input("  Mobile (10 цифр): ").strip() or "9001234567"
            
            print("\n  Gender:")
            print("    1. Male")
            print("    2. Female")
            print("    3. Other")
            gender_choice = input("  Выбор (1-3): ").strip()
            gender = {"1": "Male", "2": "Female", "3": "Other"}.get(gender_choice, "Male")
            
            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "mobile": mobile,
                "gender": gender
            }
            
            scenario = RegistrationScenario(llm, profile_path)
            result = await scenario.run(user_data, mode)
            
        elif choice == "3":
            # Мониторинг цен
            product = input("\n🛍️ Введите название товара (или Enter для 'iPhone 15'): ").strip()
            product = product or "iPhone 15"
            
            scenario = PriceMonitoringScenario(llm, profile_path)
            result = await scenario.run(product, mode)
            
        elif choice == "4":
            # Википедия
            topic = input("\n📖 Введите тему для поиска (или Enter для 'Python'): ").strip()
            topic = topic or "Python (язык программирования)"
            
            scenario = WikipediaScenario(llm, profile_path)
            result = await scenario.run(topic, mode)
            
        else:
            print("❌ Неверный выбор сценария!")
            return
        
        print("\n" + "="*60)
        print("✅ СЦЕНАРИЙ ЗАВЕРШЁН!")
        print("="*60)
        print(f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}")
        
        # Вывод статистики использования API
        print_api_stats()
        
        # Вывод результата если есть
        if result:
            print(f"\n📊 Результат выполнения:")
            print(result)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


# ==================== БЫСТРЫЙ ЗАПУСК (БЕЗ МЕНЮ) ====================

async def quick_run_example():
    """Пример быстрого запуска без меню"""
    
    print("\n🚀 БЫСТРЫЙ ЗАПУСК: Пример использования\n")
    
    try:
        llm = get_llm()
        profile_path = get_profile_path()
        
        # Пример 1: Поиск новостей (единый промпт)
        print("\n" + "="*60)
        print("ПРИМЕР 1: Поиск новостей (единый промпт)")
        print("="*60)
        
        scenario = NewsSearchScenario(llm, profile_path)
        await scenario.run("космос", mode="single_prompt")
        
        # Небольшая пауза
        await asyncio.sleep(3)
        
        # Пример 2: Википедия (пошаговый)
        print("\n" + "="*60)
        print("ПРИМЕР 2: Википедия (пошаговый)")
        print("="*60)
        
        scenario = WikipediaScenario(llm, profile_path)
        await scenario.run("Искусственный интеллект", mode="step_by_step")
        
        print("\n✅ Все примеры выполнены!")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


# ==================== ТОЧКА ВХОДА ====================

async def main():
    """Главная функция"""
    
    import sys
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick":
            # Быстрый запуск примеров
            await quick_run_example()
        elif sys.argv[1] == "--help":
            print("""
╔════════════════════════════════════════════════════════════╗
║  Browser-Use + Gemini: Многосценарный скрипт               ║
╚════════════════════════════════════════════════════════════╝

ИСПОЛЬЗОВАНИЕ:
  python multi_scenario.py           - Интерактивное меню
  python multi_scenario.py --quick   - Быстрый запуск примеров
  python multi_scenario.py --help    - Эта справка

СЦЕНАРИИ:
  1. Поиск новостей на Яндекс
  2. Заполнение формы регистрации (DemoQA)
  3. Мониторинг цен на товар (Яндекс.Маркет)
  4. Поиск информации в Википедии

РЕЖИМЫ:
  - Единый промпт: вся задача в одной инструкции
  - Пошаговый: разбиение на отдельные шаги с паузами

ТРЕБОВАНИЯ:
  1. Создать .env файл с GOOGLE_API_KEY
  2. Установить зависимости: pip install -r requirements.txt
  3. Установить браузеры: python -m playwright install
            """)
        else:
            print(f"❌ Неизвестный аргумент: {sys.argv[1]}")
            print("Используйте --help для справки")
    else:
        # Интерактивное меню по умолчанию
        await show_menu_and_run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
