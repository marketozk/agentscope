"""
Простой тест только основной функциональности без сложных блоков
"""

import asyncio
from main import IntelligentRegistrationAgent

async def simple_test():
    print("🧪 ПРОСТОЙ ТЕСТ ОСНОВНОЙ ФУНКЦИОНАЛЬНОСТИ")
    print("=" * 50)
    
    # Тест создания агента
    try:
        agent = IntelligentRegistrationAgent("test_key")
        print("✅ Агент создан успешно")
    except Exception as e:
        print(f"❌ Ошибка создания агента: {e}")
        return
    
    # Тест генерации данных
    try:
        await agent.generate_user_data()
        print(f"✅ Данные сгенерированы: {agent.context['email']}")
    except Exception as e:
        print(f"❌ Ошибка генерации данных: {e}")
        return
        
    print("\n🎉 Основная функциональность работает!")
    print("💡 Для полного теста запустите: python main.py")

if __name__ == "__main__":
    asyncio.run(simple_test())
