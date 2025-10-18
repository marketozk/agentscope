# 🛡️ ПРОМПТ: ЗАЩИТА ОТ CLOUDFLARE + CODE REVIEW

> **Готовый промпт для GPT-5 Pro**  
> Просто скопируй весь текст ниже и отправь в ChatGPT (GPT-5 Pro)

---

# 🎯 ЭКСПЕРТНЫЙ АНАЛИЗ: ОБХОД CLOUDFLARE В PLAYWRIGHT АВТОМАТИЗАЦИИ

## 📋 РОЛЬ

Ты — **senior Python developer** с 10+ летним опытом в:
- Web scraping и browser automation
- Обход антибот систем (Cloudflare, PerimeterX, DataDome)
- Playwright/Selenium advanced techniques
- Browser fingerprinting и stealth techniques
- Code review и архитектура ПО

---

## 🎯 ЗАДАЧА

Проанализируй Python скрипт автоматической регистрации на Airtable, который:
- Использует **Playwright** для браузерной автоматизации
- Использует **Google Gemini 2.5 Computer Use API** для AI-управления браузером
- Использует **playwright_stealth** для обхода антибот систем
- Реализует двухэтапную регистрацию: получение temp-mail → регистрация → подтверждение

---

## 🚨 ПРОБЛЕМА

**Скрипт все еще блокируется Cloudflare**, несмотря на использование playwright_stealth.

---

## 📊 ТЕКУЩАЯ РЕАЛИЗАЦИЯ

### 1️⃣ Импорт и настройка

```python
from playwright_stealth import stealth_async
from playwright.async_api import async_playwright

# Fallback если stealth не установлен
try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None
```

### 2️⃣ Функция детекции Cloudflare блокировки

```python
async def detect_cloudflare_block(page) -> tuple[bool, str]:
    """
    Проверяет признаки Cloudflare challenge/block
    """
    try:
        title = await page.title()
        body_text = await page.evaluate("""() => {
            try { return document.body ? document.body.innerText.slice(0, 4000) : ''; } 
            catch(e) { return ''; }
        }""")
        
        indicators = []
        
        # Признаки Cloudflare
        if title and ("Attention Required" in title) and ("Cloudflare" in title):
            indicators.append("title:Attention Required | Cloudflare")
        
        if body_text:
            if "Sorry, you have been blocked" in body_text:
                indicators.append("text:blocked")
            if "Cloudflare Ray ID" in body_text:
                indicators.append("text:ray_id")
            if "cf-challenge" in body_text or "cf-browser-verification" in body_text:
                indicators.append("text:cf_challenge")
        
        # Признак пустой страницы (может быть блок)
        body_html = await page.evaluate("""() => {
            try { return document.body ? document.body.innerHTML.length : 0; } 
            catch(e) { return 0; }
        }""")
        
        if body_html < 100 and not "temp-mail" in page.url.lower():
            indicators.append(f"html_size:{body_html} (possible_block)")
        
        # Проверка на наличие iframe (challenge)
        iframes = await page.evaluate("""() => {
            return document.querySelectorAll('iframe').length;
        }""")
        if iframes > 3:
            indicators.append(f"iframes:{iframes}")
        
        blocked = len(indicators) > 0
        return blocked, ", ".join(indicators)
        
    except Exception as e:
        print(f"⚠️ detect_cloudflare_block error: {e}")
        return False, ""
```

### 3️⃣ Обработка блокировки (текущая)

```python
# При навигации проверяем блокировку
blocked, signal = await detect_cloudflare_block(page)
if blocked:
    print(f"🛡️ Обнаружен Cloudflare блок: {signal}")
    log_cloudflare_event(phase="navigate", step=-1, action="navigate", 
                          url=page.url, signal=signal)
    
    # Простое ожидание (НЕЭФФЕКТИВНО!)
    print(f"⏳ Ждём прохождения Cloudflare (10 сек)...")
    await asyncio.sleep(10)
    
    # Повторная проверка
    blocked, signal = await detect_cloudflare_block(page)
    if blocked:
        print(f"❌ Cloudflare всё ещё блокирует")
        return {"status": "ERROR", "reason": "Cloudflare persistent block"}
```

---

## 🎯 ЧТО ТРЕБУЕТСЯ ОТ ТЕБЯ

### ✅ ЗАДАЧА 1: АНАЛИЗ ПРОБЛЕМ

Определи **конкретные слабости** текущей защиты:

