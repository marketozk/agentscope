# 🎯 Паттерн: Dual Agent (Computer Use + Code Execution)

## Проблема
- `gemini-2.5-computer-use` - только браузер, без code execution
- `gemini-2.0-flash` - code execution, но без computer use
- Нужны ОБА инструмента для комплексных задач

## ✅ Решение: Использовать 2 агента

### Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator                         │
│              (координирует агентов)                     │
└─────────────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌───────────────────┐   ┌───────────────────┐
│  Browser Agent    │   │  Compute Agent    │
│                   │   │                   │
│ Model:            │   │ Model:            │
│ computer-use      │   │ gemini-2.0-flash  │
│                   │   │                   │
│ Tools:            │   │ Tools:            │
│ - navigate        │   │ - code_execution  │
│ - click_at        │   │                   │
│ - type_text_at    │   │ Capabilities:     │
│ - search          │   │ - Python код      │
│ - scroll          │   │ - Numpy/Pandas    │
│ (17 actions)      │   │ - Matplotlib      │
│                   │   │ - Вычисления      │
└───────────────────┘   └───────────────────┘
```

### Пример использования

#### Задача: Собрать данные с сайта и построить график

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_API_KEY")

# ════════════════════════════════════════════════════════
# 1. BROWSER AGENT - Сбор данных
# ════════════════════════════════════════════════════════

browser_config = types.GenerateContentConfig(
    tools=[
        types.Tool(
            computer_use=types.ComputerUse(
                environment=types.Environment.ENVIRONMENT_BROWSER
            )
        )
    ]
)

# Задача: собрать курсы валют
response = client.models.generate_content(
    model='gemini-2.5-computer-use-preview-10-2025',
    contents=[
        types.Content(role="user", parts=[
            types.Part(text="Открой cbr.ru и собери курсы USD, EUR, CNY за последние 7 дней"),
            types.Part.from_bytes(data=screenshot, mime_type='image/png')
        ])
    ],
    config=browser_config
)

# Получаем текстовые данные
currency_data = extract_text_from_response(response)
# Например: "USD: [79.08, 78.95, 79.10, ...], EUR: [92.08, 91.85, ...]"

# ════════════════════════════════════════════════════════
# 2. COMPUTE AGENT - Анализ и визуализация
# ════════════════════════════════════════════════════════

compute_config = types.GenerateContentConfig(
    tools=[types.Tool(code_execution=types.ToolCodeExecution)]
)

response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=f"""
    Вот данные курсов валют за 7 дней:
    {currency_data}
    
    Задача:
    1. Распарси эти данные
    2. Вычисли средний курс для каждой валюты
    3. Построй линейный график изменения курсов
    4. Добавь трендовую линию
    """,
    config=compute_config
)

# Модель сгенерирует и выполнит Python код:
# - Создаст DataFrame pandas
# - Построит график matplotlib
# - Вернет изображение графика

for part in response.candidates[0].content.parts:
    if part.executable_code:
        print("📝 Код:", part.executable_code.code)
    if part.code_execution_result:
        print("✅ Результат:", part.code_execution_result.output)
```

### Реальная имплементация

