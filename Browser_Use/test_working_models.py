"""
Тест для проверки работоспособности различных моделей Gemini с browser-use.
Проверяет каждую модель из конфигурации и выводит результаты.
"""
import asyncio
import os
from dotenv import load_dotenv
from browser_use import Agent
from browser_use.llm.google import ChatGoogle
from config import ModelConfig

# Загрузить переменные окружения
load_dotenv()

async def test_model(model_name: str) -> dict:
    """
    Тестирует одну модель.
    
    Args:
        model_name: Имя модели для тестирования
        
    Returns:
        dict с результатами теста
    """
    print(f"\n{'='*60}")
    print(f"Тестирование модели: {model_name}")
    print(f"{'='*60}")
    
    result = {
        'model': model_name,
        'status': 'unknown',
        'error': None,
        'llm_created': False,
        'agent_created': False
    }
    
    try:
        # Шаг 1: Создание LLM
        print(f"1. Создание LLM для {model_name}...")
        
        # Получаем конфигурацию модели
        model_info = ModelConfig.MODELS.get(model_name)
        if not model_info:
            raise ValueError(f"Модель {model_name} не найдена в конфигурации")
        
        # Создаем LLM напрямую
        api_key = os.getenv('GOOGLE_API_KEY')
        llm = ChatGoogle(
            model=model_info['model_string'],
            api_key=api_key
        )
        result['llm_created'] = True
        print(f"   ✓ LLM успешно создан")
        
        # Шаг 2: Создание агента (без запуска браузера)
        print(f"2. Создание агента с {model_name}...")
        agent = Agent(
            task="test task",
            llm=llm,
            use_vision=False  # Не используем vision для быстрого теста
        )
        result['agent_created'] = True
        print(f"   ✓ Агент успешно создан")
        
        result['status'] = 'success'
        print(f"\n✅ Модель {model_name} работает корректно!")
        
    except Exception as e:
        error_msg = str(e)
        result['error'] = error_msg
        result['status'] = 'failed'
        
        print(f"\n❌ Ошибка при тестировании {model_name}:")
        print(f"   {error_msg}")
        
        # Анализ типа ошибки
        if '404' in error_msg or 'NOT_FOUND' in error_msg:
            print(f"   → Модель не найдена (404)")
        elif '503' in error_msg or 'UNAVAILABLE' in error_msg:
            print(f"   → Модель перегружена (503)")
        elif '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg:
            print(f"   → Превышен лимит запросов (429)")
        elif 'API_KEY' in error_msg:
            print(f"   → Проблема с API ключом")
    
    return result

async def main():
    """Основная функция тестирования всех моделей."""
    
    # Проверка API ключа
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ ОШИБКА: GOOGLE_API_KEY не установлен в .env файле")
        return
    
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ МОДЕЛЕЙ GEMINI С BROWSER-USE")
    print("="*60)
    print(f"\nНайдено моделей для тестирования: {len(ModelConfig.MODELS)}")
    
    # Тестирование каждой модели
    results = []
    for model_name in ModelConfig.MODELS.keys():
        result = await test_model(model_name)
        results.append(result)
        
        # Небольшая пауза между тестами
        await asyncio.sleep(2)
    
    # Итоговый отчет
    print("\n" + "="*60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("="*60)
    
    working_models = [r for r in results if r['status'] == 'success']
    failed_models = [r for r in results if r['status'] == 'failed']
    
    print(f"\n✅ Работающие модели ({len(working_models)}):")
    for r in working_models:
        model_info = ModelConfig.MODELS[r['model']]
        print(f"   • {r['model']}")
        print(f"     - {model_info['description']}")
        print(f"     - Лимиты: {model_info['requests_per_minute']}/мин, {model_info['requests_per_day']}/день")
    
    if failed_models:
        print(f"\n❌ Неработающие модели ({len(failed_models)}):")
        for r in failed_models:
            print(f"   • {r['model']}")
            print(f"     - Ошибка: {r['error'][:100]}...")
    
    # Рекомендации
    print("\n" + "="*60)
    print("РЕКОМЕНДАЦИИ")
    print("="*60)
    
    if working_models:
        best_model = working_models[0]['model']
        print(f"\n✓ Рекомендуемая модель: {best_model}")
        print(f"  Установите в .env файле:")
        print(f"  GEMINI_MODEL={best_model}")
        
        if len(working_models) > 1:
            print(f"\n✓ Альтернативные модели:")
            for r in working_models[1:]:
                print(f"  - {r['model']}")
    else:
        print("\n⚠ Внимание: Ни одна модель не прошла тест!")
        print("  Возможные причины:")
        print("  1. Проблема с API ключом")
        print("  2. Все модели временно недоступны")
        print("  3. Проблема с интернет-соединением")
    
    # Сохранение результатов в файл
    print("\n" + "="*60)
    print("Сохранение результатов...")
    
    with open('Browser_Use/test_results.txt', 'w', encoding='utf-8') as f:
        f.write("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ МОДЕЛЕЙ GEMINI\n")
        f.write("="*60 + "\n\n")
        
        f.write("Работающие модели:\n")
        for r in working_models:
            f.write(f"  ✓ {r['model']}\n")
        
        f.write("\nНеработающие модели:\n")
        for r in failed_models:
            f.write(f"  ✗ {r['model']}: {r['error']}\n")
        
        if working_models:
            f.write(f"\nРекомендация: используйте GEMINI_MODEL={working_models[0]['model']}\n")
    
    print("✓ Результаты сохранены в Browser_Use/test_results.txt")

if __name__ == "__main__":
    asyncio.run(main())
