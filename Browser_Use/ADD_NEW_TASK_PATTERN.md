# add_new_task() - Правильные паттерны использования

## 🎯 Главное правило

**ВСЕГДА используй `keep_alive=True` при работе с `add_new_task()`!**

Без этого браузер закроется после первого `run()`.

---

## ✅ Паттерн 1: BrowserProfile (РЕКОМЕНДУЕТСЯ)

### Код из официального примера

```python
from browser_use import Agent
from browser_use.browser.profile import BrowserProfile

# 1. Создаем профиль с keep_alive=True
profile = BrowserProfile(keep_alive=True)

# 2. Создаем Agent с этим профилем
agent = Agent(task="Go to reddit.com", browser_profile=profile, llm=llm)
await agent.run(max_steps=1)

# 3. Добавляем новые задачи и выполняем
while True:
    user_input = input('\n👤 New task or "q" to quit: ')
    agent.add_new_task(f'New task: {user_input}')
    await agent.run()
```

**Источник**: `browser-use-repo/examples/features/follow_up_tasks.py`

### Преимущества
- ✅ Простота использования
- ✅ Один объект профиля для всех задач
- ✅ Автоматическое управление браузером
- ✅ Поддержка всех настроек BrowserProfile

### Применение в нашем проекте

```python
class AirtableRegistration:
    def __init__(self, llm, max_retries=5):
        self.llm = llm
        self.agent = None
        self.browser_profile = BrowserProfile(keep_alive=True)  # ← КЛЮЧЕВОЕ!
    
    async def run(self):
        # Создаем Agent с профилем
        self.agent = Agent(
            task="Open https://airtable.com",
            llm=self.llm,
            browser_profile=self.browser_profile,  # ← ИСПОЛЬЗУЕМ ПРОФИЛЬ!
            use_vision=True
        )
        await self.agent.run()
        
        # Добавляем следующие задачи
        self.agent.add_new_task("Get temp email from temp-mail.io")
        await self.agent.run()
        
        self.agent.add_new_task("Fill registration form")
        await self.agent.run()
        
        # Браузер остается открытым! ✅
```

---

## ✅ Паттерн 2: Browser (низкоуровневый контроль)

### Код из официального примера

```python
from browser_use import Agent, Browser

async def main():
    # 1. Создаем Browser с keep_alive=True
    browser = Browser(keep_alive=True)
    await browser.start()
    
    # 2. Передаем browser_session в Agent
    agent = Agent(task='search for browser-use', browser_session=browser, llm=llm)
    await agent.run(max_steps=2)
    
    # 3. Добавляем новую задачу
    agent.add_new_task('return the title of first result')
    await agent.run()
    
    # 4. НЕ ЗАБЫВАЕМ закрыть браузер!
    await browser.kill()
```

**Источник**: `browser-use-repo/examples/features/follow_up_task.py`

### Преимущества
- ✅ Полный контроль над браузером
- ✅ Можно переиспользовать browser между Agent'ами (с осторожностью!)
- ✅ Явное управление жизненным циклом

### Недостатки
- ⚠️ Требуется ручное управление: `start()` и `kill()`
- ⚠️ Больше кода
- ⚠️ Легче забыть закрыть браузер

---

## ❌ Что НЕ работает

### Ошибка 1: Без keep_alive

```python
# ❌ НЕПРАВИЛЬНО - браузер закроется после первого run()!
agent = Agent(task="Open google.com", llm=llm)
await agent.run()

agent.add_new_task("Search something")  
await agent.run()  # ← ОШИБКА! Браузер уже закрыт!
```

**Проблема**: Браузер автоматически закрывается после завершения первого `run()`.

**Решение**: Использовать `BrowserProfile(keep_alive=True)` или `Browser(keep_alive=True)`.

---

### Ошибка 2: Множество Agent с одним browser_session

```python
# ❌ НЕПРАВИЛЬНО - CDP ошибки!
browser = Browser(keep_alive=True)
await browser.start()

agent1 = Agent(task="Task 1", browser_session=browser, llm=llm)
await agent1.run()

agent2 = Agent(task="Task 2", browser_session=browser, llm=llm)  # ← ОШИБКА!
await agent2.run()  # CDP client not initialized!
```

**Проблема**: CDP (Chrome DevTools Protocol) клиент не может быть переиспользован между Agent'ами напрямую.

**Решение**: Использовать **ОДИН Agent** + `add_new_task()`:

```python
# ✅ ПРАВИЛЬНО - один Agent, много задач
browser = Browser(keep_alive=True)
await browser.start()

agent = Agent(task="Task 1", browser_session=browser, llm=llm)
await agent.run()

agent.add_new_task("Task 2")  # ← ПРАВИЛЬНО!
await agent.run()
```

---

### Ошибка 3: add_new_task() без последующего run()

