"""
🔍 Анализ кода test_agent3_air.py с помощью GPT-5 Pro через PromptTuner

Задачи:
1. Полноценная защита от Cloudflare
2. Code Review (технический)
3. Business Logic Review (соответствие BUSINESS_LOGIC.md)

Использует CoolPrompt для создания оптимального промпта
"""
import os
import sys
from pathlib import Path
from coolprompt.assistant import PromptTuner
from langchain_openai import ChatOpenAI
from io import StringIO
import logging

# Подавляем NLTK логи
logging.getLogger('nltk').setLevel(logging.CRITICAL)

class SuppressNLTKDownload:
    def __enter__(self):
        self._original_stderr = sys.stderr
        sys.stderr = StringIO()
        return self
    
    def __exit__(self, *args):
        sys.stderr = self._original_stderr

import nltk
with SuppressNLTKDownload():
    try:
        nltk.download('wordnet', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        nltk.download('omw-1.4', quiet=True)
    except:
        pass

# API ключ
API_KEY = os.environ.get("OPENAI_API_KEY", "your-api-key-here")

def read_file_content(file_path: str) -> str:
    """Читает содержимое файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Ошибка чтения файла: {e}"

def create_comprehensive_review_task() -> str:
    """
    Создаёт комплексную задачу для GPT-5 Pro с анализом кода и бизнес-логики
    """
    
    # Пути к файлам
    base_path = Path(__file__).parent
    code_file = base_path / "test_agent3_air.py"
    business_logic_file = base_path / "BUSINESS_LOGIC.md"
    
    # Читаем содержимое файлов
    code_content = read_file_content(code_file)
    business_logic_content = read_file_content(business_logic_file)
    
    # Формируем задачу на русском языке
    task = f"""
# 🎯 КОМПЛЕКСНЫЙ АНАЛИЗ СИСТЕМЫ АВТОМАТИЧЕСКОЙ РЕГИСТРАЦИИ AIRTABLE

## 📋 КОНТЕКСТ

Ты — эксперт по веб-автоматизации, обходу систем защиты и архитектуре программного обеспечения.

Перед тобой стоит задача проанализировать Python-скрипт для автоматической регистрации на платформе Airtable, который использует:
- **Google Gemini 2.5 Computer Use API** для управления браузером через ИИ
- **Playwright** для браузерной автоматизации
- **playwright_stealth** для обхода антибот систем
- **Двухэтапную регистрацию**: получение временного email → регистрация → подтверждение

## 🚨 ОСНОВНЫЕ ПРОБЛЕМЫ

### Проблема 1: Блокировка Cloudflare
Скрипт **все еще наталкивается на блокировки Cloudflare**, несмотря на использование playwright_stealth.

**Текущая реализация защиты:**
```python
# Импорт stealth
from playwright_stealth import stealth_async

# Функция детекции блокировки
async def detect_cloudflare_block(page) -> tuple[bool, str]:
    # Проверяет признаки Cloudflare challenge
    # Ждет 10 секунд при обнаружении блока
    pass
```

**Что требуется:**
- Полноценная стратегия обхода Cloudflare на уровне 2025 года
- Комплексный подход: headers, cookies, fingerprinting, timing
- Рекомендации по дополнительным библиотекам/техникам
- Анализ слабых мест текущей реализации

### Проблема 2: Соответствие Бизнес-Логике
Необходимо проверить, что код **полностью реализует** бизнес-требования из документации.

## 📊 ВХОДНЫЕ ДАННЫЕ

### КОД СКРИПТА (test_agent3_air.py):
```python
{code_content[:15000]}
```

[... КОД ПРОДОЛЖАЕТСЯ - всего {len(code_content)} символов ...]

### БИЗНЕС-ЛОГИКА (BUSINESS_LOGIC.md):
```markdown
{business_logic_content}
```

---

## 🎯 ЗАДАЧИ ДЛЯ АНАЛИЗА

### ✅ ЗАДАЧА 1: ПОЛНОЦЕННАЯ ЗАЩИТА ОТ CLOUDFLARE

Проанализируй текущую реализацию и предложи **комплексное решение** для обхода Cloudflare, включая:

#### 1.1 Анализ текущей реализации
- Какие методы уже используются?
- Почему они недостаточны?
- Какие сигналы выдают автоматизацию?

#### 1.2 Browser Fingerprinting
- User-Agent (реалистичный и актуальный)
- WebGL fingerprint
- Canvas fingerprint
- Audio fingerprint
- Screen resolution и timezone
- Plugins и MIME types
- WebRTC leaks

#### 1.3 Network Level Protection
- IP rotation (рекомендации по прокси)
- TLS fingerprinting
- HTTP/2 fingerprinting
- Cookie handling
- Referer headers

#### 1.4 Behavioral Patterns
- Human-like timing (random delays)
- Mouse movements simulation
- Scroll patterns
- Focus events
- Keyboard timing

#### 1.5 Конкретные рекомендации
- Дополнительные Python библиотеки
- Playwright context options
- CDP (Chrome DevTools Protocol) команды
- Browser launch arguments
- Stealth plugins настройки

#### 1.6 Код-примеры
Предоставь готовые к использованию фрагменты кода на Python для:
- Инициализации браузера с максимальной защитой
- Функции обхода Cloudflare challenge
- Retry механизма при блокировке
- Ротации fingerprints

---

### ✅ ЗАДАЧА 2: CODE REVIEW (ТЕХНИЧЕСКИЙ АНАЛИЗ)

Проведи детальный технический аудит кода по следующим критериям:

#### 2.1 Архитектура и структура
- Модульность и разделение ответственности
- Наличие дублирования кода (DRY principle)
- Читаемость и документирование
- Соответствие PEP 8

#### 2.2 Обработка ошибок
- Правильность try-except блоков
- Логирование ошибок
- Graceful degradation
- Retry механизмы

#### 2.3 Асинхронность
- Корректное использование async/await
- Отсутствие blocking calls
- Race conditions
- Deadlocks потенциал

#### 2.4 Безопасность
- Валидация входных данных
- SQL injection риски (если есть)
- XSS уязвимости
- Secrets management

#### 2.5 Производительность
- Оптимальность алгоритмов
- Memory leaks
- Ненужные API calls
- Screenshot overhead

#### 2.6 Тестируемость
- Возможность unit-тестирования
- Mock-объекты
- Dependency injection

---

### ✅ ЗАДАЧА 3: BUSINESS LOGIC REVIEW

Проверь соответствие кода документу BUSINESS_LOGIC.md:

#### 3.1 Полный цикл регистрации (7 этапов)
Для каждого этапа проверь:
- ✓ Реализован ли в коде?
- ✓ Соответствует ли описанию?
- ✓ Есть ли отклонения?

**Этапы:**
1. Открытие Airtable
2. Получение temp-mail
3. Заполнение формы (с валидацией)
4. Создание аккаунта
5. Ожидание письма
6. Подтверждение email
7. Финальная проверка

#### 3.2 Обработка ошибок нейросети
- Агент стер поле → Проверяется ли перед submit?
- Email отклонен → Получается ли новый email?
- Дополнительные поля → Заполняются ли автоматически?
- Confirm не подтвердился → Переключается ли на Airtable?

#### 3.3 Rate Limit Control
- Соблюдается ли задержка 8 секунд между вызовами?
- Есть ли подсчет total API calls?
- Логируется ли timing?

#### 3.4 Гарантии успеха (7 пунктов)
- Валидация полей
- Обработка reject
- Адаптация к доп. полям
- Полная проверка Confirm
- Rate limit safe
- Retry mechanism
- State tracking

#### 3.5 Метрики
- Соответствуют ли время выполнения целевым показателям?
- Соблюдается ли Success Rate?

---

## 📤 ФОРМАТ ОТВЕТА

Структурируй ответ следующим образом:

### 1️⃣ CLOUDFLARE PROTECTION (ПРИОРИТЕТ 1)

**1.1 Проблемы текущей реализации:**
- [Список выявленных проблем]

**1.2 Комплексное решение:**
```python
# Готовый к использованию код
# С комментариями на русском
```

**1.3 Дополнительные рекомендации:**
- Библиотеки для установки
- Настройки Playwright
- Сервисы для прокси (если нужны)

**1.4 Таблица эффективности:**
| Метод | Эффективность | Сложность | Стоимость |
|-------|---------------|-----------|-----------|
| ...   | ...           | ...       | ...       |

---

### 2️⃣ CODE REVIEW

**2.1 Критичные проблемы (нужно исправить срочно):**
- [Список с примерами кода]

**2.2 Некритичные замечания (можно отложить):**
- [Список]

**2.3 Рекомендации по улучшению:**
- [Конкретные предложения с кодом]

---

### 3️⃣ BUSINESS LOGIC REVIEW

**3.1 Соответствие этапам регистрации:**
| Этап | Статус | Комментарий |
|------|--------|-------------|
| 1    | ✅/❌  | ...         |

**3.2 Несоответствия бизнес-требованиям:**
- [Детальное описание]

**3.3 Предложения по доработке:**
- [Конкретные шаги]

---

### 4️⃣ ИТОГОВЫЕ РЕКОМЕНДАЦИИ

**Приоритет 1 (критично):**
1. ...
2. ...

**Приоритет 2 (важно):**
1. ...

**Приоритет 3 (желательно):**
1. ...

---

## 🎯 ТРЕБОВАНИЯ К АНАЛИЗУ

1. **Глубина:** Анализируй на уровне senior-разработчика
2. **Практичность:** Все рекомендации должны быть реализуемы
3. **Код-примеры:** Предоставляй готовые решения на Python
4. **Русский язык:** Весь ответ на русском, код с русскими комментариями
5. **Структурированность:** Используй таблицы, списки, эмодзи для читаемости
6. **Ссылки:** Где возможно, давай ссылки на документацию

---

Начинай анализ! 🚀
"""
    
    return task


def main():
    """
    Основная функция - запускает оптимизацию промпта через PromptTuner
    """
    print("=" * 80)
    print("🔍 КОМПЛЕКСНЫЙ АНАЛИЗ: CLOUDFLARE PROTECTION + CODE REVIEW + BUSINESS LOGIC")
    print("=" * 80)
    print("\n📦 Используем: GPT-5 Pro + CoolPrompt PromptTuner")
    print("🎯 Цель: Создать оптимальный промпт для глубокого анализа\n")
    
    try:
        # Создаем модель GPT-5 Pro
        print("🤖 Инициализация GPT-5 Pro...")
        llm = ChatOpenAI(
            model="gpt-5-pro",  # или "gpt-5" если pro не доступен
            temperature=0.3,    # Низкая температура для точного анализа
            api_key=API_KEY
        )
        
        # Инициализируем PromptTuner
        print("🔧 Настройка PromptTuner...")
        prompt_tuner = PromptTuner(target_model=llm)
        
        # Создаем задачу
        print("📝 Подготовка задачи для анализа...")
        task = create_comprehensive_review_task()
        
        print(f"\n📊 Размер задачи: {len(task)} символов")
        print(f"📄 Файлы включены:")
        print(f"   - test_agent3_air.py")
        print(f"   - BUSINESS_LOGIC.md")
        
        print("\n" + "=" * 80)
        print("🔄 ЗАПУСК ОПТИМИЗАЦИИ ПРОМПТА...")
        print("=" * 80)
        print("⏱️  Это может занять 1-2 минуты...\n")
        
        # Запускаем оптимизацию
        prompt_tuner.run(task)
        
        print("\n" + "=" * 80)
        print("✅ ОПТИМИЗАЦИЯ ЗАВЕРШЕНА!")
        print("=" * 80)
        
        # Сохраняем результат
        output_file = Path(__file__).parent / "OPTIMIZED_REVIEW_PROMPT.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 🎯 ОПТИМИЗИРОВАННЫЙ ПРОМПТ ДЛЯ GPT-5 PRO\n\n")
            f.write("## 📋 Создано с помощью CoolPrompt PromptTuner\n\n")
            f.write("---\n\n")
            f.write(prompt_tuner.final_prompt)
        
        print(f"\n💾 Результат сохранен в: {output_file}")
        print("\n" + "=" * 80)
        print("📄 ОПТИМИЗИРОВАННЫЙ ПРОМПТ:")
        print("=" * 80)
        print(prompt_tuner.final_prompt)
        print("=" * 80)
        
        print("\n✨ ГОТОВО!")
        print("\n💡 Следующие шаги:")
        print("   1. Скопируй оптимизированный промпт из файла OPTIMIZED_REVIEW_PROMPT.md")
        print("   2. Отправь его GPT-5 Pro для анализа")
        print("   3. Получи детальные рекомендации по защите от Cloudflare и улучшению кода")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print(f"Тип ошибки: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
