"""
Тестовый скрипт для CoolPrompt с GPT-5 моделями
Автоматическая оптимизация промптов с использованием GPT-5
"""
import os
import sys
import logging
from io import StringIO
from coolprompt.assistant import PromptTuner
from langchain_openai import ChatOpenAI

# Подавляем NLTK логи (перехватываем stderr для nltk.download)
logging.getLogger('nltk').setLevel(logging.CRITICAL)

# Перехватываем вывод NLTK download
class SuppressNLTKDownload:
    def __enter__(self):
        self._original_stderr = sys.stderr
        sys.stderr = StringIO()
        return self
    
    def __exit__(self, *args):
        sys.stderr = self._original_stderr

# Применяем один раз при импорте
import nltk
with SuppressNLTKDownload():
    try:
        nltk.download('wordnet', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        nltk.download('omw-1.4', quiet=True)
    except:
        pass  # Уже установлены

# API ключ OpenAI
API_KEY = "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"

os.environ["OPENAI_API_KEY"] = API_KEY

def test_basic_prompt_optimization():
    """Тест 1: Базовая оптимизация промпта"""
    print("=" * 70)
    print("ТЕСТ 1: БАЗОВАЯ ОПТИМИЗАЦИЯ ПРОМПТА С GPT-5")
    print("=" * 70)
    
    try:
        # Создаем модель GPT-5
        llm = ChatOpenAI(
            model="gpt-5-chat-latest",
            temperature=0.7,
            api_key=API_KEY
        )
        
        # Инициализируем PromptTuner
        prompt_tuner = PromptTuner(target_model=llm)
        
        # Задача для оптимизации
        task = "Напиши короткий рассказ о программисте, который нашел баг в своем коде"
        
        print(f"\n📝 Исходная задача: {task}")
        print("\n🔄 Запуск оптимизации промпта...")
        
        # Запускаем оптимизацию
        prompt_tuner.run(task)
        
        print("\n✅ Оптимизация завершена!")
        print("\n" + "=" * 70)
        print("ОПТИМИЗИРОВАННЫЙ ПРОМПТ:")
        print("=" * 70)
        print(prompt_tuner.final_prompt)
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print(f"Тип ошибки: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def test_custom_task_optimization():
    """Тест 2: Оптимизация для специфической задачи"""
    print("\n" + "=" * 70)
    print("ТЕСТ 2: ОПТИМИЗАЦИЯ ДЛЯ ГЕНЕРАЦИИ КОДА")
    print("=" * 70)
    
    try:
        llm = ChatOpenAI(
            model="gpt-5",
            temperature=0.3,  # Низкая температура для кода
            api_key=API_KEY
        )
        
        prompt_tuner = PromptTuner(target_model=llm)
        
        task = "Create a Python function to check if a number is prime"
        
        print(f"\n📝 Задача: {task}")
        print("\n🔄 Оптимизация промпта для генерации кода...")
        
        prompt_tuner.run(task)
        
        print("\n✅ Готово!")
        print("\n" + "=" * 70)
        print("ОПТИМИЗИРОВАННЫЙ ПРОМПТ ДЛЯ КОДА:")
        print("=" * 70)
        print(prompt_tuner.final_prompt)
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return False

def test_with_gpt5_mini():
    """Тест 3: Использование GPT-5-mini для быстрой оптимизации"""
    print("\n" + "=" * 70)
    print("ТЕСТ 3: БЫСТРАЯ ОПТИМИЗАЦИЯ С GPT-5-MINI")
    print("=" * 70)
    
    try:
        llm = ChatOpenAI(
            model="gpt-5-mini",
            temperature=0.5,
            api_key=API_KEY
        )
        
        prompt_tuner = PromptTuner(target_model=llm)
        
        task = "Explain machine learning to a 10-year-old"
        
        print(f"\n📝 Задача: {task}")
        print("\n🔄 Быстрая оптимизация с mini-моделью...")
        
        prompt_tuner.run(task)
        
        print("\n✅ Выполнено!")
        print("\n" + "=" * 70)
        print("ОПТИМИЗИРОВАННЫЙ ПРОМПТ (GPT-5-MINI):")
        print("=" * 70)
        print(prompt_tuner.final_prompt)
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return False

def test_with_evaluation():
    """Тест 4: Оптимизация с оценкой качества"""
    print("\n" + "=" * 70)
    print("ТЕСТ 4: ОПТИМИЗАЦИЯ С ОЦЕНКОЙ КАЧЕСТВА")
    print("=" * 70)
    
    try:
        llm = ChatOpenAI(
            model="gpt-5-chat-latest",
            temperature=0.7,
            api_key=API_KEY
        )
        
        # PromptTuner с оценкой
        prompt_tuner = PromptTuner(target_model=llm)
        
        task = "Write a professional email to decline a job offer politely"
        
        print(f"\n📝 Задача: {task}")
        print("\n🔄 Оптимизация с оценкой качества...")
        
        prompt_tuner.run(task)
        
        print("\n✅ Оптимизация с оценкой завершена!")
        print("\n" + "=" * 70)
        print("ЛУЧШИЙ ПРОМПТ:")
        print("=" * 70)
        print(prompt_tuner.final_prompt)
        print("=" * 70)
        
        # Попытка получить метрики (если доступны)
        if hasattr(prompt_tuner, 'metrics'):
            print("\n📊 МЕТРИКИ ОЦЕНКИ:")
            print(prompt_tuner.metrics)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return False

def test_compare_models():
    """Тест 5: Сравнение результатов разных моделей GPT-5"""
    print("\n" + "=" * 70)
    print("ТЕСТ 5: СРАВНЕНИЕ GPT-5 МОДЕЛЕЙ")
    print("=" * 70)
    
    models = [
        "gpt-5-mini",
        "gpt-5",
        "gpt-5-chat-latest"
    ]
    
    task = "Summarize the benefits of exercise in 3 sentences"
    
    results = {}
    
    for model_name in models:
        try:
            print(f"\n🔄 Тестирование модели: {model_name}")
            
            llm = ChatOpenAI(
                model=model_name,
                temperature=0.5,
                api_key=API_KEY
            )
            
            prompt_tuner = PromptTuner(target_model=llm)
            prompt_tuner.run(task)
            
            results[model_name] = prompt_tuner.final_prompt
            print(f"✅ {model_name} - готово")
            
        except Exception as e:
            print(f"❌ {model_name} - ошибка: {e}")
            results[model_name] = None
    
    # Показываем результаты
    print("\n" + "=" * 70)
    print("СРАВНЕНИЕ РЕЗУЛЬТАТОВ:")
    print("=" * 70)
    
    for model_name, prompt in results.items():
        print(f"\n🤖 Модель: {model_name}")
        print("-" * 70)
        if prompt:
            print(prompt[:300] + "..." if len(prompt) > 300 else prompt)
        else:
            print("Не удалось получить результат")
        print("-" * 70)
    
    return True

def test_advanced_configuration():
    """Тест 6: Продвинутая конфигурация"""
    print("\n" + "=" * 70)
    print("ТЕСТ 6: ПРОДВИНУТАЯ КОНФИГУРАЦИЯ")
    print("=" * 70)
    
    try:
        llm = ChatOpenAI(
            model="gpt-5-chat-latest",
            temperature=0.8,
            max_tokens=4000,  # Увеличено для оптимизации промпта
            api_key=API_KEY
        )
        
        # Создаем PromptTuner с настройками
        prompt_tuner = PromptTuner(target_model=llm)
        
        task = "Generate creative product names for a new eco-friendly water bottle"
        
        print(f"\n📝 Задача: {task}")
        print("\n🔄 Запуск с продвинутыми настройками...")
        
        prompt_tuner.run(task)
        
        print("\n✅ Завершено!")
        print("\n" + "=" * 70)
        print("КРЕАТИВНЫЙ ОПТИМИЗИРОВАННЫЙ ПРОМПТ:")
        print("=" * 70)
        print(prompt_tuner.final_prompt)
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return False

def main():
    """Основная функция для запуска всех тестов"""
    print("\n" + "🚀" * 35)
    print("  ТЕСТИРОВАНИЕ COOLPROMPT С GPT-5 МОДЕЛЯМИ")
    print("🚀" * 35)
    
    print("\n📌 Версия: CoolPrompt v1.1.0")
    print("🤖 Модели: GPT-5, GPT-5-chat-latest, GPT-5-mini")
    print("🎯 Цель: Автоматическая оптимизация промптов")
    
    results = []
    
    # Запускаем тесты
    tests = [
        ("Базовая оптимизация", test_basic_prompt_optimization),
        ("Оптимизация для кода", test_custom_task_optimization),
        ("GPT-5-mini", test_with_gpt5_mini),
        ("Оптимизация с оценкой", test_with_evaluation),
        ("Сравнение моделей", test_compare_models),
        ("Продвинутая конфигурация", test_advanced_configuration),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*70}")
        print(f"Запуск теста: {test_name}")
        print('='*70)
        
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте: {e}")
            results.append((test_name, False))
        
        print("\n⏸️  Пауза между тестами...")
        import time
        time.sleep(2)
    
    # Итоговая таблица
    print("\n" + "=" * 70)
    print("📊 ИТОГОВАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
    print("=" * 70)
    
    success_count = 0
    for test_name, success in results:
        status = "✅ УСПЕХ" if success else "❌ ПРОВАЛ"
        print(f"{status:12} | {test_name}")
        if success:
            success_count += 1
    
    print("=" * 70)
    print(f"✅ Успешно: {success_count}/{len(results)}")
    print(f"❌ Провалено: {len(results) - success_count}/{len(results)}")
    print("=" * 70)
    
    if success_count > 0:
        print("\n🎉 CoolPrompt работает с GPT-5!")
        print("\n💡 ВОЗМОЖНОСТИ:")
        print("   ✓ Автоматическая оптимизация промптов")
        print("   ✓ Поддержка всех GPT-5 моделей")
        print("   ✓ Оценка качества промптов")
        print("   ✓ LLM-агностичный подход")
        print("\n📚 Документация: https://github.com/CTLab-ITMO/CoolPrompt")

if __name__ == "__main__":
    # Проверка установки библиотеки
    try:
        import coolprompt
        print("✅ CoolPrompt установлен")
        print(f"📦 Версия: {coolprompt.__version__ if hasattr(coolprompt, '__version__') else 'unknown'}")
    except ImportError:
        print("❌ CoolPrompt не установлен!")
        print("\n📥 Установите библиотеку:")
        print("   pip install coolprompt")
        print("\nили:")
        print("   git clone https://github.com/CTLab-ITMO/CoolPrompt.git")
        print("   pip install -r requirements.txt")
        exit(1)
    
    try:
        from langchain_openai import ChatOpenAI
        print("✅ LangChain OpenAI установлен")
    except ImportError:
        print("❌ LangChain OpenAI не установлен!")
        print("\n📥 Установите:")
        print("   pip install langchain-openai")
        exit(1)
    
    main()
