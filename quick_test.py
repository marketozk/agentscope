"""
Простой тест системы регистрации
"""

import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.dirname(__file__))

from src.temp_mail_agent import TempMailAgent

async def test_temp_mail():
    """Тестируем создание временного email"""
    print("🔥 Тестирование TempMailAgent...")
    
    async with TempMailAgent() as agent:
        try:
            # Создаем временный email
            temp_email = await agent.create_temp_email()
            print(f"✅ Создан временный email: {temp_email.email}")
            print(f"🕒 Срок действия до: {temp_email.expires_at}")
            
            # Проверяем входящие
            emails = await agent.check_inbox()
            print(f"📬 Писем в ящике: {len(emails)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

async def main():
    print("🚀 === БЫСТРЫЙ ТЕСТ СИСТЕМЫ ===")
    
    # Тест временной почты
    result = await test_temp_mail()
    
    if result:
        print("\n✅ Система работает!")
        print("📧 TempMailAgent успешно создает временные email адреса")
    else:
        print("\n❌ Есть проблемы с системой")
    
    print("\n🎉 Тест завершен!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
