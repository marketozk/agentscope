"""
🔍 КОМПАКТНАЯ ВЕРСИЯ: Анализ защиты от Cloudflare для test_agent3_air.py

Использует CoolPrompt PromptTuner для создания оптимального промпта
Фокус на Cloudflare bypass + критичные проблемы кода
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

API_KEY = os.environ.get("OPENAI_API_KEY", "your-api-key-here")


def create_cloudflare_review_task() -> str:
    """Создает задачу для анализа защиты от Cloudflare"""
    
    task = """
🎯 ЗАДАЧА: Экспертный анализ защиты от Cloudflare в Python скрипте автоматизации браузера

## КОНТЕКСТ
Python скрипт для автоматической регистрации на Airtable использует:
- Playwright для браузерной автоматизации
- Google Gemini 2.5 Computer Use API для AI-управления
- playwright_stealth для обхода антибот систем
- Двухэтапную регистрацию: temp-mail → регистрация → подтверждение

## ПРОБЛЕМА
Скрипт **все еще блокируется Cloudflare**, несмотря на использование stealth плагина.

## ТЕКУЩАЯ РЕАЛИЗАЦИЯ ЗАЩИТЫ

```python
# 1. Импорт stealth
from playwright_stealth import stealth_async

# 2. Функция детекции блокировки
async def detect_cloudflare_block(page) -> tuple[bool, str]:
    title = await page.title()
    body_text = await page.evaluate("() => document.body.innerText")
    
    indicators = []
    if "Attention Required" in title and "Cloudflare" in title:
        indicators.append("title:Attention Required | Cloudflare")
    if "Sorry, you have been blocked" in body_text:
        indicators.append("text:blocked")
    if "Cloudflare Ray ID" in body_text:
        indicators.append("text:ray_id")
    
    # Проверка пустой страницы (признак блока)
    body_html_size = await page.evaluate("() => document.body.innerHTML.length")
    if body_html_size < 100:
        indicators.append(f"html_size:{body_html_size} (possible_block)")
    
    blocked = len(indicators) > 0
    return blocked, ", ".join(indicators)

# 3. Обработка блокировки (примитивная)
blocked, signal = await detect_cloudflare_block(page)
if blocked:
    print(f"🛡️ Обнаружен Cloudflare блок: {signal}")
    await asyncio.sleep(10)  # Просто ждём 10 секунд
    blocked, signal = await detect_cloudflare_block(page)
    if blocked:
        return {"status": "ERROR", "reason": "Cloudflare block"}
```

## БИЗНЕС-ТРЕБОВАНИЯ

Из документа BUSINESS_LOGIC.md:
- ✅ Регистрация должна проходить в 90-120 секунд
- ✅ Success Rate: 85-95%
- ✅ Обход Cloudflare критичен для работы системы
- ✅ Необходим human-like behavior (клики, скроллинг, timing)
- ✅ Retry механизм при блокировке

## ЧТО ТРЕБУЕТСЯ

### 1️⃣ АНАЛИЗ ПРОБЛЕМ
Определи слабые места текущей защиты:
- Какие сигналы выдают автоматизацию?
- Почему playwright_stealth недостаточно?
- Что именно детектирует Cloudflare?

### 2️⃣ КОМПЛЕКСНОЕ РЕШЕНИЕ (2025 год, актуальное)

Предложи полную стратегию обхода включающую:

**A. Browser Fingerprinting**
- User-Agent (реалистичный Windows/Chrome)
- WebGL, Canvas, Audio fingerprints
- Screen resolution, timezone, языки
- Plugins, MIME types
- WebRTC leak prevention

**B. Network Protection**
- HTTP headers (realistic набор)
- Cookie handling
- TLS fingerprinting
- HTTP/2 использование

**C. Behavioral Patterns**
- Random delays (human-like timing)
- Mouse movements (если возможно через CDP)
- Scroll simulation
- Focus/blur events

**D. Playwright Configuration**
- Browser launch args для stealth
- Context options
- CDP commands для anti-detection
- Viewport и screen настройки

### 3️⃣ ГОТОВЫЙ КОД

Предоставь Python код для:

```python
# A. Функция инициализации stealth браузера
async def create_stealth_browser():
    # Полная настройка с максимальной защитой
    pass

# B. Функция обхода Cloudflare challenge
async def bypass_cloudflare_if_detected(page):
    # Умная обработка блокировки
    pass

# C. Retry механизм с ротацией fingerprints
async def navigate_with_cloudflare_bypass(page, url, max_retries=3):
    # Навигация с автоматическим retry
    pass
```

### 4️⃣ ДОПОЛНИТЕЛЬНЫЕ ИНСТРУМЕНТЫ

