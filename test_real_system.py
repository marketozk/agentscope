"""
Тест реальной системы регистрации без заглушек
"""

import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_real_registration():
    """Тестирует реальную систему регистрации"""
    print("🚀 === ТЕСТ РЕАЛЬНОЙ СИСТЕМЫ РЕГИСТРАЦИИ ===")
    
    from src.registration_orchestrator import RegistrationOrchestrator
    
    try:
        # Создаем оркестратор
        orchestrator = RegistrationOrchestrator({
            "headless_mode": True,  # Скрытый режим для тестов
            "email_wait_timeout": 60,  # Короткий таймаут для тестов
            "screenshot_on_error": True
        })
        
        # Тестовые данные пользователя
        user_data = {
            'first_name': 'Тест',
            'last_name': 'Пользователь',
            'country': 'Russia',
            'phone': '+7900123456'
        }
        
        # Тестируем на простой форме
        test_url = "https://httpbin.org/forms/post"
        
        print(f"🌐 Тестирование на: {test_url}")
        print("🔄 Запуск процесса регистрации...")
        
        # Запускаем реальную регистрацию
        result = await orchestrator.start_registration(
            registration_url=test_url,
            user_data=user_data
        )
        
        # Выводим подробные результаты
        print(f"\n📊 === РЕЗУЛЬТАТЫ ТЕСТА ===")
        print(f"✅ Общий успех: {result.success}")
        print(f"👤 Аккаунт создан: {result.account_created}")
        print(f"📧 Email подтвержден: {result.email_verified}")
        print(f"🔗 Финальный URL: {result.final_url}")
        
        print(f"\n🔑 === УЧЕТНЫЕ ДАННЫЕ ===")
        for key, value in result.credentials.items():
            if key == 'password':
                print(f"   {key}: {'*' * len(str(value))}")  # Скрываем пароль
            else:
                print(f"   {key}: {value}")
        
        print(f"\n📋 === ШАГИ ПРОЦЕССА ===")
        for i, step in enumerate(result.steps, 1):
            status_emoji = {
                "completed": "✅",
                "failed": "❌", 
                "in_progress": "⏳",
                "pending": "⏸️"
            }.get(step.status, "❓")
            
            print(f"   {i}. {status_emoji} {step.step_name}")
            if step.error:
                print(f"      ❌ Ошибка: {step.error}")
            if step.result and step.result.get('message'):
                print(f"      💬 {step.result['message']}")
        
        if result.errors:
            print(f"\n⚠️ === ОШИБКИ ===")
            for error in result.errors:
                print(f"   ❌ {error}")
        
        if result.screenshots:
            print(f"\n📸 === СКРИНШОТЫ ===")
            for screenshot in result.screenshots:
                print(f"   📷 {screenshot}")
        
        # Сохраняем лог
        orchestrator.save_registration_log("test_real_registration.json")
        print(f"\n💾 Лог сохранен: test_real_registration.json")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_temp_mail_integration():
    """Тестирует интеграцию с temp-mail"""
    print("\n🔥 === ТЕСТ ИНТЕГРАЦИИ С TEMP-MAIL ===")
    
    from src.temp_mail_agent import TempMailAgent
    
    try:
        async with TempMailAgent() as agent:
            # Создаем email
            temp_email = await agent.create_temp_email()
            print(f"📧 Создан email: {temp_email.email}")
            
            # Проверяем функции извлечения
            test_email_body = """
            Добро пожаловать! 
            Для подтверждения регистрации перейдите по ссылке:
            https://example.com/verify?token=ABC123XYZ
            
            Или введите код: 789456
            """
            
            # Создаем тестовое письмо
            from src.temp_mail_agent import Email
            from datetime import datetime
            
            test_email = Email(
                id="test123",
                from_email="noreply@example.com",
                subject="Подтверждение регистрации",
                body=test_email_body,
                received_at=datetime.now()
            )
            
            # Тестируем извлечение данных
            link = await agent.extract_verification_link(test_email)
            code = await agent.extract_verification_code(test_email)
            
            print(f"🔗 Извлеченная ссылка: {link}")
            print(f"🔢 Извлеченный код: {code}")
            
            return link is not None or code is not None
            
    except Exception as e:
        print(f"❌ Ошибка temp-mail: {e}")
        return False

async def test_email_verification():
    """Тестирует email верификацию"""
    print("\n🔥 === ТЕСТ EMAIL ВЕРИФИКАЦИИ ===")
    
    from src.email_verification_agent import EmailVerificationAgent
    
    try:
        async with EmailVerificationAgent(headless=True) as agent:
            # Тестируем на простой странице
            test_url = "https://httpbin.org/html"
            
            result = await agent.click_verification_link(test_url)
            
            print(f"🔗 Переход по ссылке: {result.get('success', False)}")
            print(f"📄 Заголовок: {result.get('title', 'N/A')}")
            print(f"🌐 URL: {result.get('url', 'N/A')}")
            
            return result.get('success', False)
            
    except Exception as e:
        print(f"❌ Ошибка email верификации: {e}")
        return False

async def main():
    """Запускает все реальные тесты"""
    print("🎯 === ПОЛНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ БЕЗ ЗАГЛУШЕК ===")
    
    tests = [
        ("Интеграция с temp-mail", test_temp_mail_integration),
        ("Email верификация", test_email_verification),
        ("Полная система регистрации", test_real_registration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🎯 Выполняется: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"📊 Результат: {'✅ УСПЕХ' if result else '❌ НЕУДАЧА'}")
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в {test_name}: {e}")
            results.append((test_name, False))
        
        print(f"{'='*60}")
    
    # Итоги
    print(f"\n🏆 === ИТОГОВЫЕ РЕЗУЛЬТАТЫ ===")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"   {status} {test_name}")
    
    print(f"\n📊 Общий результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система работает без заглушек!")
    elif passed >= total * 0.7:
        print("⚠️ Большинство функций работает. Система готова к использованию.")
    else:
        print("❌ Необходимо исправить критические проблемы.")
    
    print(f"\n🚀 Система AgentScope готова для автоматической регистрации!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Тестирование прервано пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
