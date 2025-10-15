"""
Быстрый тест DeepSeek API
"""
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import os

# Загружаем .env
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

async def test_deepseek():
    print("\n🧪 Тестирование DeepSeek API...")
    print("=" * 60)
    
    # Проверяем наличие ключа
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ DEEPSEEK_API_KEY не найден в .env файле!")
        return
    
    print(f"✅ API ключ найден: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model="deepseek-chat",
            temperature=0.2,
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        print("\n📤 Отправка тестового запроса...")
        response = await llm.ainvoke("Say 'Hello, DeepSeek is working!' in one sentence.")
        
        print("\n✅ УСПЕХ! DeepSeek API работает!")
        print(f"📝 Ответ: {response.content}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_deepseek())
