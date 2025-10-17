# 📘 Gemini 2.5 Computer Use API - Полный справочник

## 🎯 Обзор

**Модель**: `gemini-2.5-computer-use-preview-10-2025`  
**SDK**: `google.genai` (новый unified SDK)  
**Назначение**: Автономное управление браузером через Computer Use tool  
**Среда**: `ENVIRONMENT_BROWSER` (для веб-браузеров)

---

## 📊 Технические характеристики

| Параметр | Значение |
|----------|----------|
| **Входные токены** | 128,000 |
| **Выходные токены** | 64,000 |
| **Поддерживаемые типы данных** | Вход: изображение + текст; Выход: текст + function_calls |
| **Координаты** | Нормализованные 0-999 (преобразуются в пиксели) |
| **Рекомендуемое разрешение** | 1440x900 (работает с любым) |
| **Последнее обновление** | Октябрь 2025 |

---

## 🔧 Полный список действий (Function Calls)

### 1️⃣ Навигация и управление браузером

#### `open_web_browser`
**Описание**: Открывает веб-браузер  
**Аргументы**: Нет  
**Пример ответа от модели**:
```json
{
  "name": "open_web_browser",
  "args": {}
}
```
**Реализация Playwright**:
```python
# Браузер уже открыт - ничего не делаем
pass
```

---

#### `navigate`
**Описание**: Переходит по указанному URL  
**Аргументы**:
- `url` (string): URL для перехода

**Пример ответа от модели**:
```json
{
  "name": "navigate",
  "args": {
    "url": "https://www.wikipedia.org"
  }
}
```
**Реализация Playwright**:
```python
await page.goto(args["url"], wait_until="networkidle", timeout=30000)
```

---

#### `search`
**Описание**: Переходит на домашнюю страницу поисковой системы (Google)  
**Аргументы**: Нет  
**Пример ответа от модели**:
```json
{
  "name": "search",
  "args": {}
}
```
**Реализация Playwright**:
```python
await page.goto("https://www.google.com", wait_until="networkidle")
```

---

#### `go_back`
**Описание**: Возврат на предыдущую страницу в истории браузера  
**Аргументы**: Нет  
**Пример ответа от модели**:
```json
{
  "name": "go_back",
  "args": {}
}
```
**Реализация Playwright**:
```python
await page.go_back(wait_until="networkidle")
```

---

#### `go_forward`
**Описание**: Переход к следующей странице в истории браузера  
**Аргументы**: Нет  
**Пример ответа от модели**:
```json
{
  "name": "go_forward",
  "args": {}
}
```
**Реализация Playwright**:
```python
await page.go_forward(wait_until="networkidle")
```

---

### 2️⃣ Взаимодействие с элементами (клики и наведение)

#### `click_at`
**Описание**: Клик по координатам (0-999 нормализованная сетка)  
**Аргументы**:
- `x` (int, 0-999): Координата X
- `y` (int, 0-999): Координата Y

**Пример ответа от модели**:
```json
{
  "name": "click_at",
  "args": {
    "x": 500,
    "y": 300
  }
}
```
**Реализация Playwright**:
```python
# Денормализация координат
screen_width = 1440  # Ваше разрешение
screen_height = 900
actual_x = int(args["x"] / 1000 * screen_width)
actual_y = int(args["y"] / 1000 * screen_height)
await page.mouse.click(actual_x, actual_y)
```

---

#### `hover_at`
**Описание**: Наведение курсора на координаты (для отображения подменю)  
**Аргументы**:
- `x` (int, 0-999): Координата X
- `y` (int, 0-999): Координата Y

**Пример ответа от модели**:
```json
{
  "name": "hover_at",
  "args": {
    "x": 250,
    "y": 150
  }
}
```
**Реализация Playwright**:
```python
actual_x = int(args["x"] / 1000 * screen_width)
actual_y = int(args["y"] / 1000 * screen_height)
await page.mouse.move(actual_x, actual_y)
```

