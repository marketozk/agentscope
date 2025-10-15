"""
Демонстрация работы Rate Limiter - тест автоматического ожидания
"""
import asyncio
from config import get_rate_limiter, ModelConfig

async def test_rate_limiting():
    """Тестирует систему rate limiting с автоматическим ожиданием"""
    
    print("\n" + "="*70)
    print("🧪 ДЕМОНСТРАЦИЯ РАБОТЫ RATE LIMITER")
    print("="*70)
    
    # Для теста используем модель с минимальным лимитом
    model_config = ModelConfig.MODELS["gemini-2.5-pro"]  # 5 req/min
    print(f"\n📋 Используем модель: gemini-2.5-pro")
    print(f"   Лимит: {model_config['requests_per_minute']} запросов/минуту")
    
    # Создаем rate limiter с малым лимитом для быстрого теста
    limiter = get_rate_limiter()
    
    print(f"\n🎯 Попытаемся сделать {model_config['requests_per_minute'] + 3} запросов быстро...")
    print("="*70)
    
    # Делаем запросы
    for i in range(model_config['requests_per_minute'] + 3):
        print(f"\n🔄 Запрос #{i+1}")
        
        # Проверяем и ждём если нужно
        can_proceed = await limiter.wait_if_needed()
        
        if not can_proceed:
            print(f"⛔ Запрос #{i+1} заблокирован (достигнут дневной лимит)")
            break
        
        # "Выполняем" запрос
        limiter.register_request()
        print(f"✅ Запрос #{i+1} выполнен успешно")
        
        # Показываем текущую статистику
        stats = limiter.get_stats()
        print(f"   📊 Использовано в текущую минуту: {stats['minute_used']}/{limiter.requests_per_minute}")
        print(f"   📊 Использовано за день: {stats['day_used']}/{limiter.requests_per_day}")
    
    # Итоговая статистика
    print("\n" + "="*70)
    print("📈 ИТОГОВАЯ СТАТИСТИКА")
    print("="*70)
    limiter.print_stats()
    
    print("\n" + "="*70)
    print("✅ Демонстрация завершена!")
    print("="*70)
    
    print("\n💡 Что произошло:")
    print("   1. Первые 5 запросов прошли мгновенно")
    print("   2. На 6-м запросе система автоматически подождала ~60 секунд")
    print("   3. После ожидания запросы продолжились")
    print("\n🎯 Вывод: Rate Limiter автоматически управляет темпом запросов!")

async def quick_test():
    """Быстрый тест без реального ожидания"""
    print("\n" + "="*70)
    print("⚡ БЫСТРЫЙ ТЕСТ RATE LIMITER (без ожидания)")
    print("="*70)
    
    limiter = get_rate_limiter()
    
    print("\n1️⃣ Проверяем начальное состояние:")
    stats = limiter.get_stats()
    print(f"   Минута: {stats['minute_used']}/{limiter.requests_per_minute}")
    print(f"   День: {stats['day_used']}/{limiter.requests_per_day}")
    
    print(f"\n2️⃣ Делаем {limiter.requests_per_minute} запросов...")
    for i in range(limiter.requests_per_minute):
        can_request, reason = limiter.can_make_request()
        if can_request:
            limiter.register_request()
            print(f"   ✅ Запрос {i+1} зарегистрирован")
        else:
            print(f"   ⛔ Запрос {i+1} отклонён: {reason}")
    
    print("\n3️⃣ Пытаемся сделать ещё один (должен быть отклонён):")
    can_request, reason = limiter.can_make_request()
    if can_request:
        print("   ❌ ОШИБКА: Запрос прошёл, хотя не должен был!")
    else:
        print(f"   ✅ Запрос правильно отклонён: {reason}")
    
    print("\n4️⃣ Финальная статистика:")
    limiter.print_stats()
    
    print("\n✅ Быстрый тест завершён!")

if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("🎮 ТЕСТИРОВАНИЕ СИСТЕМЫ RATE LIMITING")
    print("="*70)
    print("\nВыберите режим:")
    print("1. Быстрый тест (без реального ожидания) - рекомендуется")
    print("2. Полный тест (с автоматическим ожиданием ~60 сек)")
    
    choice = input("\nВаш выбор (1 или 2, Enter = 1): ").strip() or "1"
    
    if choice == "2":
        print("\n⚠️ ВНИМАНИЕ: Этот тест займёт ~60 секунд из-за реального ожидания")
        confirm = input("Продолжить? (y/n): ").strip().lower()
        if confirm == 'y':
            asyncio.run(test_rate_limiting())
        else:
            print("\n❌ Тест отменён")
    else:
        asyncio.run(quick_test())
