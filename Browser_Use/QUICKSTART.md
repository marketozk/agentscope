# Быстрый старт 🚀

## Файлы проекта

### 1. `yandex_search.py` — Базовый пример
Простейший скрипт для понимания основ browser-use.

**Запуск:**
```cmd
python yandex_search.py
```

**Что делает:** Открывает Яндекс и выполняет поиск.

---

### 2. `multi_scenario.py` — Многосценарный скрипт
Содержит 4 готовых сценария с интерактивным меню.

**Запуск с меню:**
```cmd
python multi_scenario.py
```

**Быстрый запуск примеров:**
```cmd
python multi_scenario.py --quick
```

**Справка:**
```cmd
python multi_scenario.py --help
```

---

### 3. `examples.py` — Программные примеры
Показывает, как использовать сценарии в вашем коде.

**Запуск:**
```cmd
python examples.py
```

Выберите пример из меню или изучите код для интеграции в свой проект.

---

## Два режима работы

### 🎯 Единый промпт
```python
agent = Agent(
    task="""
    1. Открой yandex.ru
    2. Найди 'тест'
    3. Открой первый результат
    """,
    llm=llm
)
await agent.run()
```

**Когда использовать:**
- Простые линейные задачи
- Быстрые проверки
- Доверяете LLM в планировании

---

### 👣 Пошаговый режим
```python
steps = [
    "Открой yandex.ru",
    "Найди 'тест'",
    "Открой первый результат"
]

for step in steps:
    agent = Agent(task=step, llm=llm)
    await agent.run()
    await asyncio.sleep(2)
```

**Когда использовать:**
- Сложные задачи
- Нужен контроль между шагами
- Отладка

---

## Сценарии

### 📰 1. Поиск новостей
```python
from multi_scenario import NewsSearchScenario, get_llm, get_profile_path

scenario = NewsSearchScenario(get_llm(), get_profile_path())
await scenario.run("космос", mode="single_prompt")
```

### 📝 2. Регистрация
```python
from multi_scenario import RegistrationScenario, get_llm, get_profile_path

user_data = {
    "first_name": "Иван",
    "last_name": "Тестов",
    "email": "test@example.com",
    "mobile": "9001234567",
    "gender": "Male"
}

scenario = RegistrationScenario(get_llm(), get_profile_path())
await scenario.run(user_data, mode="single_prompt")
```

### 💰 3. Мониторинг цен
```python
from multi_scenario import PriceMonitoringScenario, get_llm, get_profile_path

scenario = PriceMonitoringScenario(get_llm(), get_profile_path())
await scenario.run("iPhone 15", mode="step_by_step")
```

### 📚 4. Википедия
```python
from multi_scenario import WikipediaScenario, get_llm, get_profile_path

scenario = WikipediaScenario(get_llm(), get_profile_path())
await scenario.run("Python", mode="single_prompt")
```

---

## Создание собственного сценария

```python
from multi_scenario import ScenarioRunner, get_llm, get_profile_path

class MyScenario(ScenarioRunner):
    async def run(self, param: str, mode: str = "single_prompt"):
        if mode == "single_prompt":
            task = f"Моя задача с параметром {param}"
            return await self.run_single_prompt(task)
        
        elif mode == "step_by_step":
            steps = [
                f"Шаг 1 с {param}",
                "Шаг 2",
                "Шаг 3"
            ]
            return await self.run_step_by_step(steps)

# Использование
scenario = MyScenario(get_llm(), get_profile_path())
await scenario.run("значение", mode="single_prompt")
```

---

## Частые вопросы

### Q: Как изменить модель Gemini?
В коде замените:
```python
llm = bu_llm.google_gemini_2_5_flash  # быстрая
# на
llm = bu_llm.google_gemini_2_5_pro    # более умная
```

### Q: Как включить headless режим?
Browser-use по умолчанию использует `headless=False` для лучшей совместимости.
Для изменения нужно передать параметры браузера при создании Agent.

### Q: Как добавить паузы между действиями?
```python
for step in steps:
    agent = Agent(task=step, llm=llm)
    await agent.run()
    await asyncio.sleep(5)  # пауза 5 секунд
```

### Q: Как обработать ошибки?
```python
try:
    result = await scenario.run("запрос")
    print("✅ Успех:", result)
except Exception as e:
    print("❌ Ошибка:", e)
```

### Q: Профиль браузера сохраняется?
Да, в папке `profile_data/`. Удалите её для сброса cookies/сессий.

---

## Полезные ссылки

- **Browser-Use документация:** https://github.com/browser-use/browser-use
- **Gemini API:** https://ai.google.dev/
- **Playwright:** https://playwright.dev/

---

## Следующие шаги

1. ✅ Запустите `yandex_search.py` для проверки настройки
2. ✅ Попробуйте `multi_scenario.py` с разными сценариями
3. ✅ Изучите `examples.py` для понимания программного использования
4. ✅ Создайте свой сценарий на основе `ScenarioRunner`

---

**Приятной автоматизации! 🤖**
