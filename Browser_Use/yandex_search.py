import asyncio
import os
from pathlib import Path
from browser_use import Agent, llm as bu_llm
from dotenv import load_dotenv

# Импорт конфигурации с rate limiting
from config import (
    get_app_config,
    get_llm,
    get_profile_path,
    wait_for_rate_limit,
    register_api_request,
    print_api_stats
)

# Загружаем переменные окружения из .env рядом со скриптом
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

async def main():
    # Инициализация конфигурации
    try:
        config = get_app_config()
        config.print_config()
        
        llm = get_llm()
        profile_path = get_profile_path()
    except ValueError as e:
        print(f"\n❌ Ошибка: {e}")
        return
    
    print("\n🚀 Запуск агента...")
    
    # Проверка rate limit перед запуском
    if not await wait_for_rate_limit():
        print("⛔ Достигнут дневной лимит API. Попробуйте позже.")
        return
    
    # Создаем и запускаем агента
    agent = Agent(
        task="Зайди на yandex.ru и введи 'тест' в поиск",
        llm=llm,
        use_vision=False,
    )
    
    # Регистрируем запрос
    register_api_request()
    
    await agent.run()
    
    print("\n✅ Готово!")
    
    # Показываем статистику
    print_api_stats()

if __name__ == "__main__":
    asyncio.run(main())