1. Какие **fingerprints** выдают автоматизацию?
2. Почему **playwright_stealth недостаточно** в 2025 году?
3. Какие **behavioral patterns** отсутствуют?
4. Какие **network-level индикаторы** детектируются?
5. Что именно видит **Cloudflare** в этом скрипте?

---

### ✅ ЗАДАЧА 2: КОМПЛЕКСНОЕ РЕШЕНИЕ

Предложи **полную стратегию обхода Cloudflare 2025** включающую:

#### 🔐 A. Browser Fingerprinting Protection

**Что нужно замаскировать:**
- User-Agent (реалистичный Windows 11 + Chrome 131)
- WebGL renderer/vendor
- Canvas fingerprint
- Audio context fingerprint
- Screen resolution + color depth
- Timezone + language
- Plugins и MIME types
- WebRTC leaks (IP утечки)
- Battery API
- Hardware concurrency
- Device memory

**Формат ответа:**
```python
# Конкретный Python код с настройками
```

#### 🌐 B. Network-Level Protection

**Что нужно настроить:**
- HTTP headers (полный realistic набор)
- TLS fingerprinting (ja3/ja4)
- HTTP/2 prioritization
- Cookie handling (SameSite, Secure)
- Referer policy
- Origin headers

**Формат ответа:**
```python
# Playwright context options + custom headers
```

#### 🤖 C. Behavioral Patterns (Human-like)

**Что нужно симулировать:**
- Random delays между действиями (2-5 сек)
- Mouse movements (через CDP если возможно)
- Scroll patterns (плавный скроллинг)
- Focus/blur events
- Keyboard timing (не моментальный ввод)
- Page visibility API interactions

**Формат ответа:**
```python
# Функции для human-like behavior
```

#### ⚙️ D. Playwright Advanced Configuration

**Что настроить:**
- Browser launch arguments (--disable-blink-features=AutomationControlled и др.)
- Context options (viewport, user_agent, locale, timezone)
- CDP commands для маскировки automation
- stealth_async правильное применение
- Extra HTTP headers

**Формат ответа:**
```python
# Полная функция create_stealth_browser()
```

---

### ✅ ЗАДАЧА 3: ГОТОВЫЙ КОД

Предоставь **3 готовые функции** на Python:

#### Функция 1: Инициализация stealth браузера
```python
async def create_stealth_browser(
    headless: bool = False,
    proxy: Optional[str] = None
) -> tuple[Browser, BrowserContext, Page]:
    """
    Создает Playwright браузер с максимальной защитой от детекции.
    
    Returns:
        (browser, context, page) - готовые к использованию объекты
    """
    # ТУТ ТВОЙ КОД
    pass
```

#### Функция 2: Обход Cloudflare challenge
```python
async def bypass_cloudflare_if_detected(
    page: Page,
    max_wait_time: int = 30
) -> dict:
    """
    Умная обработка Cloudflare блокировки:
    - Детектирует challenge
    - Ждет автоматического прохождения
    - Симулирует human behavior
    - Возвращает статус
    """
    # ТУТ ТВОЙ КОД
    pass
```

#### Функция 3: Навигация с retry и bypass
```python
async def navigate_with_cloudflare_bypass(
    page: Page,
    url: str,
    max_retries: int = 3
) -> dict:
    """
    Навигация с автоматическим обходом Cloudflare:
    - Переходит на URL
    - Проверяет блокировку
    - Обходит challenge
    - Retry с экспоненциальной задержкой
    """
    # ТУТ ТВОЙ КОД
    pass
```

---

### ✅ ЗАДАЧА 4: ДОПОЛНИТЕЛЬНЫЕ ИНСТРУМЕНТЫ

Рекомендуй **конкретные решения** в формате таблицы:

| Инструмент/Библиотека | Назначение | Установка | Эффективность | Сложность |
|------------------------|-----------|-----------|---------------|-----------|
| playwright_stealth | Base stealth | `pip install ...` | 60% | Низкая |
| undetected-playwright | Advanced stealth | `pip install ...` | 85% | Средняя |
| ... | ... | ... | ... | ... |

**Категории:**
- Python библиотеки для stealth
- Playwright плагины/расширения
- CDP (Chrome DevTools Protocol) скрипты
- Прокси сервисы (для IP rotation)
- Captcha solving (если нужно)
- Browser profiles (для реалистичности)

---

