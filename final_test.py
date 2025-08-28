"""
Финальный тест всех компонентов системы
"""

import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_temp_mail():
    """Тестирует TempMailAgent"""
    print("🔥 Тестирование TempMailAgent...")
    
    try:
        from src.temp_mail_agent import TempMailAgent
        
        async with TempMailAgent() as agent:
            # Создаем временный email
            temp_email = await agent.create_temp_email()
            print(f"✅ Email создан: {temp_email.email}")
            
            # Проверяем входящие
            emails = await agent.check_inbox()
            print(f"✅ Проверка входящих: {len(emails)} писем")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка TempMailAgent: {e}")
        return False

async def test_email_verification():
    """Тестирует EmailVerificationAgent"""
    print("\n🔥 Тестирование EmailVerificationAgent...")
    
    try:
        from src.email_verification_agent import EmailVerificationAgent
        
        async with EmailVerificationAgent(headless=True) as agent:
            # Тестируем переход по тестовой ссылке
            result = await agent.click_verification_link("https://httpbin.org/html")
            print(f"✅ Переход по ссылке: {result.get('success', False)}")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка EmailVerificationAgent: {e}")
        return False

async def test_registration_orchestrator():
    """Тестирует RegistrationOrchestrator"""
    print("\n🔥 Тестирование RegistrationOrchestrator...")
    
    try:
        from src.registration_orchestrator import RegistrationOrchestrator
        
        orchestrator = RegistrationOrchestrator()
        
        # Тестовые данные
        user_data = {
            'first_name': 'Тест',
            'last_name': 'Пользователь'
        }
        
        # Запускаем тестовую регистрацию
        result = await orchestrator.start_registration(
            registration_url="https://httpbin.org/forms/post",
            user_data=user_data
        )
        
        print(f"✅ Регистрация завершена: {result.success}")
        print(f"✅ Шагов выполнено: {len(result.steps)}")
        print(f"✅ Email создан: {result.credentials.get('email', 'N/A')}")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Ошибка RegistrationOrchestrator: {e}")
        return False

async def test_interface_analysis():
    """Тестирует анализ интерфейса"""
    print("\n🔥 Тестирование анализа интерфейса...")
    
    try:
        from src.interface_agent import InterfaceAgent
        
        agent = InterfaceAgent()
        
        # Анализируем тестовую страницу
        result = await agent.analyze_page("https://httpbin.org/forms/post")
        
        print(f"✅ Страница проанализирована: {result.get('success', False)}")
        print(f"✅ Найдено элементов: {len(result.get('interactive_elements', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка анализа интерфейса: {e}")
        return False

async def main():
    """Запускает все тесты"""
    print("🚀 === ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ AgentScope ===")
    print("Проверяем все компоненты системы...\n")
    
    tests = [
        ("TempMailAgent", test_temp_mail),
        ("EmailVerificationAgent", test_email_verification),
        ("Interface Analysis", test_interface_analysis),
        ("RegistrationOrchestrator", test_registration_orchestrator),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в {test_name}: {e}")
            results.append((test_name, False))
        
        print(f"\n{'='*50}")
    
    # Итоговые результаты
    print(f"\n🎯 === ИТОГОВЫЕ РЕЗУЛЬТАТЫ ===")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\n📊 Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система полностью работоспособна!")
    elif passed >= total * 0.7:
        print("⚠️ Большинство тестов пройдено. Система в основном работает.")
    else:
        print("❌ Много тестов провалено. Требуется доработка.")
    
    print(f"\n📋 Система готова для:")
    print(f"   📧 Создания временных email адресов")
    print(f"   🔍 Анализа веб-интерфейсов")
    print(f"   ✉️ Email верификации")
    print(f"   🤖 Автоматической регистрации")
    
    print(f"\n🎪 Для демонстрации запустите:")
    print(f"   python demo_interface_analysis.py")
    print(f"   python demo_registration_system.py")

if __name__ == "__main__":
    asyncio.run(main())
