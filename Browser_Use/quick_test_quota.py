#!/usr/bin/env python3
"""Быстрая проверка квоты на gemini-exp-1206"""

import asyncio
from config import AppConfig
from browser_use.llm.messages import UserMessage

async def test_quota():
    """Проверяет доступность модели gemini-exp-1206"""
    print("🧪 Тестирование gemini-exp-1206...")
    print("=" * 60)
    
    try:
        # Инициализируем конфиг
        config = AppConfig()
        print(f"✅ Активная модель: {config.model_config['name']}")
        print(f"📊 Rate limits: {config.model_config['requests_per_minute']} RPM, {config.model_config['requests_per_day']} RPD")
        
        # Простой тестовый запрос
        print("\n📤 Отправляю тестовый запрос...")
        
        llm = config.get_llm()
        messages = [UserMessage(content="Скажи 'OK' если ты работаешь")]
        
        response = await llm.ainvoke(messages)
        
        print(f"✅ Ответ получен: {response.completion[:100]}")
        print("\n🎉 УСПЕХ! Модель работает, квота доступна!")
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Ошибка: {error_msg}")
        
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            print("⚠️  Квота исчерпана на этой модели!")
        elif "quota" in error_msg.lower():
            print("⚠️  Проблема с квотой!")
        else:
            print(f"❓ Другая ошибка: {type(e).__name__}")
        
        return False

if __name__ == "__main__":
    asyncio.run(test_quota())