```python
# ❌ НЕПРАВИЛЬНО - задача не выполнится!
agent = Agent(task="Open google.com", llm=llm, browser_profile=profile)
await agent.run()

agent.add_new_task("Search something")
# Забыли вызвать run()! Задача НЕ выполнена!
```

**Решение**: Всегда вызывать `run()` после `add_new_task()`:

```python
# ✅ ПРАВИЛЬНО
agent.add_new_task("Search something")
await agent.run()  # ← Обязательно!
```

---

## 🔍 Как работает add_new_task() внутри

### Исходный код из browser_use/agent/service.py:

```python
def add_new_task(self, new_task: str) -> None:
    """Add a new task to the agent, keeping the same task_id as tasks are continuous"""
    # 1. Обновляем текущую задачу
    self.task = new_task
    
    # 2. Добавляем в историю сообщений
    self._message_manager.add_new_task(new_task)
    
    # 3. Помечаем как follow-up задачу
    self.state.follow_up_task = True
    
    # 4. Пересоздаем EventBus (для обработки событий)
    agent_id_suffix = str(self.id)[-4:].replace('-', '_')
    if agent_id_suffix and agent_id_suffix[0].isdigit():
        agent_id_suffix = 'a' + agent_id_suffix
    self.eventbus = EventBus(name=f'Agent_{agent_id_suffix}')
```

### Что происходит при add_new_task():

1. **Обновление задачи**: Новая задача становится текущей
2. **Сохранение в истории**: Добавляется в `<follow_up_user_request>` тег
3. **Флаг follow_up**: Агент понимает, что это продолжение работы
4. **Пересоздание EventBus**: Новый bus для обработки событий

### ⚠️ Важно понимать:

- `add_new_task()` **НЕ выполняет задачу** сразу
- Задача выполнится только при следующем `run()`
- EventBus пересоздается → могут быть warning'и "EventBus already exists"
- Браузер **НЕ закрывается**, если `keep_alive=True`

---

## 📊 Сравнение паттернов

| Аспект | BrowserProfile | Browser | Без keep_alive |
|--------|---------------|---------|----------------|
| **Простота** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Контроль** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| **Надежность** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ Не работает |
| **Рекомендуется** | ✅ ДА | ✅ Для сложных случаев | ❌ НЕТ |

---

## 🎓 Best Practices

### 1. Всегда используй keep_alive=True

```python
# ✅ ПРАВИЛЬНО
profile = BrowserProfile(keep_alive=True)
agent = Agent(task="...", browser_profile=profile)
```

### 2. Один Agent для всего workflow

```python
# ✅ ПРАВИЛЬНО - один Agent, все задачи
class MyAutomation:
    def __init__(self, llm):
        self.agent = None
        self.profile = BrowserProfile(keep_alive=True)
    
    async def run(self):
        # Создаем Agent один раз
        self.agent = Agent(task="Step 1", browser_profile=self.profile, llm=llm)
        await self.agent.run()
        
        # Все остальные шаги через add_new_task()
        self.agent.add_new_task("Step 2")
        await self.agent.run()
        
        self.agent.add_new_task("Step 3")
        await self.agent.run()
```

### 3. Обрабатывай таймауты и ошибки

```python
# ✅ ПРАВИЛЬНО - с timeout и retry
for attempt in range(max_retries):
    try:
        self.agent.add_new_task(task)
        await asyncio.wait_for(self.agent.run(), timeout=120)
        break
    except asyncio.TimeoutError:
        print(f"Timeout, retry {attempt + 1}")
        await asyncio.sleep(5)
```

### 4. Всегда закрывай Agent в finally

```python
# ✅ ПРАВИЛЬНО - cleanup в finally
try:
    agent = Agent(task="...", browser_profile=profile, llm=llm)
    await agent.run()
    # ... работа ...
finally:
    if agent:
        await agent.close()
```

### 5. Используй явные промпты для управления вкладками

```python
# ✅ ПРАВИЛЬНО - явно указываем про вкладки
task = """
IMPORTANT: Work in the SAME browser window!

Steps:
1. Open a NEW TAB (Ctrl+T) - do NOT open new window
2. Navigate to https://example.com
3. ...

Remember: NEW TAB, not new window!
"""
agent.add_new_task(task)
await agent.run()
```

---

## 🐛 Troubleshooting

### Проблема: "Browser closed" после add_new_task()

**Причина**: Не используется `keep_alive=True`

**Решение**:
```python
profile = BrowserProfile(keep_alive=True)  # ← Добавить!
agent = Agent(task="...", browser_profile=profile)
```

---

### Проблема: "CDP client not initialized"

**Причина**: Попытка передать `browser_session` между разными Agent'ами