---

### 3️⃣ Ввод текста

#### `type_text_at`
**Описание**: Вводит текст в указанных координатах  
**Аргументы**:
- `x` (int, 0-999): Координата X
- `y` (int, 0-999): Координата Y
- `text` (string): Текст для ввода
- `press_enter` (bool, optional, default=True): Нажимать Enter после ввода
- `clear_before_typing` (bool, optional, default=True): Очистить поле перед вводом

**Пример ответа от модели**:
```json
{
  "name": "type_text_at",
  "args": {
    "x": 400,
    "y": 250,
    "text": "search query",
    "press_enter": false,
    "clear_before_typing": true
  }
}
```
**Реализация Playwright**:
```python
actual_x = int(args["x"] / 1000 * screen_width)
actual_y = int(args["y"] / 1000 * screen_height)
text = args["text"]
press_enter = args.get("press_enter", True)
clear_before = args.get("clear_before_typing", True)

# Клик по полю
await page.mouse.click(actual_x, actual_y)

# Очистка (если нужно)
if clear_before:
    await page.keyboard.press("Control+A")  # Windows/Linux
    # await page.keyboard.press("Meta+A")  # Mac
    await page.keyboard.press("Backspace")

# Ввод текста
await page.keyboard.type(text)

# Enter (если нужно)
if press_enter:
    await page.keyboard.press("Enter")
```

---

### 4️⃣ Клавиатурные действия

#### `key_combination`
**Описание**: Нажимает клавиши или их комбинации  
**Аргументы**:
- `keys` (string): Клавиша или комбинация (например, "Control+C", "Enter")

**Пример ответа от модели**:
```json
{
  "name": "key_combination",
  "args": {
    "keys": "Control+A"
  }
}
```
**Реализация Playwright**:
```python
keys = args["keys"]
await page.keyboard.press(keys)
```

**Поддерживаемые клавиши**:
- `Enter`, `Escape`, `Tab`, `Backspace`, `Delete`
- `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`
- `Control`, `Shift`, `Alt`, `Meta` (для комбинаций)
- `Control+C`, `Control+V`, `Control+A`, `Control+Z` и т.д.

---

### 5️⃣ Скроллинг

#### `scroll_document`
**Описание**: Прокручивает всю веб-страницу  
**Аргументы**:
- `direction` (string): Направление - "up", "down", "left", "right"

**Пример ответа от модели**:
```json
{
  "name": "scroll_document",
  "args": {
    "direction": "down"
  }
}
```
**Реализация Playwright**:
```python
direction = args["direction"]
scroll_amount = 500  # пикселей

if direction == "down":
    await page.mouse.wheel(0, scroll_amount)
elif direction == "up":
    await page.mouse.wheel(0, -scroll_amount)
elif direction == "right":
    await page.mouse.wheel(scroll_amount, 0)
elif direction == "left":
    await page.mouse.wheel(-scroll_amount, 0)
```

---

#### `scroll_at`
**Описание**: Прокручивает элемент в указанных координатах  
**Аргументы**:
- `x` (int, 0-999): Координата X
- `y` (int, 0-999): Координата Y
- `direction` (string): Направление - "up", "down", "left", "right"
- `magnitude` (int, 0-999, optional, default=800): Величина прокрутки

**Пример ответа от модели**:
```json
{
  "name": "scroll_at",
  "args": {
    "x": 500,
    "y": 500,
    "direction": "down",
    "magnitude": 400
  }
}
```
**Реализация Playwright**:
```python
actual_x = int(args["x"] / 1000 * screen_width)
actual_y = int(args["y"] / 1000 * screen_height)
direction = args["direction"]
magnitude = args.get("magnitude", 800)
actual_magnitude = int(magnitude / 1000 * screen_height)  # или screen_width

# Сначала наводим на элемент
await page.mouse.move(actual_x, actual_y)

# Прокручиваем
if direction == "down":
    await page.mouse.wheel(0, actual_magnitude)
elif direction == "up":
    await page.mouse.wheel(0, -actual_magnitude)
elif direction == "right":
    await page.mouse.wheel(actual_magnitude, 0)
elif direction == "left":
    await page.mouse.wheel(-actual_magnitude, 0)
```

