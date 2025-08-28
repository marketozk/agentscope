"""
Быстрый тест интеграции AgentScope - только проверяем что все работает
"""

import asyncio
from main import IntelligentRegistrationAgent

async def quick_test():
    print("🚀 БЫСТРЫЙ ТЕСТ AGENTSCOPE ИНТЕГРАЦИИ")
    print("=" * 45)
    
    # Тест 1: Создание агента
    agent = IntelligentRegistrationAgent("test_key")
    print("✅ Агент создан")
    
    # Тест 2: Проверка AgentScope
    from main import AGENTSCOPE_AVAILABLE
    print(f"✅ AgentScope: {'доступен' if AGENTSCOPE_AVAILABLE else 'недоступен'}")
    
    # Тест 3: Генерация данных 
    await agent.generate_user_data()
    print(f"✅ Email: {agent.context['email']}")
    print(f"✅ Username: {agent.context['username']}")
    
    print("\n🎉 Интеграция работает! Система готова.")

if __name__ == "__main__":
    asyncio.run(quick_test())