```python
import asyncio
from playwright.async_api import async_playwright
from google import genai
from google.genai import types

class DualAgent:
    """Агент с Computer Use и Code Execution"""
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.browser_model = "gemini-2.5-computer-use-preview-10-2025"
        self.compute_model = "gemini-2.0-flash"
        
        # Конфиги для разных задач
        self.browser_config = types.GenerateContentConfig(
            tools=[
                types.Tool(
                    computer_use=types.ComputerUse(
                        environment=types.Environment.ENVIRONMENT_BROWSER
                    )
                )
            ]
        )
        
        self.compute_config = types.GenerateContentConfig(
            tools=[types.Tool(code_execution=types.ToolCodeExecution)]
        )
    
    async def browse_and_extract(self, task: str) -> str:
        """Используем Browser Agent для сбора данных"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            
            # Начальный скриншот
            screenshot = await page.screenshot(type="png")
            
            response = self.client.models.generate_content(
                model=self.browser_model,
                contents=[
                    types.Content(role="user", parts=[
                        types.Part(text=task),
                        types.Part.from_bytes(data=screenshot, mime_type='image/png')
                    ])
                ],
                config=self.browser_config
            )
            
            # Выполняем действия браузера...
            # (здесь цикл выполнения function_calls)
            
            # Извлекаем финальный текст
            final_text = " ".join([
                part.text for part in response.candidates[0].content.parts 
                if part.text
            ])
            
            await browser.close()
            return final_text
    
    def compute_and_visualize(self, data: str, task: str):
        """Используем Compute Agent для вычислений и графиков"""
        prompt = f"""
        Данные:
        {data}
        
        Задача:
        {task}
        
        Используй Python для:
        1. Парсинга данных
        2. Вычислений
        3. Построения графиков (matplotlib)
        """
        
        response = self.client.models.generate_content(
            model=self.compute_model,
            contents=prompt,
            config=self.compute_config
        )
        
        return response
    
    async def execute_complex_task(self, task: str):
        """Оркестрация: браузер → данные → вычисления"""
        
        # Шаг 1: Собираем данные через браузер
        print("🌐 Шаг 1: Сбор данных через браузер...")
        data = await self.browse_and_extract(
            f"Собери данные для задачи: {task}"
        )
        
        print(f"✅ Данные собраны:\n{data}\n")
        
        # Шаг 2: Анализируем и визуализируем
        print("🔢 Шаг 2: Анализ и визуализация...")
        result = self.compute_and_visualize(
            data=data,
            task="Проанализируй данные, построй график"
        )
        
        # Выводим результаты
        for part in result.candidates[0].content.parts:
            if part.executable_code:
                print("📝 Сгенерированный код:")
                print(part.executable_code.code)
            if part.code_execution_result:
                print("\n✅ Результат выполнения:")
                print(part.code_execution_result.output)
        
        return result

# ════════════════════════════════════════════════════════
# Использование
# ════════════════════════════════════════════════════════

async def main():
    agent = DualAgent(api_key="YOUR_API_KEY")
    
    # Комплексная задача
    await agent.execute_complex_task(
        "Открой cbr.ru, собери курсы USD/EUR за неделю, "
        "построй график и посчитай среднее изменение"
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## Примеры задач для Dual Agent

### 1. Финансовый анализ
```
Browser Agent: Собрать котировки акций с investing.com
Compute Agent: Рассчитать волатильность, построить свечной график
```

### 2. Парсинг таблиц
```
Browser Agent: Извлечь таблицу с результатами с сайта
Compute Agent: Преобразовать в pandas DataFrame, сделать сводную таблицу
```

### 3. Сравнение цен
```
Browser Agent: Собрать цены товара с 5 сайтов
Compute Agent: Найти минимум, построить bar chart, вычислить экономию
```

### 4. Мониторинг метрик
```
Browser Agent: Собрать метрики с dashboard'а
Compute Agent: Проанализировать тренды, построить time series график
```

## ⚠️ Важные моменты

### Разделение ответственности

| Агент | Задачи |
|-------|--------|
| **Browser Agent** | - Навигация по сайтам<br>- Клики и формы<br>- Извлечение текста<br>- Скриншоты |
| **Compute Agent** | - Python вычисления<br>- Pandas/Numpy<br>- Matplotlib графики<br>- Статистика |

### Передача данных между агентами

**✅ Хорошо:**
```python
# Browser извлекает структурированный текст
data = "USD: 79.08, EUR: 92.08, CNY: 11.23"

# Compute парсит и обрабатывает
response = compute_agent.process(data)
```

**❌ Плохо:**
```python
# Пытаться передать HTML или сложные объекты
data = page.content()  # Слишком много информации
```

### Оптимизация токенов

- **Browser Agent**: Минимизировать историю, передавать только нужные скриншоты
- **Compute Agent**: Использовать компактные данные (JSON, CSV-строки)

## 🎯 Когда использовать Dual Agent?

✅ **Подходит:**
- Сбор данных с веб-сайтов + математический анализ
- Автоматизация форм + вычисления результатов
- Парсинг таблиц + построение графиков
- E2E тестирование + анализ метрик

❌ **Избыточно:**
- Простой парсинг без вычислений → только Browser Agent
- Чистые вычисления без веба → только Compute Agent
- Задачи, где можно обойтись одним агентом

## 📊 Сравнение моделей

| Возможность | computer-use | gemini-2.0-flash |
|-------------|--------------|------------------|
| Браузер (17 actions) | ✅ | ❌ |
| Code Execution | ❌ | ✅ |
| Python библиотеки | ❌ | ✅ (60+ libs) |
| Matplotlib/Seaborn | ❌ | ✅ |
| Файлы (CSV/JSON) | ❌ | ✅ |
| Скриншоты анализ | ✅ | ✅ |
| Function calling | ✅ | ✅ |
| Thinking mode | ✅ | ✅ |

## 🚀 Вывод

**Computer Use ≠ Code Execution**

Это два **разных** инструмента для **разных** задач:

- **Computer Use**: Браузер-автоматизация (как Selenium, но с AI)
- **Code Execution**: Python песочница (как Jupyter, но в API)

Для комплексных задач используйте **Dual Agent Pattern** 🎯
