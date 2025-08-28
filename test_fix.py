"""
Тест исправления TypeError с await
"""

import asyncio
from main import IntelligentRegistrationAgent

async def test_fix():
    print("🔧 ТЕСТ ИСПРАВЛЕНИЯ TYPEERROR")
    print("=" * 35)
    
    agent = IntelligentRegistrationAgent("test_key")
    print("✅ Агент создан")
    
    # Симулируем создание страницы
    print("🤖 Тест инициализации агентов...")
    try:
        # Создаем мок page объект
        class MockPage:
            pass
        
        mock_page = MockPage()
        agent.init_agents(mock_page)  # Теперь без await
        print("✅ init_agents работает без ошибки")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    print("🎉 Исправление применено успешно!")
    return True

if __name__ == "__main__":
    asyncio.run(test_fix())
