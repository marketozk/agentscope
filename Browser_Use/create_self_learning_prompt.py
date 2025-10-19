"""
🧠 Генератор оптимизированного промпта для самообучающегося агента
Использует CoolPrompt для создания лучшего промпта для GPT-5

Что делает:
1. Создает базовый промпт для задачи самообучения
2. Использует CoolPrompt (генетический алгоритм) для оптимизации
3. Сохраняет финальный оптимизированный промпт в файл
4. Этот промпт можно использовать для переделки test_agent3_air.py
"""
import os
import sys
import logging
from io import StringIO
from pathlib import Path
from datetime import datetime

# Подавляем NLTK логи
logging.getLogger('nltk').setLevel(logging.CRITICAL)

class SuppressNLTKDownload:
    def __enter__(self):
        self._original_stderr = sys.stderr
        sys.stderr = StringIO()
        return self
    
    def __exit__(self, *args):
        sys.stderr = self._original_stderr

# Импорт NLTK данных (тихо)
import nltk
with SuppressNLTKDownload():
    try:
        nltk.download('wordnet', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        nltk.download('omw-1.4', quiet=True)
    except:
        pass

from coolprompt.assistant import PromptTuner
from langchain_openai import ChatOpenAI

# API ключ OpenAI
API_KEY = os.environ.get("OPENAI_API_KEY", "your-api-key-here")

def create_base_prompt():
    """Создает базовый промпт для самообучающегося агента"""
    
    base_prompt = """
Задача: Добавить систему самообучения в агента автоматической регистрации в Airtable.

КОНТЕКСТ:
У меня есть рабочий скрипт test_agent3_air.py (~2600 строк), который:
- Использует Gemini Computer Use API для управления браузером через Playwright
- Автоматически регистрирует аккаунты в Airtable
- Проходит весь процесс: получение email → регистрация → подтверждение → онбординг (10+ шагов)
- Работает стабильно, но каждый раз выполняет одинаковую последовательность действий

ПРОБЛЕМА:
Агент не учится на опыте. Он не запоминает:
- Какие действия работают быстрее
- Какие селекторы более надежные
- Какие таймауты оптимальны
- Альтернативные пути при ошибках

ЦЕЛЬ:
Добавить самообучение, чтобы агент:
1. **Собирал опыт** во время каждой регистрации (метрики, успешность, время)
2. **Сохранял знания** между запусками (персистентное хранилище)
3. **Применял оптимизации** в следующих запусках (использовал лучшие найденные стратегии)
4. **Экспериментировал** для поиска еще более эффективных путей

ОГРАНИЧЕНИЯ:
- НЕ переписывать весь код с нуля
- НЕ ломать существующую логику Computer Use + Playwright
- НЕ менять внешний интерфейс (функция register_airtable_account должна работать как раньше)
- Минимально инвазивная интеграция

СВОБОДА РЕШЕНИЯ:
Ты сам решаешь:
- Какую архитектуру использовать (классы, функции, декораторы и т.д.)
- Как хранить данные (JSON, SQLite, pickle и т.д.)
- Какие метрики собирать
- Как выбирать оптимальную стратегию
- Как балансировать эксплуатацию (использование лучших стратегий) vs исследование (поиск новых)

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:
После первой регистрации - агент работает как обычно.
После 5-10 регистраций - агент становится быстрее и надежнее.
После 20+ регистраций - агент работает оптимально, адаптируется к изменениям.

Твоя задача: придумать элегантное решение и показать КАК его интегрировать в существующий код test_agent3_air.py.
"""
    
    return base_prompt.strip()


def optimize_prompt_with_coolprompt(base_prompt: str, model_name: str = "gpt-5-chat-latest"):
    """
    Оптимизирует промпт с помощью CoolPrompt
    
    Args:
        base_prompt: Базовый промпт для оптимизации
        model_name: Модель GPT для использования
        
    Returns:
        Оптимизированный промпт
    """
    print("=" * 80)
    print("🧠 COOLPROMPT: ОПТИМИЗАЦИЯ ПРОМПТА ДЛЯ САМООБУЧАЮЩЕГОСЯ АГЕНТА")
    print("=" * 80)
    
    try:
        # Создаем модель GPT-5
        llm = ChatOpenAI(
            model=model_name,
            temperature=0.7,
            api_key=API_KEY,
            timeout=120  # Увеличенный таймаут для сложной задачи
        )
        
        print(f"\n✅ Модель инициализирована: {model_name}")
        print(f"📝 Длина базового промпта: {len(base_prompt)} символов")
        
        # Инициализируем PromptTuner
        prompt_tuner = PromptTuner(target_model=llm)
        
        print("\n🔄 Запуск генетической оптимизации промпта...")
        print("⏳ Это может занять 2-5 минут...")
        print("-" * 80)
        
        # Запускаем оптимизацию
        prompt_tuner.run(base_prompt)
        
        print("\n" + "=" * 80)
        print("✅ ОПТИМИЗАЦИЯ ЗАВЕРШЕНА!")
        print("=" * 80)
        
        optimized_prompt = prompt_tuner.final_prompt
        
        print(f"\n📊 СТАТИСТИКА:")
        print(f"   - Длина оптимизированного промпта: {len(optimized_prompt)} символов")
        print(f"   - Разница: {len(optimized_prompt) - len(base_prompt):+d} символов")
        
        return optimized_prompt
        
    except Exception as e:
        print(f"\n❌ ОШИБКА при оптимизации: {e}")
        print(f"   Тип ошибки: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
        print("\n⚠️  Возвращаем исходный промпт (без оптимизации)")
        return base_prompt


def save_prompt_to_file(prompt: str, filename: str = None):
    """Сохраняет промпт в файл с timestamp"""
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"optimized_prompt_self_learning_{timestamp}.txt"
    
    output_path = Path(__file__).parent / filename
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("🧠 ОПТИМИЗИРОВАННЫЙ ПРОМПТ ДЛЯ САМООБУЧАЮЩЕГОСЯ АГЕНТА\n")
        f.write("=" * 80 + "\n")
        f.write(f"Создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Модель: GPT-5\n")
        f.write(f"Метод: CoolPrompt (генетический алгоритм)\n")
        f.write("=" * 80 + "\n\n")
        f.write(prompt)
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("КАК ИСПОЛЬЗОВАТЬ:\n")
        f.write("=" * 80 + "\n")
        f.write("1. Скопируй этот промпт целиком\n")
        f.write("2. Отправь GPT-5 вместе с содержимым test_agent3_air.py\n")
        f.write("3. GPT-5 добавит систему самообучения в код\n")
        f.write("4. Протестируй новый код на 2-3 регистрациях\n")
        f.write("5. Система начнет собирать метрики и оптимизироваться\n")
        f.write("=" * 80 + "\n")
    
    print(f"\n💾 Промпт сохранен в: {output_path}")
    return output_path


def main():
    """Основная функция"""
    
    print("\n" + "=" * 80)
    print("🚀 ГЕНЕРАТОР ПРОМПТА ДЛЯ САМООБУЧАЮЩЕГОСЯ АГЕНТА")
    print("=" * 80)
    
    # Шаг 1: Создаем базовый промпт
    print("\n📝 Шаг 1: Создание базового промпта...")
    base_prompt = create_base_prompt()
    print(f"   ✅ Базовый промпт создан ({len(base_prompt)} символов)")
    
    # Шаг 2: Проверяем наличие OpenAI ключа
    use_coolprompt = False
    if API_KEY and API_KEY != "your-api-key-here":
        print(f"\n✅ OpenAI API ключ найден: {API_KEY[:8]}...{API_KEY[-4:]}")
        print("🧬 Будет использована оптимизация через CoolPrompt")
        use_coolprompt = True
    else:
        print("\n⚠️  OpenAI API ключ не найден")
        print("   Будет использован базовый промпт (без CoolPrompt оптимизации)")
        print("   Базовый промпт уже хорошо структурирован и готов к использованию!")
    
    # Шаг 3: Оптимизация (если есть ключ)
    if use_coolprompt:
        print("\n🧬 Шаг 2: Оптимизация с CoolPrompt...")
        print("⏳ Это может занять 2-5 минут...")
        final_prompt = optimize_prompt_with_coolprompt(base_prompt)
    else:
        print("\n✅ Шаг 2: Используем базовый промпт")
        final_prompt = base_prompt
    
    # Шаг 4: Сохраняем результат
    print("\n💾 Шаг 3: Сохранение результата...")
    output_file = save_prompt_to_file(final_prompt)
    
    # Финальный вывод
    print("\n" + "=" * 80)
    print("✅ ГОТОВО!")
    print("=" * 80)
    print(f"\n📄 Промпт сохранен в:")
    print(f"   {output_file}")
    print("\n📋 ЧТО ДЕЛАТЬ ДАЛЬШЕ:")
    print("   1. Открой файл с промптом")
    print("   2. Скопируй содержимое")
    print("   3. Отправь GPT-5 Pro вместе с test_agent3_air.py")
    print("   4. GPT-5 придумает и добавит систему самообучения")
    print("   5. Протестируй на нескольких регистрациях")
    print("\n" + "=" * 80)
    
    # Выводим превью промпта
    print("\n📄 ПРЕВЬЮ ПРОМПТА:")
    print("-" * 80)
    preview_lines = final_prompt.split('\n')[:30]
    print('\n'.join(preview_lines))
    if len(final_prompt.split('\n')) > 30:
        print("\n... (остальное в файле) ...")
    print("-" * 80)


if __name__ == "__main__":
    main()