**Решение**: Использовать один Agent + `add_new_task()`:
```python
# Было (неправильно):
agent1 = Agent(task="Task 1", browser_session=browser)
agent2 = Agent(task="Task 2", browser_session=browser)  # ← ОШИБКА!

# Стало (правильно):
agent = Agent(task="Task 1", browser_session=browser)
await agent.run()
agent.add_new_task("Task 2")  # ← ПРАВИЛЬНО!
await agent.run()
```

---

### Проблема: "EventBus with name already exists" warning

**Причина**: `add_new_task()` пересоздает EventBus каждый раз (это нормально!)

**Решение**: Это **warning**, не ошибка. Можно игнорировать или подавить:
```python
import warnings
warnings.filterwarnings('ignore', message='EventBus with name')
```

Но лучше оставить - это индикатор, что `add_new_task()` работает.

---

### Проблема: "Expected at least one handler to return a non-None result"

**Причина**: LLM не смог выполнить задачу (браузер недоступен, элемент не найден, etc.)

**Решение**: 
1. Проверить, что браузер открыт (`keep_alive=True`)
2. Добавить retry logic
3. Упростить промпт
4. Увеличить `step_timeout`

```python
for attempt in range(max_retries):
    try:
        self.agent.add_new_task(task)
        result = await asyncio.wait_for(self.agent.run(), timeout=120)
        break
    except Exception as e:
        print(f"Attempt {attempt}: {e}")
        await asyncio.sleep(5)
```

---

## 📚 Примеры из официальной библиотеки

### Пример 1: follow_up_tasks.py (интерактивный)

```python
from browser_use import Agent
from browser_use.browser.profile import BrowserProfile

profile = BrowserProfile(keep_alive=True)
task = "Go to reddit.com"

async def main():
    agent = Agent(task=task, browser_profile=profile)
    await agent.run(max_steps=1)
    
    while True:
        user_response = input('\n👤 New task or "q" to quit: ')
        agent.add_new_task(f'New task: {user_response}')
        await agent.run()

asyncio.run(main())
```

**Путь**: `browser-use-repo/examples/features/follow_up_tasks.py`

---

### Пример 2: follow_up_task.py (Browser API)

```python
from browser_use import Agent, Browser

async def main():
    browser = Browser(keep_alive=True)
    await browser.start()
    
    agent = Agent(task='search for browser-use.', browser_session=browser)
    await agent.run(max_steps=2)
    
    agent.add_new_task('return the title of first result')
    await agent.run()
    
    await browser.kill()

asyncio.run(main())
```

**Путь**: `browser-use-repo/examples/features/follow_up_task.py`

---

## ✅ Checklist для использования add_new_task()

- [ ] Используется `BrowserProfile(keep_alive=True)` или `Browser(keep_alive=True)`
- [ ] Создается **ОДИН** Agent для всех задач
- [ ] После каждого `add_new_task()` вызывается `run()`
- [ ] Есть timeout для `run()`: `await asyncio.wait_for(agent.run(), timeout=120)`
- [ ] Есть retry logic для обработки ошибок
- [ ] Agent закрывается в `finally` блоке
- [ ] Промпты явно указывают на работу с вкладками (не окнами)
- [ ] Обрабатываются исключения (TimeoutError, общие Exception)

---

## 🎯 Итоговый правильный паттерн (наш случай)

```python
from browser_use import Agent
from browser_use.browser.profile import BrowserProfile

class AirtableRegistration:
    def __init__(self, llm, max_retries=5):
        self.llm = llm
        self.agent = None
        # ✅ КЛЮЧЕВОЕ: keep_alive=True!
        self.browser_profile = BrowserProfile(keep_alive=True)
        self.max_retries = max_retries
    
    async def run(self):
        try:
            # ✅ Создаем Agent ОДИН РАЗ с профилем
            self.agent = Agent(
                task="Open https://airtable.com",
                llm=self.llm,
                browser_profile=self.browser_profile,  # ← keep_alive=True!
                use_vision=True
            )
            await asyncio.wait_for(self.agent.run(), timeout=120)
            
            # ✅ Все остальные шаги через add_new_task()
            self.agent.add_new_task("Get temp email")
            await asyncio.wait_for(self.agent.run(), timeout=120)
            
            self.agent.add_new_task("Fill form")
            await asyncio.wait_for(self.agent.run(), timeout=120)
            
            # Браузер остается открытым между шагами! ✅
            
        finally:
            # ✅ Cleanup
            if self.agent:
                await self.agent.close()
```

---

## 📖 Дополнительная информация

- **Официальная документация**: https://docs.browser-use.com/
- **GitHub**: https://github.com/browser-use/browser-use (71.3k ⭐)
- **Примеры**: `browser-use-repo/examples/features/`
- **Исходный код**: `browser-use-repo/browser_use/agent/service.py:621`

---

**Вывод**: Паттерн `add_new_task()` + `run()` работает правильно, **НО** требует `keep_alive=True`! Без этого браузер закроется после первого `run()`.
