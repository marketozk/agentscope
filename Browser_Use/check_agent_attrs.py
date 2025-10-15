"""
Проверка атрибутов и методов Agent из browser-use
"""
import asyncio
from browser_use import Agent
from config import get_llm

async def check_agent():
    llm = get_llm()
    
    # Создаём агента
    agent = Agent(
        task="Open google.com",
        llm=llm,
        use_vision=True
    )
    
    print("=" * 60)
    print("АТРИБУТЫ AGENT ПОСЛЕ СОЗДАНИЯ (до run):")
    print("=" * 60)
    
    # Проверяем основные атрибуты
    important_attrs = [
        'task', 'llm', 'browser_profile', 'browser_session', 
        'controller', 'tools', 'use_vision'
    ]
    
    for attr in important_attrs:
        value = getattr(agent, attr, "НЕТ АТРИБУТА")
        print(f"{attr}: {type(value).__name__} = {str(value)[:100]}")
    
    print("\n" + "=" * 60)
    print("ЗАПУСКАЕМ agent.run()...")
    print("=" * 60)
    
    try:
        result = await agent.run()
        
        print("\n" + "=" * 60)
        print("АТРИБУТЫ AGENT ПОСЛЕ run():")
        print("=" * 60)
        
        for attr in important_attrs:
            value = getattr(agent, attr, "НЕТ АТРИБУТА")
            print(f"{attr}: {type(value).__name__} = {str(value)[:100]}")
        
        # Проверяем browser_session
        if hasattr(agent, 'browser_session') and agent.browser_session:
            print("\n" + "=" * 60)
            print("АТРИБУТЫ browser_session:")
            print("=" * 60)
            session = agent.browser_session
            session_attrs = [a for a in dir(session) if not a.startswith('_')]
            for attr in session_attrs[:20]:  # Первые 20
                try:
                    value = getattr(session, attr)
                    print(f"{attr}: {type(value).__name__}")
                except:
                    print(f"{attr}: ERROR")
        
        print("\n" + "=" * 60)
        print(f"РЕЗУЛЬТАТ run(): {type(result).__name__}")
        print("=" * 60)
        print(str(result)[:500])
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    # Держим браузер открытым
    print("\n⏳ Браузер остается открытым 30 секунд...")
    await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(check_agent())
