# Browser-Use Agent - Полная документация методов

## Информация о библиотеке

- **Репозиторий**: https://github.com/browser-use/browser-use
- **Звезд на GitHub**: 71.3k ⭐
- **Версия**: 0.8.1
- **Документация**: https://docs.browser-use.com/
- **Cloud сервис**: https://cloud.browser-use.com/

---

## 🎯 Основные методы Agent

### 1. `__init__()` - Инициализация агента

```python
Agent(
    task: str,                                    # Задача для выполнения
    llm: BaseChatModel | None = None,            # LLM модель
    browser_profile: BrowserProfile | None = None,
    browser_session: BrowserSession | None = None,
    browser: BrowserSession | None = None,        # Алиас для browser_session
    tools: Optional[Tools] = None,                # Инструменты
    controller: Optional[Tools] = None,           # Алиас для tools
    sensitive_data: dict[str, str | dict] | None = None,
    initial_actions: list[dict] | None = None,
    use_vision: Union[bool, Literal['auto']] = 'auto',
    save_conversation_path: str | Path | None = None,
    max_failures: int = 3,                        # Максимум неудач подряд
    max_actions_per_step: int = 10,
    use_thinking: bool = True,
    flash_mode: bool = False,
    step_timeout: int = 120,                      # Таймаут шага (секунды)
    llm_timeout: int | None = None,
    directly_open_url: bool = True,
    # ... и другие параметры
)
```

**Важно**: 
- `browser` и `browser_session` - это ОДНО И ТО ЖЕ (алиасы)
- `tools` и `controller` - это ОДНО И ТО ЖЕ (алиасы)
- ⚠️ **ПРОБЛЕМА**: Передача существующего `browser_session` в новый Agent может вызвать ошибку "CDP client not initialized"

---

### 2. `run()` - Основной метод выполнения

```python
async def run(
    self, 
    max_steps: int = 100,
    on_step_start: Callable | None = None,
    on_step_end: Callable | None = None
) -> AgentHistoryList
```

**Описание**: Выполняет задачу с максимальным количеством шагов

**Возвращает**: `AgentHistoryList` - история выполнения со всеми результатами

**Пример**:
```python
agent = Agent(task="Open google.com", llm=llm)
result = await agent.run(max_steps=50)
print(result)  # AgentHistoryList с историей выполнения
```

---

### 3. `run_sync()` - Синхронная версия run()

```python
def run_sync(
    self,
    max_steps: int = 100,
    on_step_start: Callable | None = None,
    on_step_end: Callable | None = None
) -> AgentHistoryList
```

**Описание**: Синхронная обертка для `run()`, не требует `await`

**Пример**:
```python
agent = Agent(task="Open google.com", llm=llm)
result = agent.run_sync()  # Без await!
```

---

### 4. `add_new_task()` - Добавление новой задачи

```python
def add_new_task(self, new_task: str) -> None
```

**Описание**: Добавляет новую задачу к текущему агенту, сохраняя браузер открытым и историю

**✅ РЕКОМЕНДУЕТСЯ**: Использовать вместо создания нового Agent для последовательных задач

**⚠️ ВАЖНО**: Для работы `add_new_task()` нужно использовать `keep_alive=True`!

**Пример 1 (BrowserProfile - рекомендуется)**:
```python
from browser_use.browser.profile import BrowserProfile

profile = BrowserProfile(keep_alive=True)
agent = Agent(task="Open google.com", llm=llm, browser_profile=profile)
await agent.run()

# Добавляем новую задачу в ТОМ ЖЕ браузере
agent.add_new_task("Now search for 'browser-use python'")
await agent.run()

# Ещё одна задача
agent.add_new_task("Click on the first result")
await agent.run()
```

**Пример 2 (Browser)**:
```python
from browser_use import Browser

browser = Browser(keep_alive=True)
await browser.start()
agent = Agent(task='Open google.com', browser_session=browser, llm=llm)
await agent.run()

agent.add_new_task('search for browser-use')
await agent.run()

await browser.kill()
```

