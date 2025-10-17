"""
🎯 Простой пример использования browser-use с Computer Use моделью

Этот скрипт показывает:
1. Как правильно настроить ChatGoogle с Computer Use инструментом
2. Как передать его в browser-use Agent
3. Как запустить простую задачу в браузере
"""
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Новый SDK для Computer Use
from google import genai
from google.genai import types as genai_types
from google.genai.types import ComputerUse, Environment

# Browser-use Agent и правильный ChatGoogle wrapper из browser-use
from browser_use.llm.google import ChatGoogle

# Наш кастомный агент для Computer Use моделей
from gemini_computer_agent import GeminiComputerAgent

def main():
    # 1. Загружаем API-ключ
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("❌ GOOGLE_API_KEY не найден в .env")
    
    print("✅ API-ключ загружен")

    # 2. Определяем модель
    model_name = "gemini-2.5-computer-use-preview-10-2025"
    print(f"🤖 Модель: {model_name}")

    # 3. Настраиваем Computer Use инструмент
    # Для computer-use моделей ОБЯЗАТЕЛЬНО нужен Computer Use tool
    computer_use_config = {
        "tools": [
            {
                "computer_use": {
                    "environment": "ENVIRONMENT_BROWSER"
                }
            }
        ]
    }
    print("� Computer Use tool настроен")

    # 4. Создаем LLM через ChatGoogle из browser-use
    # Важно: supports_structured_output=False для computer-use моделей
    llm = ChatGoogle(
        model=model_name,
        api_key=api_key,  # Правильное имя параметра
        config=computer_use_config,
        supports_structured_output=False,  # Отключаем JSON-режим для computer-use
        temperature=0.7,
    )
    print("✅ LLM создан с Computer Use конфигурацией")

    # 5. Запускаем агента
    async def run_agent_task():
        print("\n" + "="*60)
        print("🚀 ЗАПУСК GEMINI COMPUTER USE АГЕНТА")
        print("="*60)
        
        # Создаем СПЕЦИАЛЬНЫЙ агент для Computer Use моделей
        # Он правильно обрабатывает tool_calls вместо попыток парсить JSON
        agent = GeminiComputerAgent(
            task="Открой сайт google.com и найди информацию о Python",
            llm=llm,
            use_vision=True,
            max_steps=10,
            output_model_schema=None,  # Критично: не используем structured output!
        )
        
        print("🤖 GeminiComputerAgent создан, начинаю выполнение...\n")
        
        try:
            # Запускаем агента
            result = await agent.run()
            
            print("\n" + "="*60)
            print("✅ ЗАДАЧА ВЫПОЛНЕНА")
            print("="*60)
            print(f"📝 Результат: {result}")
            
        except Exception as e:
            print(f"\n❌ Ошибка выполнения: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Закрываем браузер
            await agent.close()
            print("\n👋 Браузер закрыт")

    # Запускаем асинхронный код
    asyncio.run(run_agent_task())

if __name__ == "__main__":
    main()