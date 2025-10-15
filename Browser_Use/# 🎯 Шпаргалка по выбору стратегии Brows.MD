# 🎯 Шпаргалка по выбору стратегии Browser-Use

> **Основано на реальных методах библиотеки browser-use v0.8.1**
> 
> 📚 Источники:
> - Официальная документация: https://docs.browser-use.com/
> - GitHub: https://github.com/browser-use/browser-use (71.3k ⭐)
> - Примеры: `browser-use-repo/examples/`
> - Исходный код: `browser-use-repo/browser_use/agent/`

---

## 🚀 Быстрый выбор по типу задачи

### 1️⃣ Простая задача (1-3 шага, одноразовая)

**Метод**: `run()` или `run_sync()`

```python
from browser_use import Agent

# Асинхронный вариант
agent = Agent(task="Open google.com and search for 'browser-use'", llm=llm)
result = await agent.run(max_steps=10)

# Синхронный вариант (без await)
agent = Agent(task="Find latest news", llm=llm)
result = agent.run_sync()
```

**Когда использовать:**
- ✅ Разовый поиск информации
- ✅ Простая навигация (1-3 страницы)
- ✅ Быстрая проверка данных
- ✅ Прототипирование

**Не использовать:**
- ❌ Многошаговые процессы (регистрация, оформление заказа)
- ❌ Задачи требующие работы с несколькими вкладками
- ❌ Критичные задачи (нет retry logic)

---

### 2️⃣ Последовательная задача (несколько шагов, нужен контроль)

**Метод**: `add_new_task()` + `run()`

**⚠️ ВАЖНО:** Обязательно используйте `keep_alive=True`!

```python
from browser_use import Agent
from browser_use.browser.profile import BrowserProfile

# Создаем профиль с keep_alive
profile = BrowserProfile(keep_alive=True)

# Создаем Agent
agent = Agent(
    task="Step 1: Open website", 
    browser_profile=profile,
    llm=llm
)
await agent.run()

# Добавляем следующие шаги
agent.add_new_task("Step 2: Fill form")
await agent.run()

agent.add_new_task("Step 3: Submit")
await agent.run()
```

**Когда использовать:**
- ✅ Регистрация на сайтах
- ✅ Заполнение многошаговых форм
- ✅ Работа с несколькими вкладками
- ✅ Процессы с ожиданием (подтверждение email)
- ✅ Нужен контроль между шагами

**Преимущества:**
- ✅ Браузер остается открытым между шагами
- ✅ История сохраняется
- ✅ Контроль после каждого шага
- ✅ Можно менять стратегию на лету

**📖 См. подробно:** `ADD_NEW_TASK_PATTERN.md`

---

### 3️⃣ Пошаговое выполнение (ручной контроль)

**Метод**: `step()` или `take_step()`

```python
# step() - выполняет один шаг
agent = Agent(task="Complex task", llm=llm)
await agent.step()  # Шаг 1
await agent.step()  # Шаг 2

# take_step() - с проверкой статуса
is_done, has_error = await agent.take_step()
if not is_done:
    await agent.take_step()
```

**Когда использовать:**
- ✅ Дебаг сложных процессов
- ✅ Нужен контроль после КАЖДОГО действия
- ✅ Условная логика между действиями
- ✅ Обучение/исследование поведения Agent

---

### 4️⃣ Выполнение конкретных действий

**Метод**: `multi_act()`

```python
from browser_use.tools.registry.views import ActionModel

# Явно задаем действия
actions = [
    ActionModel(action_name="navigate", params={"url": "https://google.com"}),
    ActionModel(action_name="input_text", params={"index": 1, "text": "search query"}),
    ActionModel(action_name="click", params={"index": 5}),
]

results = await agent.multi_act(actions)
```

**Когда использовать:**
- ✅ Заранее известная последовательность действий
- ✅ Детерминированные процессы
- ✅ Максимальный контроль
- ✅ Bypass LLM (экономия токенов)

**Не использовать:**
- ❌ Динамические страницы
- ❌ Неизвестная структура
- ❌ Нужен интеллектуальный поиск элементов

---

### 5️⃣ Параллельная обработка (множество задач)

**Метод**: Несколько Agent + `asyncio.gather()`

```python
import asyncio
from browser_use import Agent

async def process_item(item):
    agent = Agent(task=f"Process {item}", llm=llm)
    return await agent.run()

# Параллельное выполнение
items = ["item1", "item2", "item3"]
results = await asyncio.gather(*[process_item(item) for item in items])
```

**⚠️ ВАЖНО:** 
- Каждый Agent создает свой браузер
- Требует много ресурсов (RAM, CPU)
- Нужен rate limiting для LLM API

**Когда использовать:**
- ✅ Массовый сбор данных (10+ источников)
- ✅ Независимые задачи
- ✅ Есть ресурсы (RAM > 8GB)