**Преимущества**:
- ✅ Браузер остается открытым между задачами
- ✅ История сохраняется
- ✅ Не создаются новые окна
- ✅ CDP клиент работает корректно

**⚠️ Без `keep_alive=True` браузер закроется после первого `run()`!**

---

### 5. `step()` - Выполнение одного шага

```python
async def step(self, step_info: AgentStepInfo | None = None) -> None
```

**Описание**: Выполняет один шаг (получение контекста → запрос LLM → выполнение действий)

**Пример**:
```python
agent = Agent(task="Search something", llm=llm)
await agent.step()  # Один шаг
await agent.step()  # Ещё один шаг
```

---

### 6. `take_step()` - Управляемый шаг

```python
async def take_step(
    self, 
    step_info: AgentStepInfo | None = None
) -> tuple[bool, bool]  # (is_done, encountered_error)
```

**Описание**: Выполняет шаг и возвращает статус завершения

**Возвращает**:
- `is_done` - завершена ли задача
- `encountered_error` - была ли ошибка

---

### 7. `multi_act()` - Выполнение множества действий

```python
async def multi_act(
    self, 
    actions: list[ActionModel]
) -> list[ActionResult]
```

**Описание**: Выполняет список действий последовательно

**Пример**:
```python
from browser_use.tools.registry.views import ActionModel

actions = [
    ActionModel(action_name="navigate", params={"url": "https://google.com"}),
    ActionModel(action_name="click", params={"index": 5}),
]
results = await agent.multi_act(actions)
```

---

### 8. `close()` - Закрытие агента

```python
async def close(self) -> None
```

**Описание**: Закрывает браузер и очищает ресурсы

**Пример**:
```python
try:
    await agent.run()
finally:
    await agent.close()  # Обязательно закрываем!
```

---

### 9. `pause()` / `resume()` / `stop()` - Управление выполнением

```python
def pause(self) -> None     # Приостановить
def resume(self) -> None    # Возобновить
def stop(self) -> None      # Остановить
```

**Описание**: Контролируют выполнение задачи

**Пример**:
```python
agent = Agent(task="Long task", llm=llm)

# В другом потоке/месте
agent.pause()   # Приостановить выполнение
agent.resume()  # Продолжить
agent.stop()    # Полностью остановить
```

---

### 10. `save_history()` / `load_and_rerun()` - Работа с историей

```python
def save_history(self, file_path: str | Path | None = None) -> None

async def load_and_rerun(
    self, 
    history_file: str | Path | None = None, 
    **kwargs
) -> list[ActionResult]
```

**Описание**: Сохранение и воспроизведение истории действий

**Пример**:
```python
# Сохранить
agent.save_history("my_history.json")

# Воспроизвести
new_agent = Agent(task="replay", llm=llm)
results = await new_agent.load_and_rerun("my_history.json")
```

---

### 11. `get_model_output()` - Получение ответа от LLM

```python
async def get_model_output(
    self, 
    input_messages: list[BaseMessage]
) -> AgentOutput
```

**Описание**: Отправляет сообщения в LLM и получает структурированный ответ

---

### 12. `log_completion()` - Логирование завершения

```python
async def log_completion(self) -> None
```

**Описание**: Выводит итоговую статистику выполнения

---

## 📊 Свойства (Properties)

### `browser_session`
```python
agent.browser_session  # BrowserSession - текущая сессия браузера
```

### `tools`
```python
agent.tools  # Tools - инструменты агента
```

### `message_manager`
```python
agent.message_manager  # MessageManager - управление сообщениями
```

### `logger`
```python
agent.logger  # logging.Logger - логгер агента
```

---

## 🔥 Правильные паттерны использования

### ✅ Паттерн 1: Один Agent, несколько задач (РЕКОМЕНДУЕТСЯ)