---

### 6️⃣ Drag & Drop

#### `drag_and_drop`
**Описание**: Перетаскивает элемент из точки A в точку B  
**Аргументы**:
- `x` (int, 0-999): Начальная координата X
- `y` (int, 0-999): Начальная координата Y
- `destination_x` (int, 0-999): Конечная координата X
- `destination_y` (int, 0-999): Конечная координата Y

**Пример ответа от модели**:
```json
{
  "name": "drag_and_drop",
  "args": {
    "x": 100,
    "y": 100,
    "destination_x": 500,
    "destination_y": 500
  }
}
```
**Реализация Playwright**:
```python
start_x = int(args["x"] / 1000 * screen_width)
start_y = int(args["y"] / 1000 * screen_height)
end_x = int(args["destination_x"] / 1000 * screen_width)
end_y = int(args["destination_y"] / 1000 * screen_height)

# Перетаскивание
await page.mouse.move(start_x, start_y)
await page.mouse.down()
await page.mouse.move(end_x, end_y)
await page.mouse.up()
```

---

### 7️⃣ Ожидание

#### `wait_5_seconds`
**Описание**: Пауза на 5 секунд (для загрузки динамического контента)  
**Аргументы**: Нет  
**Пример ответа от модели**:
```json
{
  "name": "wait_5_seconds",
  "args": {}
}
```
**Реализация Playwright**:
```python
await asyncio.sleep(5)
```

---

## 🔐 Safety Decision (Система безопасности)

Модель может вернуть `safety_decision` в аргументах action, требующее подтверждения пользователя:

```json
{
  "name": "click_at",
  "args": {
    "x": 60,
    "y": 100,
    "safety_decision": {
      "explanation": "I need to click 'I'm not a robot' checkbox.",
      "decision": "require_confirmation"
    }
  }
}
```

**Типы решений**:
- **Normal/Allowed**: Действие безопасно (или `safety_decision` отсутствует)
- **require_confirmation**: Требуется подтверждение пользователя

**Обработка**:
```python
if 'safety_decision' in function_call.args:
    decision = function_call.args['safety_decision']
    if decision.get('decision') == 'require_confirmation':
        print(f"⚠️ Safety warning: {decision['explanation']}")
        user_input = input("Продолжить? (y/n): ")
        if user_input.lower() != 'y':
            return {"status": "cancelled_by_user"}
        # Добавить в function_response:
        extra_fields = {"safety_acknowledgement": "true"}
```

---

## 📋 Структура ответа модели

### Типичный ответ с tool_call:

```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "text": "I will type the search query into the search bar."
          },
          {
            "function_call": {
              "name": "type_text_at",
              "args": {
                "x": 371,
                "y": 470,
                "text": "highly rated smart fridges",
                "press_enter": true
              }
            }
          }
        ]
      }
    }
  ]
}
```

### Финальный ответ (без tool_calls):

```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "text": "Task completed! I found the information about the dollar exchange rate: 1 USD = 96.50 RUB"
          }
        ]
      }
    }
  ]
}
```

---

## 🔄 Цикл агента (Рекомендуемая архитектура)