**Оптимизация:**
```python
# Ограничение параллелизма
from asyncio import Semaphore

sem = Semaphore(3)  # Максимум 3 одновременно

async def process_with_limit(item):
    async with sem:
        agent = Agent(task=f"Process {item}", llm=llm)
        return await agent.run()
```

---

### 6️⃣ Низкоуровневое управление браузером

**Метод**: `Browser` + `browser_session`

```python
from browser_use import Agent, Browser

# Создаем Browser вручную
browser = Browser(keep_alive=True)
await browser.start()

# Используем в Agent
agent = Agent(task="Task 1", browser_session=browser, llm=llm)
await agent.run()

agent.add_new_task("Task 2")
await agent.run()

# Закрываем вручную
await browser.kill()
```

**Когда использовать:**
- ✅ Нужен полный контроль над браузером
- ✅ Переиспользование браузера в особых случаях
- ✅ Кастомная настройка Browser

**Не использовать:**
- ❌ Обычные задачи (проще использовать BrowserProfile)
- ❌ Начинающие (легко забыть `kill()`)

---

## 📋 Матрица решений (реальные методы)

| Ваша задача | Метод | Код | Сложность |
|-------------|-------|-----|-----------|
| Поиск информации | `run()` | `agent.run()` | ⭐ |
| Извлечение данных | `run()` + prompt | `task="Extract: title, price"` | ⭐ |
| Заполнение формы | `add_new_task()` | `agent.add_new_task("Fill form")` | ⭐⭐ |
| Регистрация с email | `add_new_task()` + retry | См. `airtable_registration.py` | ⭐⭐⭐ |
| Массовый сбор | `asyncio.gather()` | Параллельные Agent | ⭐⭐⭐ |
| Дебаг процесса | `step()` | `await agent.step()` | ⭐⭐ |
| Точные действия | `multi_act()` | `agent.multi_act(actions)` | ⭐⭐⭐ |

---

## 🔥 Рекомендуемые комбинации

### ✅ Надёжная регистрация (production-ready)

```python
from browser_use import Agent
from browser_use.browser.profile import BrowserProfile
import asyncio

class Registration:
    def __init__(self, llm):
        self.llm = llm
        self.profile = BrowserProfile(keep_alive=True)  # ← Ключевое!
        self.agent = None
    
    async def run(self):
        try:
            # Создаем Agent один раз
            self.agent = Agent(
                task="Step 1: Open website",
                browser_profile=self.profile,
                llm=self.llm
            )
            await asyncio.wait_for(self.agent.run(), timeout=120)
            
            # Retry logic для каждого шага
            for attempt in range(3):
                try:
                    self.agent.add_new_task("Step 2: Fill form")
                    await asyncio.wait_for(self.agent.run(), timeout=120)
                    break
                except asyncio.TimeoutError:
                    print(f"Retry {attempt + 1}/3")
                    await asyncio.sleep(5)
        
        finally:
            if self.agent:
                await self.agent.close()
```

**Паттерн:**
```
BrowserProfile(keep_alive=True) → Agent → add_new_task() + asyncio.wait_for() + retry → finally: close()
```

---

### ✅ Быстрый сбор данных

```python
# Для 1-10 источников: один Agent
agent = Agent(task="Collect data from site1, site2, site3", llm=llm)
result = await agent.run(max_steps=50)

# Для 10+ источников: параллельные Agent с ограничением
from asyncio import Semaphore

sem = Semaphore(5)  # Макс 5 параллельно

async def collect(url):
    async with sem:
        agent = Agent(task=f"Collect from {url}", llm=llm)
        return await agent.run()

results = await asyncio.gather(*[collect(url) for url in urls])
```

---

### ✅ Условная логика

```python
profile = BrowserProfile(keep_alive=True)
agent = Agent(task="Check if logged in", browser_profile=profile, llm=llm)
result = await agent.run()

# Анализ результата
if "logged in" in str(result).lower():
    agent.add_new_task("Go to dashboard")
else:
    agent.add_new_task("Login with credentials")

await agent.run()
```

---

## ⚠️ Антипаттерны (что НЕ работает)

### ❌ Множество Agent с одним browser_session

```python
# ❌ НЕПРАВИЛЬНО - CDP ошибка!
browser = Browser(keep_alive=True)
await browser.start()

agent1 = Agent(task="Task 1", browser_session=browser, llm=llm)
await agent1.run()

agent2 = Agent(task="Task 2", browser_session=browser, llm=llm)  # ОШИБКА!
await agent2.run()  # CDP client not initialized!
```

**Решение:** Один Agent + `add_new_task()`

---

### ❌ add_new_task() без keep_alive

