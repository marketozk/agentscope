"""
Демонстрация работы полной системы регистрации
Показывает, как работают все компоненты вместе
"""

import asyncio
import logging
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.registration_orchestrator import RegistrationOrchestrator
from src.temp_mail_agent import TempMailAgent
from src.email_verification_agent import EmailVerificationAgent

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('registration_demo.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def demo_temp_mail():
    """Демонстрация работы с временной почтой"""
    print("\n🔥 === ДЕМО: Работа с временной почтой ===")
    
    async with TempMailAgent() as agent:
        # Создаем временный email
        temp_email = await agent.create_temp_email()
        print(f"📧 Создан временный email: {temp_email.email}")
        print(f"🕒 Срок действия до: {temp_email.expires_at}")
        
        # Проверяем входящие (пустой ящик)
        emails = await agent.check_inbox()
        print(f"📬 Писем в ящике: {len(emails)}")
        
        # Демо ожидания письма (короткий таймаут для демо)
        print("⏳ Ожидание писем (10 секунд)...")
        verification_email = await agent.wait_for_email(timeout=10)
        
        if verification_email:
            print(f"✅ Получено письмо: {verification_email.subject}")
        else:
            print("⚠️ Письма не получены (нормально для демо)")

async def demo_email_verification():
    """Демонстрация email верификации"""
    print("\n🔥 === ДЕМО: Email верификация ===")
    
    # Примеры ссылок и кодов для демонстрации
    test_scenarios = [
        {
            "name": "Успешная страница подтверждения",
            "url": "https://httpbin.org/html",  # Тестовая страница
            "code": "123456"
        }
    ]
    
    async with EmailVerificationAgent(headless=False) as agent:
        for scenario in test_scenarios:
            print(f"\n📋 Сценарий: {scenario['name']}")
            
            # Тестируем переход по ссылке
            result = await agent.click_verification_link(scenario['url'])
            print(f"🔗 Результат перехода: {result.get('success', False)}")
            print(f"📄 Заголовок страницы: {result.get('title', 'N/A')}")
            
            await asyncio.sleep(2)  # Пауза между тестами

async def demo_full_registration():
    """Демонстрация полного процесса регистрации"""
    print("\n🔥 === ДЕМО: Полный процесс регистрации ===")
    
    # Конфигурация для демо
    config = {
        "max_retries": 2,
        "page_load_timeout": 15000,
        "element_timeout": 3000,
        "email_check_interval": 5,
        "email_wait_timeout": 60,  # Короткий таймаут для демо
        "screenshot_on_error": True,
        "headless_mode": False,  # Показываем браузер для демо
    }
    
    # Данные пользователя для демо
    user_data = {
        'first_name': 'Тест',
        'last_name': 'Пользователь',
        'country': 'Russia',
        'phone': '+7900123456',
        'agree_terms': True,
        'subscribe_newsletter': False
    }
    
    # Тестовые URL для демонстрации
    test_sites = [
        {
            "name": "HTTPBin Forms",
            "url": "https://httpbin.org/forms/post",
            "description": "Простая форма для тестирования"
        },
        {
            "name": "Example.com",
            "url": "https://example.com",
            "description": "Базовая страница (без формы регистрации)"
        }
    ]
    
    orchestrator = RegistrationOrchestrator(config)
    
    for site in test_sites:
        print(f"\n🌐 Тестирование сайта: {site['name']}")
        print(f"📋 Описание: {site['description']}")
        print(f"🔗 URL: {site['url']}")
        
        try:
            result = await orchestrator.start_registration(
                registration_url=site['url'],
                user_data=user_data
            )
            
            # Выводим результаты
            print(f"\n📊 === РЕЗУЛЬТАТЫ ===")
            print(f"✅ Успешность: {result.success}")
            print(f"👤 Аккаунт создан: {result.account_created}")
            print(f"📧 Email подтвержден: {result.email_verified}")
            print(f"🔑 Учетные данные: {result.credentials}")
            print(f"📸 Скриншотов: {len(result.screenshots)}")
            print(f"⚠️ Ошибок: {len(result.errors)}")
            
            # Выводим детали шагов
            print(f"\n📋 === ШАГИ ПРОЦЕССА ===")
            for step in result.steps:
                status_emoji = "✅" if step.status == "completed" else "❌" if step.status == "failed" else "⏳"
                print(f"{status_emoji} {step.step_name}: {step.status}")
                if step.error:
                    print(f"   ❌ Ошибка: {step.error}")
            
            # Сохраняем лог
            orchestrator.save_registration_log(f"demo_log_{site['name'].replace(' ', '_').lower()}.json")
            
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
        
        print(f"\n{'='*60}")
        await asyncio.sleep(3)  # Пауза между сайтами

async def demo_manual_temp_mail_check():
    """Демо проверки реальной temp-mail ссылки"""
    print("\n🔥 === ДЕМО: Проверка реальной temp-mail ===")
    
    # Используем реальный API temp-mail.io для демо
    print("🌐 Подключение к temp-mail.io...")
    
    async with TempMailAgent() as agent:
        try:
            # Создаем реальный временный email
            temp_email = await agent.create_temp_email()
            print(f"📧 Создан email: {temp_email.email}")
            
            # Показываем как проверить ящик
            print("📬 Проверка входящих писем...")
            emails = await agent.check_inbox()
            
            if emails:
                print(f"📨 Найдено писем: {len(emails)}")
                for i, email in enumerate(emails, 1):
                    print(f"  {i}. От: {email.from_email}")
                    print(f"     Тема: {email.subject}")
                    print(f"     Дата: {email.received_at}")
            else:
                print("📭 Входящих писем нет")
            
            # Показываем извлечение ссылок и кодов
            if emails:
                first_email = emails[0]
                link = await agent.extract_verification_link(first_email)
                code = await agent.extract_verification_code(first_email)
                
                if link:
                    print(f"🔗 Найдена ссылка: {link}")
                if code:
                    print(f"🔢 Найден код: {code}")
                
        except Exception as e:
            print(f"⚠️ Ошибка при работе с temp-mail: {e}")
            print("💡 Это нормально - API может быть недоступен или требовать ключ")

async def main():
    """Главная функция демонстрации"""
    print("🚀 === ДЕМОНСТРАЦИЯ СИСТЕМЫ РЕГИСТРАЦИИ AgentScope ===")
    print("Эта демонстрация покажет работу всех компонентов системы")
    
    demos = [
        ("Работа с временной почтой", demo_temp_mail),
        ("Email верификация", demo_email_verification),
        ("Проверка temp-mail.io", demo_manual_temp_mail_check),
        ("Полный процесс регистрации", demo_full_registration),
    ]
    
    for name, demo_func in demos:
        print(f"\n🎯 Запуск демо: {name}")
        print("📍 Нажмите Enter для продолжения или Ctrl+C для выхода...")
        
        try:
            input()  # Ждем нажатия Enter
            await demo_func()
        except KeyboardInterrupt:
            print("\n👋 Демонстрация прервана пользователем")
            break
        except Exception as e:
            print(f"❌ Ошибка в демо '{name}': {e}")
            logger.exception(f"Ошибка в демо {name}")
        
        print(f"\n✅ Демо '{name}' завершено")
    
    print("\n🎉 Демонстрация завершена!")
    print("📁 Проверьте файлы логов для подробной информации")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Программа завершена пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logger.exception("Критическая ошибка в демо")