### ✅ ЗАДАЧА 5: КРИТИЧНЫЕ ПРОБЛЕМЫ В КОДЕ

Найди и опиши **5-10 критичных проблем** в текущем коде:

**Формат:**
```
❌ ПРОБЛЕМА: [Название]
📍 Где: [Строка/функция]
🔍 Почему критично: [Объяснение]
✅ Решение:
[Код исправления]
```

**Что проверить:**
- Race conditions в async функциях
- Memory leaks (скриншоты, страницы не закрываются?)
- Отсутствие timeout'ов
- Неправильная обработка исключений
- Проблемы с валидацией данных
- Blocking operations в async коде
- Незащищенные API calls

---

## 📤 ФОРМАТ ИТОГОВОГО ОТВЕТА

Структурируй ответ **строго так**:

---

## 📊 1. АНАЛИЗ ПРОБЛЕМ ТЕКУЩЕЙ ЗАЩИТЫ

### 1.1 Fingerprinting индикаторы
- [Список того, что выдает автоматизацию]

### 1.2 Network индикаторы
- [Список подозрительных паттернов]

### 1.3 Behavioral индикаторы
- [Что отсутствует из human-like поведения]

### 1.4 Почему playwright_stealth недостаточно
- [Объяснение]

---

## 🛡️ 2. КОМПЛЕКСНОЕ РЕШЕНИЕ

### 2.1 Fingerprinting Protection (код)
```python
# Готовый код с комментариями на русском
```

### 2.2 Network Protection (код)
```python
# Готовый код с комментариями на русском
```

### 2.3 Behavioral Patterns (код)
```python
# Готовый код с комментариями на русском
```

### 2.4 Playwright Configuration (код)
```python
async def create_stealth_browser():
    # Полная реализация
    pass
```

---

## 🔧 3. ГОТОВЫЕ ФУНКЦИИ

### 3.1 Инициализация stealth браузера
```python
# Полный код функции create_stealth_browser()
```

### 3.2 Обход Cloudflare
```python
# Полный код функции bypass_cloudflare_if_detected()
```

### 3.3 Навигация с retry
```python
# Полный код функции navigate_with_cloudflare_bypass()
```

---

## 📦 4. ИНСТРУМЕНТЫ И БИБЛИОТЕКИ

| Инструмент | Назначение | Установка | Эффективность | Сложность | Цена |
|------------|-----------|-----------|---------------|-----------|------|
| ... | ... | ... | ... | ... | ... |

---

## ⚠️ 5. КРИТИЧНЫЕ ПРОБЛЕМЫ В КОДЕ

### Проблема 1: [Название]
❌ **Суть:** ...  
📍 **Где:** ...  
🔍 **Почему критично:** ...  
✅ **Решение:**
```python
# Код исправления
```

[Повтори для всех найденных проблем]

---

## 🎯 6. ИТОГОВЫЙ ЧЕКЛИСТ ВНЕДРЕНИЯ

### Приоритет 1 (Критично - внедрить сегодня):
- [ ] Установить библиотеки: `pip install ...`
- [ ] Заменить функцию инициализации браузера
- [ ] Добавить bypass_cloudflare_if_detected()
- [ ] ...

### Приоритет 2 (Важно - внедрить на неделе):
- [ ] Настроить behavioral patterns
- [ ] Добавить IP rotation через прокси
- [ ] ...

### Приоритет 3 (Улучшения):
- [ ] Оптимизировать timing
- [ ] Добавить метрики успешности
- [ ] ...

---

## 📚 7. ССЫЛКИ НА ДОКУМЕНТАЦИЮ

- Playwright anti-detection: [ссылка]
- CDP commands: [ссылка]
- Browser fingerprinting: [ссылка]
- Cloudflare bypass 2025: [ссылка]

---

## ✅ ТРЕБОВАНИЯ К ОТВЕТУ

1. ✅ **Весь ответ на русском языке**
2. ✅ **Код с русскими комментариями**
3. ✅ **Готовые к copy-paste решения** (не "заглушки", а рабочий код)
4. ✅ **Актуальные методы 2025 года** (не устаревшие техники)
5. ✅ **Практичность** (всё должно работать в реальном проекте)
6. ✅ **Таблицы для наглядности**
7. ✅ **Примеры с пояснениями**
8. ✅ **Ссылки на документацию** где уместно

---

**🚀 Начинай анализ!**

Действуй как senior Python developer с 10+ летним опытом web scraping и обхода антибот систем!