```python
# Создаём ОДИН агент
agent = Agent(task="Open https://example.com", llm=llm, use_vision=True)
await agent.run()

# Добавляем новые задачи
agent.add_new_task("Find the email on this page")
await agent.run()

agent.add_new_task("Copy the email address")
await agent.run()

# Браузер остается открытым, все работает в ОДНОМ окне
```

**Преимущества**:
- ✅ Один браузер
- ✅ Одна сессия
- ✅ CDP работает корректно
- ✅ Нет проблем с новыми окнами

---

### ❌ Паттерн 2: Множество Agent (НЕ РАБОТАЕТ)

```python
# НЕПРАВИЛЬНО - создаёт проблемы!
agent1 = Agent(task="Open site", llm=llm)
await agent1.run()

# Пытаемся переиспользовать browser_session
agent2 = Agent(
    task="Do something else",
    llm=llm,
    browser_session=agent1.browser_session,  # ❌ ОШИБКА!
    tools=agent1.tools
)
await agent2.run()  # ERROR: CDP client not initialized!
```

**Проблемы**:
- ❌ CDP клиент не инициализируется
- ❌ Новые окна вместо вкладок
- ❌ Нестабильная работа

---

### ✅ Паттерн 3: С контекстным менеджером

```python
async with Agent(task="My task", llm=llm) as agent:
    result = await agent.run()
    # Браузер автоматически закроется
```

---

### ✅ Паттерн 4: С кастомными инструментами

```python
from browser_use import Tools, ActionResult

tools = Tools()

@tools.action("Save data to file")
def save_data(data: str):
    with open("output.txt", "w") as f:
        f.write(data)
    return ActionResult(extracted_content="Saved!")

agent = Agent(
    task="Extract data and save it",
    llm=llm,
    tools=tools
)
await agent.run()
```

---

## ⚠️ Известные проблемы

### 1. Переиспользование browser_session

**Проблема**: 
```python
agent2 = Agent(browser_session=agent1.browser_session)  # ❌
# ERROR: CDP client not initialized
```

**Решение**: Использовать `add_new_task()` вместо создания нового Agent

---

### 2. Открытие новых окон вместо вкладок

**Проблема**: При создании нового Agent открывается новое окно

**Решение**: Использовать один Agent с `add_new_task()`

---

### 3. Таймауты

**Проблема**: Нет встроенных таймаутов для `agent.run()`

**Решение**: Использовать `asyncio.wait_for()`:
```python
try:
    result = await asyncio.wait_for(agent.run(), timeout=300)
except asyncio.TimeoutError:
    print("Task timed out!")
    await agent.stop()
```

---

## 📚 Полезные ссылки

- **Документация**: https://docs.browser-use.com/
- **Примеры**: https://github.com/browser-use/browser-use/tree/main/examples
- **Discord**: https://link.browser-use.com/discord
- **Cloud**: https://cloud.browser-use.com/

---

## 💡 Рекомендации для вашего проекта

### Для `airtable_registration.py`:

1. **Используйте один Agent**:
```python
class AirtableRegistration:
    def __init__(self, llm, max_retries=5):
        self.agent = None  # Один Agent для всех шагов
        
    async def run(self):
        # Создаём агента один раз
        self.agent = Agent(task="Open airtable", llm=self.llm)
        await self.agent.run()
        
        # Все последующие шаги через add_new_task
        self.agent.add_new_task("Open temp-mail in new tab")
        await self.agent.run()
        
        self.agent.add_new_task("Fill registration form")
        await self.agent.run()
```

2. **Добавьте таймауты**:
```python
result = await asyncio.wait_for(
    self.agent.run(), 
    timeout=self.step_timeout
)
```

3. **Добавьте cleanup**:
```python
try:
    await self.run()
finally:
    if self.agent:
        await self.agent.close()
```

---

## 🎓 Заключение

**Ключевая идея**: Используйте **ОДИН Agent + add_new_task()** для последовательных задач в одном браузере.

**НЕ создавайте** множество Agent'ов - это вызовет проблемы с CDP и откроет новые окна.

---

*Документация создана на основе browser-use v0.8.1*
*Дата: 15 октября 2025*