```python
# 1. Инициализация
history = [
    Content(role="user", parts=[
        Part.from_text(text="Task description"),
        Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes))
    ])
]

# 2. Основной цикл
while step < max_steps:
    # 2.1 Запрос к модели
    response = client.models.generate_content(
        model="gemini-2.5-computer-use-preview-10-2025",
        contents=history,
        config=config
    )
    
    # 2.2 Извлечение tool_calls
    model_content = response.candidates[0].content
    history.append(model_content)
    
    tool_responses = []
    for part in model_content.parts:
        if part.function_call:
            # 2.3 Выполнение действия
            result = execute_action(page, part.function_call)
            tool_responses.append(
                Part.from_function_response(
                    name=part.function_call.name,
                    response=result
                )
            )
    
    # 2.4 Отправка результата + новый скриншот
    if tool_responses:
        screenshot_bytes = page.screenshot(type="png")
        history.append(
            Content(role="user", parts=tool_responses + [
                Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes))
            ])
        )
    else:
        # Нет tool_calls - задача завершена
        break
```

---

## ⚙️ Конфигурация модели

### Базовая конфигурация:

```python
from google import genai
from google.genai.types import Tool, ComputerUse, GenerateContentConfig

config = GenerateContentConfig(
    tools=[
        Tool(
            computer_use=ComputerUse(
                environment=genai.types.Environment.ENVIRONMENT_BROWSER
            )
        )
    ],
    temperature=0.3,
    max_output_tokens=4096,
)
```

### Исключение действий:

```python
excluded_functions = ["drag_and_drop", "key_combination"]

config = GenerateContentConfig(
    tools=[
        Tool(
            computer_use=ComputerUse(
                environment=genai.types.Environment.ENVIRONMENT_BROWSER,
                excluded_predefined_functions=excluded_functions
            )
        )
    ],
    temperature=0.3,
    max_output_tokens=4096,
)
```

### Добавление пользовательских функций:

```python
custom_functions = [
    types.FunctionDeclaration.from_callable(
        client=client, 
        callable=my_custom_function
    )
]

config = GenerateContentConfig(
    tools=[
        Tool(computer_use=ComputerUse(
            environment=genai.types.Environment.ENVIRONMENT_BROWSER
        )),
        Tool(function_declarations=custom_functions)
    ],
    temperature=0.3,
    max_output_tokens=4096,
)
```

---

## 🎨 Пользовательские функции (расширение)

Вы можете добавить свои функции для специфичных задач:

```python
def take_screenshot_and_save(filename: str) -> dict:
    """Сохранить скриншот в файл.
    
    Args:
        filename: Имя файла для сохранения
    
    Returns:
        Статус операции
    """
    # Реализация
    return {"status": "saved", "filename": filename}

def read_file_content(filepath: str) -> dict:
    """Прочитать содержимое файла.
    
    Args:
        filepath: Путь к файлу
    
    Returns:
        Содержимое файла
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    return {"content": content}

# Регистрация
custom_functions = [
    types.FunctionDeclaration.from_callable(client=client, callable=take_screenshot_and_save),
    types.FunctionDeclaration.from_callable(client=client, callable=read_file_content),
]
```

---

## 🛡️ Лучшие практики безопасности

1. **Изолированная среда**: Запускайте агента в Docker/VM/изолированном профиле браузера
2. **Подтверждение HITL**: Всегда обрабатывайте `safety_decision` с `require_confirmation`
3. **Списки разрешенных URL**: Ограничьте доступные домены
4. **Логирование**: Записывайте все действия, скриншоты, ответы модели
5. **Таймауты**: Ограничивайте время выполнения задач
6. **Системные инструкции**: Добавляйте правила безопасности в промпт

Пример системной инструкции:
```python
system_instruction = """
SAFETY RULES:
- Never download executable files
- Never submit payment forms without explicit user confirmation
- Never delete or modify files on the system
- Never visit suspicious URLs
- Always verify SSL certificates
- Stop immediately if you encounter login pages requiring credentials
"""

config = GenerateContentConfig(
    system_instruction=system_instruction,
    tools=[...],
    temperature=0.3,
)
```

---

## 📊 Параллельный вызов функций

Модель может вернуть **несколько действий за один ход**:

```json
{
  "content": {
    "parts": [
      {"text": "I'll click the button and scroll down"},
      {"function_call": {"name": "click_at", "args": {"x": 500, "y": 300}}},
      {"function_call": {"name": "scroll_document", "args": {"direction": "down"}}}
    ]
  }
}
```