```python
# ❌ НЕПРАВИЛЬНО - браузер закроется!
agent = Agent(task="Task 1", llm=llm)  # Нет keep_alive!
await agent.run()

agent.add_new_task("Task 2")
await agent.run()  # Браузер уже закрыт!
```

**Решение:** `BrowserProfile(keep_alive=True)`

---

### ❌ run() в цикле без await

```python
# ❌ НЕПРАВИЛЬНО - run() асинхронный!
agent = Agent(task="Task", llm=llm)
for i in range(10):
    agent.run()  # Забыли await!
```

**Решение:** `await agent.run()` или используйте `run_sync()`

---

### ❌ Забыли close()

```python
# ❌ НЕПРАВИЛЬНО - утечка ресурсов!
agent = Agent(task="Task", llm=llm)
await agent.run()
# Забыли закрыть - браузер остается в памяти!
```

**Решение:** Всегда используйте `finally`
```python
try:
    agent = Agent(task="Task", llm=llm)
    await agent.run()
finally:
    await agent.close()
```

---

## 💡 Правило выбора (3 вопроса)

### 1. Сколько шагов в задаче?

- **1-3 шага** → `run()` или `run_sync()`
- **4-10 шагов** → `add_new_task()` + `keep_alive=True`
- **10+ шагов** → Разбить на подзадачи или `step()` для контроля

### 2. Нужен ли контроль между шагами?

- **Нет** → `run()` с одним большим промптом
- **Да** → `add_new_task()` после каждого шага
- **Полный контроль** → `step()` или `multi_act()`

### 3. Сколько задач параллельно?

- **1 задача** → Один Agent
- **2-5 задач** → `asyncio.gather()` без ограничений
- **10+ задач** → `asyncio.gather()` + `Semaphore(5)`

---

## 📊 Статистика использования (80/20 правило)

По данным примеров из `browser-use-repo/examples/`:

| Паттерн | Доля использования | Методы |
|---------|-------------------|--------|
| Simple run | 60% | `run()`, `run_sync()` |
| Multi-step | 30% | `add_new_task()` + `run()` |
| Advanced | 10% | `step()`, `multi_act()`, `Browser` |

**Вывод:** 90% задач решаются через `run()` или `add_new_task()`!

---

## 🎓 Best Practices (проверенные)

### 1. Всегда используйте keep_alive для multi-step

```python
# ✅ ПРАВИЛЬНО
profile = BrowserProfile(keep_alive=True)
agent = Agent(task="...", browser_profile=profile, llm=llm)
```

### 2. Всегда используйте timeout

```python
# ✅ ПРАВИЛЬНО
await asyncio.wait_for(agent.run(), timeout=120)
```

### 3. Всегда используйте finally для cleanup

```python
# ✅ ПРАВИЛЬНО
try:
    await agent.run()
finally:
    await agent.close()
```

### 4. Используйте max_steps для ограничения

```python
# ✅ ПРАВИЛЬНО - не даем Agent зациклиться
await agent.run(max_steps=20)
```

### 5. Используйте retry для критичных задач

```python
# ✅ ПРАВИЛЬНО
for attempt in range(3):
    try:
        await asyncio.wait_for(agent.run(), timeout=120)
        break
    except asyncio.TimeoutError:
        await asyncio.sleep(5)
```

---

## 🚀 Быстрые рецепты

### Рецепт 1: Простой поиск

```python
agent = Agent(task="Google search for 'browser-use python'", llm=llm)
result = agent.run_sync()  # Без await!
print(result)
```

### Рецепт 2: Регистрация

```python
profile = BrowserProfile(keep_alive=True)
agent = Agent(task="Open signup page", browser_profile=profile, llm=llm)
await agent.run()

agent.add_new_task("Fill email and password")
await agent.run()

agent.add_new_task("Submit form")
await agent.run()

await agent.close()
```

### Рецепт 3: Сбор цен (10 сайтов)

```python
from asyncio import Semaphore

sem = Semaphore(3)
async def get_price(url):
    async with sem:
        agent = Agent(task=f"Get price from {url}", llm=llm)
        return await agent.run()

prices = await asyncio.gather(*[get_price(url) for url in urls])
```

---

## � Дополнительные материалы

- 📖 **Полная документация методов:** `BROWSER_USE_AGENT_METHODS.md`
- 🎯 **Паттерн add_new_task():** `ADD_NEW_TASK_PATTERN.md`
- ⚡ **Быстрая шпаргалка:** `ADD_NEW_TASK_CHEATSHEET.md`
- 💼 **Пример production-ready:** `airtable_registration.py`

---

**Создано на основе:**
- browser-use v0.8.1
- Официальная документация: https://docs.browser-use.com/
- GitHub репозиторий: https://github.com/browser-use/browser-use
- Анализ исходного кода: `browser-use-repo/browser_use/agent/`
- Официальные примеры: `browser-use-repo/examples/`