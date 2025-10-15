# add_new_task() - Быстрая шпаргалка

## ⚡ TL;DR (слишком долго не читал)

```python
# ✅ ПРАВИЛЬНО (3 строки для запоминания):
profile = BrowserProfile(keep_alive=True)  # 1. Обязательно keep_alive!
agent = Agent(task="...", browser_profile=profile, llm=llm)  # 2. Передаем профиль
await agent.run()  # 3. Выполняем

# Добавляем новые задачи:
agent.add_new_task("новая задача")  # 4. Добавляем
await agent.run()  # 5. Выполняем (каждый раз!)
```

---

## 🎯 Главное правило

**`keep_alive=True` обязательно!** Без этого браузер закроется после первого `run()`.

---

## ✅ Два рабочих паттерна

### Паттерн 1: BrowserProfile (рекомендуется)

```python
from browser_use.browser.profile import BrowserProfile

profile = BrowserProfile(keep_alive=True)
agent = Agent(task="задача", browser_profile=profile, llm=llm)
await agent.run()

agent.add_new_task("новая задача")
await agent.run()
```

### Паттерн 2: Browser (больше контроля)

```python
from browser_use import Browser

browser = Browser(keep_alive=True)
await browser.start()
agent = Agent(task="задача", browser_session=browser, llm=llm)
await agent.run()

agent.add_new_task("новая задача")
await agent.run()

await browser.kill()  # Не забыть!
```

---

## ❌ Частые ошибки

### Ошибка 1: Забыли keep_alive

```python
# ❌ НЕПРАВИЛЬНО
agent = Agent(task="задача", llm=llm)  # Нет keep_alive!
await agent.run()
agent.add_new_task("новая задача")
await agent.run()  # ← Браузер закрыт!
```

### Ошибка 2: Множество Agent с одним browser

```python
# ❌ НЕПРАВИЛЬНО
agent1 = Agent(task="задача 1", browser_session=browser)
agent2 = Agent(task="задача 2", browser_session=browser)  # CDP ошибка!

# ✅ ПРАВИЛЬНО - один Agent
agent = Agent(task="задача 1", browser_session=browser)
await agent.run()
agent.add_new_task("задача 2")
await agent.run()
```

### Ошибка 3: Забыли run() после add_new_task()

```python
# ❌ НЕПРАВИЛЬНО
agent.add_new_task("новая задача")
# Забыли run()! Задача не выполнилась!

# ✅ ПРАВИЛЬНО
agent.add_new_task("новая задача")
await agent.run()  # Обязательно!
```

---

## 🔧 С timeout и retry

```python
# ✅ Production-ready паттерн
for attempt in range(max_retries):
    try:
        agent.add_new_task(task)
        await asyncio.wait_for(agent.run(), timeout=120)
        break
    except asyncio.TimeoutError:
        print(f"Timeout, retry {attempt}")
        await asyncio.sleep(5)
```

---

## 🎓 Best Practices

1. ✅ Всегда `keep_alive=True`
2. ✅ Один Agent для всех шагов
3. ✅ Всегда `run()` после `add_new_task()`
4. ✅ Timeout для `run()`: `asyncio.wait_for(..., timeout=120)`
5. ✅ Cleanup в `finally`: `await agent.close()`

---

## 🐛 Troubleshooting

| Ошибка | Причина | Решение |
|--------|---------|---------|
| Browser closed | Нет `keep_alive=True` | Добавить `BrowserProfile(keep_alive=True)` |
| CDP not initialized | Много Agent с одним browser | Использовать один Agent + `add_new_task()` |
| EventBus warning | Нормально при `add_new_task()` | Игнорировать (это не ошибка) |
| Expected at least one handler | LLM не смог выполнить | Retry + упростить промпт |

---

## 📚 Примеры из библиотеки

- `browser-use-repo/examples/features/follow_up_tasks.py` - BrowserProfile
- `browser-use-repo/examples/features/follow_up_task.py` - Browser API

---

## ✅ Checklist

- [ ] `BrowserProfile(keep_alive=True)` или `Browser(keep_alive=True)`
- [ ] ОДИН Agent для всех задач
- [ ] `run()` после каждого `add_new_task()`
- [ ] `asyncio.wait_for()` с timeout
- [ ] Retry logic
- [ ] `await agent.close()` в `finally`
