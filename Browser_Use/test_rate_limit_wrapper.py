"""
Тест обертки RateLimitedLLM
"""
import asyncio
from config import get_llm, get_app_config, print_api_stats
from langchain_core.messages import HumanMessage

# Импортируем обертку
import sys
sys.path.insert(0, '.')
from airtable_registration import RateLimitedLLM


async def test_wrapper():
    """Тест что обертка работает"""
    print("\n🧪 ТЕСТИРОВАНИЕ RateLimitedLLM\n")
    
    # Получаем конфиг
    config = get_app_config()
    config.print_config()
    
    # Получаем оригинальный LLM
    original_llm = get_llm()
    
    # Оборачиваем
    wrapped_llm = RateLimitedLLM(original_llm)
    
    print("\n📍 Делаем 3 тестовых вызова...")
    
    for i in range(3):
        print(f"\n--- Вызов {i+1} ---")
        
        messages = [HumanMessage(content=f"Say 'Test {i+1}' and nothing else.")]
        
        try:
            result = await wrapped_llm.ainvoke(messages)
            print(f"✅ Результат получен: {type(result)}")
            # Результат может быть разного типа, просто показываем что получили
            if hasattr(result, 'content'):
                print(f"   Content: {result.content[:50]}")
            else:
                print(f"   Response: {str(result)[:100]}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            break
    
    # Статистика
    print_api_stats()


if __name__ == "__main__":
    asyncio.run(test_wrapper())