**Обработка**:
```python
tool_responses = []
for part in model_content.parts:
    if part.function_call:
        result = await execute_action(page, part.function_call)
        tool_responses.append(
            Part.from_function_response(
                name=part.function_call.name,
                response=result
            )
        )

# Все результаты отправляем вместе
history.append(
    Content(role="user", parts=tool_responses + [screenshot_part])
)
```

---

## 🚀 Примеры использования

### Пример 1: Простой поиск

```python
task = "Открой Google и найди информацию о Python"

# Модель вернет последовательность:
# 1. open_web_browser или navigate(url="https://google.com")
# 2. type_text_at(x=500, y=300, text="Python", press_enter=True)
# 3. scroll_document(direction="down")
# 4. Финальный текстовый ответ с результатами
```

### Пример 2: Заполнение формы

```python
task = "Заполни регистрационную форму на example.com"

# Модель вернет:
# 1. navigate(url="https://example.com/signup")
# 2. type_text_at(x=300, y=200, text="John Doe", press_enter=False)
# 3. click_at(x=300, y=250)  # Next field
# 4. type_text_at(x=300, y=250, text="john@example.com", press_enter=False)
# 5. click_at(x=400, y=500)  # Submit button
```

### Пример 3: Сложная навигация

```python
task = "Найди на Amazon товар 'laptop' дешевле $500 и добавь в корзину"

# Модель вернет:
# 1. navigate(url="https://amazon.com")
# 2. type_text_at(..., text="laptop", press_enter=True)
# 3. scroll_document(direction="down")
# 4. click_at(...)  # Filters
# 5. type_text_at(..., text="500", press_enter=False)  # Price filter
# 6. scroll_document(direction="down")
# 7. click_at(...)  # Product
# 8. click_at(...)  # Add to cart button
```

---

## ⚠️ Ограничения и известные проблемы

1. **Нет прямого доступа к DOM**: Модель работает только через скриншоты (vision)
2. **Координаты не всегда точные**: Нормализация 0-999 может давать погрешность
3. **Нет чтения текста из скриншота напрямую**: Только визуальное распознавание
4. **Требует подтверждения для рискованных действий**: CAPTCHA, платежи, удаление
5. **Не для desktop приложений**: ENVIRONMENT_BROWSER только для веб-браузеров
6. **Preview модель**: Может содержать баги, не для production

---

## 📚 Ссылки на документацию

- [Официальная документация Computer Use](https://ai.google.dev/gemini-api/docs/computer-use)
- [Reference Implementation (GitHub)](https://github.com/google/computer-use-preview/)
- [Demo Environment (Browserbase)](http://gemini.browserbase.com/)
- [Gemini API Terms](https://ai.google.dev/gemini-api/terms)

---

## 💡 Рекомендации по использованию

### ✅ Хорошо подходит для:
- Автоматизация веб-форм
- Web scraping с динамическим контентом
- Тестирование UI веб-приложений
- Исследование сайтов (price comparison, product research)
- Автоматизация повторяющихся задач в браузере

### ❌ НЕ подходит для:
- Desktop приложения (используйте другие инструменты)
- Критически важные операции (banking, medical)
- Задачи требующие 100% точности координат
- Production системы (это preview модель)
- Задачи с конфиденциальными данными

---

## 🎯 Итоговая рекомендация

Для **browser-use** проекта:
- ❌ **НЕ использовать** `gemini-2.5-computer-use-preview-10-2025` - он не совместим с browser-use Agent
- ✅ **Использовать** `gemini-2.0-flash-exp` - полная совместимость, JSON mode, vision support
- ✅ Для прямого использования Computer Use - только через собственный цикл (как в `test_agent3.py`)

---

**Дата создания**: 17 октября 2025  
**Версия документа**: 1.0  
**Автор**: AI Assistant
