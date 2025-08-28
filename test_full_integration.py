"""
Тест полной интеграции AgentScope для регистрации
"""

import asyncio
from main import IntelligentRegistrationAgent

async def test_real_integration():
    print("🚀 ТЕСТ ПОЛНОЙ ИНТЕГРАЦИИ AGENTSCOPE")
    print("=" * 50)
    
    # Используем тестовую ссылку Airtable
    referral_link = "https://airtable.com/invite/r/ovoAP1zR"
    
    # Создаем агента с API ключом
    agent = IntelligentRegistrationAgent("test_key")
    
    print("✅ Агент создан")
    print("🔗 Тестовая ссылка: https://airtable.com/invite/r/ovoAP1zR")
    print("🤖 Будут использоваться AgentScope агенты для умного поиска элементов")
    
    # Запускаем реальную регистрацию
    try:
        await agent.register(referral_link)
    except KeyboardInterrupt:
        print("\n⏹️ Тест прерван пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка теста: {e}")
    
    print("\n🎉 Тест интеграции завершен!")

if __name__ == "__main__":
    asyncio.run(test_real_integration())