Рекомендуй:
- Python библиотеки (кроме playwright_stealth)
- Playwright расширения/плагины
- CDP (Chrome DevTools Protocol) команды
- Прокси сервисы (если нужны для IP rotation)
- Captcha solving сервисы (если нужны)

### 5️⃣ CODE REVIEW КРИТИЧНЫХ ПРОБЛЕМ

Проанализируй фрагменты кода на:
- Race conditions в async функциях
- Memory leaks (скриншоты накапливаются?)
- Отсутствие timeout'ов
- Неправильная обработка ошибок
- Проблемы с валидацией URL

## ФОРМАТ ОТВЕТА

Структурируй ответ так:

### 📊 1. ПРОБЛЕМЫ ТЕКУЩЕЙ РЕАЛИЗАЦИИ
[Список с объяснениями]

### 🛡️ 2. КОМПЛЕКСНАЯ ЗАЩИТА ОТ CLOUDFLARE

#### 2.1 Код инициализации браузера
```python
# С комментариями на русском
```

#### 2.2 Код обхода блокировки
```python
# С комментариями на русском
```

#### 2.3 Retry механизм
```python
# С комментариями на русском
```

### 📦 3. ИНСТРУМЕНТЫ И БИБЛИОТЕКИ
| Инструмент | Назначение | Установка | Сложность |
|------------|-----------|-----------|-----------|

### ⚠️ 4. КРИТИЧНЫЕ ПРОБЛЕМЫ В КОДЕ
[Список с примерами и решениями]

### 🎯 5. ИТОГОВЫЙ ЧЕКЛИСТ ВНЕДРЕНИЯ
- [ ] Шаг 1: ...
- [ ] Шаг 2: ...
- [ ] Шаг 3: ...

---

ТРЕБОВАНИЯ:
✓ Ответ на русском языке
✓ Код с русскими комментариями
✓ Практичные решения, которые работают в 2025 году
✓ Примеры готовые к copy-paste
✓ Таблицы для наглядности
✓ Ссылки на документацию где уместно

Анализируй как senior Python developer с опытом web scraping! 🚀
"""
    
    return task


def main():
    """Основная функция"""
    print("=" * 80)
    print("🔍 АНАЛИЗ: CLOUDFLARE PROTECTION + CODE REVIEW")
    print("=" * 80)
    print("\n📦 GPT-5 Pro + CoolPrompt PromptTuner")
    print("🎯 Фокус: Обход Cloudflare + критичные проблемы\n")
    
    try:
        print("🤖 Инициализация GPT-5 Pro...")
        llm = ChatOpenAI(
            model="gpt-5-pro",
            temperature=0.3,
            api_key=API_KEY
        )
        
        print("🔧 Настройка PromptTuner...")
        prompt_tuner = PromptTuner(target_model=llm)
        
        print("📝 Подготовка задачи...")
        task = create_cloudflare_review_task()
        
        print(f"\n📊 Размер задачи: {len(task)} символов")
        
        print("\n" + "=" * 80)
        print("🔄 ЗАПУСК ОПТИМИЗАЦИИ ПРОМПТА...")
        print("=" * 80)
        print("⏱️  Ожидайте 1-2 минуты...\n")
        
        prompt_tuner.run(task)
        
        print("\n" + "=" * 80)
        print("✅ ОПТИМИЗАЦИЯ ЗАВЕРШЕНА!")
        print("=" * 80)
        
        # Сохраняем результат
        output_file = Path(__file__).parent / "CLOUDFLARE_BYPASS_PROMPT.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 🛡️ ОПТИМИЗИРОВАННЫЙ ПРОМПТ: ЗАЩИТА ОТ CLOUDFLARE\n\n")
            f.write("## 📋 Создано с помощью CoolPrompt PromptTuner\n\n")
            f.write("### 🎯 Цель: Комплексный обход Cloudflare в Playwright + Code Review\n\n")
            f.write("---\n\n")
            f.write(prompt_tuner.final_prompt)
        
        print(f"\n💾 Результат: {output_file}")
        print("\n" + "=" * 80)
        print("📄 ОПТИМИЗИРОВАННЫЙ ПРОМПТ:")
        print("=" * 80)
        print(prompt_tuner.final_prompt)
        print("=" * 80)
        
        print("\n✨ ГОТОВО!")
        print("\n💡 Следующие шаги:")
        print("   1. Открой файл: CLOUDFLARE_BYPASS_PROMPT.md")
        print("   2. Скопируй оптимизированный промпт")
        print("   3. Отправь GPT-5 Pro для анализа")
        print("   4. Получи готовое решение для обхода Cloudflare")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print(f"Тип: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
