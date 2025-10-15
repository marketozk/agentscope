# 🎯 Стратегии работы с Browser-Use: Полное руководство

## 📋 Оглавление

1. [Базовые стратегии выполнения](#базовые-стратегии-выполнения)
2. [Продвинутые паттерны](#продвинутые-паттерны)
3. [Стратегии обработки данных](#стратегии-обработки-данных)
4. [Стратегии устойчивости](#стратегии-устойчивости)
5. [Стратегии оптимизации](#стратегии-оптимизации)
6. [Выбор стратегии](#выбор-стратегии)
7. [Примеры кода](#примеры-кода)

---

## 🚀 Базовые стратегии выполнения

### 1. Single Prompt (Единый промпт)

**Описание:** Вся задача описывается в одной инструкции.

**Когда использовать:**
- ✅ Простые линейные задачи
- ✅ Не требуется промежуточный контроль
- ✅ Задача понятна и однозначна
- ✅ Минимум API вызовов

**Преимущества:**
- Минимальное количество запросов к API
- Быстрое выполнение
- Простота реализации

**Недостатки:**
- Нет контроля над промежуточными шагами
- Сложно отладить при ошибках
- Не подходит для сложных workflow

```python
agent = Agent(
    task="Открой yandex.ru, найди 'погода', открой первый результат",
    llm=llm
)
result = await agent.run()
```

### 2. Step-by-Step (Пошаговое выполнение)

**Описание:** Задача разбивается на отдельные шаги.

**Когда использовать:**
- ✅ Сложные многоэтапные задачи
- ✅ Нужен контроль над каждым шагом
- ✅ Требуется обработка промежуточных результатов
- ✅ Условная логика между шагами

**Преимущества:**
- Полный контроль над процессом
- Легче отладить
- Можно добавить условную логику
- Промежуточные результаты

**Недостатки:**
- Больше API вызовов
- Медленнее выполнение
- Сложнее реализация

```python
# ⚠️ ВНИМАНИЕ: execute_task() НЕ СУЩЕСТВУЕТ в browser-use!
# Правильный подход - создавать нового агента для каждого шага:

# Шаг 1
agent1 = Agent(task="Открой yandex.ru и дождись загрузки", llm=llm)
await agent1.run()

# Шаг 2
agent2 = Agent(task="Найди поле поиска и введи 'погода'", llm=llm)
await agent2.run()

# Шаг 3
agent3 = Agent(task="Нажми кнопку поиска и открой первый результат", llm=llm)
result = await agent3.run()
```

### 3. Hybrid (Гибридный подход)

**Описание:** Комбинация единого промпта и множественных агентов.

**Когда использовать:**
- ✅ Группы связанных действий
- ✅ Баланс между контролем и эффективностью
- ✅ Разные фазы задачи

```python
# Фаза 1: Навигация и авторизация (единый промпт)
task1 = """
1. Открой сайт example.com
2. Найди форму входа
3. Введи логин и пароль
4. Нажми кнопку входа
"""
agent1 = Agent(task=task1, llm=llm)
await agent1.run()

# Фаза 2: Работа с данными (отдельные агенты)
for item in items:
    task = f"""
    1. Найди элемент {item}
    2. Обработай его
    3. Сохрани результат
    """
    agent = Agent(task=task, llm=llm)
    await agent.run()
```
```

---

## 🔧 Продвинутые паттерны

### 4. Pipeline Pattern (Конвейер)

**Описание:** Последовательная обработка с передачей результатов.

```python
class BrowserPipeline:
    def __init__(self, llm):
        self.stages = []
        self.llm = llm
    
    def add_stage(self, name, task):
        self.stages.append((name, task))
    
    async def run(self):
        results = {}
        context = ""
        
        for name, task in self.stages:
            agent = Agent(
                task=f"{context}\\n{task}",
                llm=self.llm
            )
            result = await agent.run()
            results[name] = result
            context = f"Предыдущий результат: {result}"
        
        return results

# Использование
pipeline = BrowserPipeline(llm)
pipeline.add_stage("search", "Найди информацию о продукте")
pipeline.add_stage("compare", "Сравни цены на разных сайтах")
pipeline.add_stage("report", "Создай отчет о найденном")
```

### 5. Parallel Execution (Параллельное выполнение)

**Описание:** Одновременное выполнение независимых задач.

```python
async def parallel_search(queries, llm):
    tasks = []
    
    for query in queries:
        agent = Agent(
            task=f"Найди информацию о {query}",
            llm=llm
        )
        tasks.append(agent.run())
    
    results = await asyncio.gather(*tasks)
    return dict(zip(queries, results))

# Использование
results = await parallel_search(
    ["Python", "JavaScript", "Rust"],
    llm
)
```

### 6. State Machine Pattern (Конечный автомат)

**Описание:** Управление сложными workflow с состояниями.

```python
class BrowserStateMachine:
    def __init__(self, llm):
        self.llm = llm
        self.state = "START"
        self.data = {}
    
    async def transition(self, action):
        transitions = {
            ("START", "login"): self.handle_login,
            ("LOGGED_IN", "search"): self.handle_search,
            ("SEARCH_DONE", "extract"): self.handle_extract,
            ("EXTRACTED", "save"): self.handle_save
        }
        
        handler = transitions.get((self.state, action))
        if handler:
            await handler()
        else:
            raise ValueError(f"Invalid transition: {self.state} -> {action}")
    
    async def handle_login(self):
        agent = Agent(task="Авторизуйся на сайте", llm=self.llm)
        await agent.run()
        self.state = "LOGGED_IN"
```

### 7. Observer Pattern (Наблюдатель)

**Описание:** Мониторинг изменений на странице.

```python
class PageMonitor:
    def __init__(self, llm, check_interval=5):
        self.llm = llm
        self.check_interval = check_interval
        self.observers = []
    
    def attach(self, observer):
        self.observers.append(observer)
    
    async def monitor(self, url, condition):
        while True:
            # Создаем агента для каждой проверки
            check_task = f"""
            1. Открой {url}
            2. Проверь условие: {condition}
            3. Если условие выполнено, верни "CONDITION_MET"
            4. Иначе верни "NO_CHANGE"
            """
            agent = Agent(task=check_task, llm=self.llm)
            result = await agent.run()
            
            if "CONDITION_MET" in str(result).upper():
                for observer in self.observers:
                    await observer.notify(result)
            
            await asyncio.sleep(self.check_interval)
```

---

## 📊 Стратегии обработки данных

### 8. Extraction Strategy (Извлечение данных)

**Варианты:**

```python
# 1. Простое извлечение
async def simple_extract(url, selectors):
    task = f"Открой {url} и извлеки: {', '.join(selectors)}"
    return await agent.run()

# 2. Структурированное извлечение
async def structured_extract(url, schema):
    task = f"""
    Открой {url} и извлеки данные в формате:
    {json.dumps(schema, indent=2, ensure_ascii=False)}
    """
    return await agent.run()

# 3. Итеративное извлечение
async def iterative_extract(url, item_selector, fields):
    results = []
    
    # Сначала получаем количество элементов
    count_task = f"""
    1. Открой {url}
    2. Найди все элементы {item_selector}
    3. Верни их количество (только число)
    """
    agent = Agent(task=count_task, llm=llm)
    count_result = await agent.run()
    count = int(str(count_result).strip())
    
    # Извлекаем данные из каждого элемента
    for i in range(count):
        extract_task = f"""
        1. Найди элемент {item_selector} номер {i+1}
        2. Извлеки из него поля: {', '.join(fields)}
        3. Верни результат в формате JSON
        """
        agent = Agent(task=extract_task, llm=llm)
        item_data = await agent.run()
        results.append(item_data)
    
    return results
```

### 9. Validation Strategy (Валидация данных)

```python
class DataValidator:
    def __init__(self, llm):
        self.llm = llm
        self.rules = {}
    
    def add_rule(self, field, rule):
        self.rules[field] = rule
    
    async def validate(self, data):
        errors = []
        
        for field, rule in self.rules.items():
            if field in data:
                validate_task = f"""
                Проверь значение '{data[field]}' для поля '{field}'
                Правило: {rule}
                Верни "VALID" если валидно, иначе опиши ошибку
                """
                agent = Agent(task=validate_task, llm=self.llm)
                result = await agent.run()
                
                if "VALID" not in str(result).upper():
                    errors.append({
                        "field": field,
                        "error": str(result)
                    })
                    f"Проверь, что '{data[field]}' {rule}"
                )
                if "не" in is_valid.lower():
                    errors.append(f"{field}: {is_valid}")
        
        return errors

# Использование
validator = DataValidator(llm)
validator.add_rule("email", "является валидным email адресом")
validator.add_rule("phone", "содержит 10 цифр")
```

---

## 🛡️ Стратегии устойчивости

### 10. Retry Strategy (Повторные попытки)

```python
async def retry_with_backoff(task, max_retries=3, base_delay=2):
    for attempt in range(max_retries):
        try:
            agent = Agent(task=task, llm=llm)
            return await agent.run()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            delay = base_delay * (2 ** attempt)
            print(f"Попытка {attempt + 1} неудачна, ожидание {delay}с...")
            await asyncio.sleep(delay)
```

### 11. Fallback Strategy (Запасные варианты)

```python
async def multi_source_search(query):
    sources = [
        ("yandex.ru", f"Найди '{query}' на Яндексе"),
        ("google.com", f"Найди '{query}' в Google"),
        ("duckduckgo.com", f"Найди '{query}' в DuckDuckGo")
    ]
    
    for source, task in sources:
        try:
            agent = Agent(task=task, llm=llm)
            result = await agent.run()
            if result and "не найдено" not in result.lower():
                return {"source": source, "result": result}
        except Exception as e:
            print(f"Ошибка с {source}: {e}")
            continue
    
    return None
```

### 12. Circuit Breaker (Предохранитель)

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, task, llm):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            agent = Agent(task=task, llm=llm)
            result = await agent.run()
            
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise
```

---

## ⚡ Стратегии оптимизации

### 13. Caching Strategy (Кэширование)

```python
class BrowserCache:
    def __init__(self, ttl=3600):
        self.cache = {}
        self.ttl = ttl
    
    def get_key(self, task):
        return hashlib.md5(task.encode()).hexdigest()
    
    async def execute(self, task, llm):
        key = self.get_key(task)
        
        if key in self.cache:
            timestamp, result = self.cache[key]
            if time.time() - timestamp < self.ttl:
                print(f"Cache hit for: {task[:50]}...")
                return result
        
        agent = Agent(task=task, llm=llm)
        result = await agent.run()
        self.cache[key] = (time.time(), result)
        
        return result
```

### 14. Batch Processing (Пакетная обработка)

```python
async def batch_process(items, batch_size=5, task_template=None):
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_task = f"""
        Обработай следующие элементы:
        {json.dumps(batch, ensure_ascii=False)}
        
        Для каждого: {task_template}
        """
        
        agent = Agent(task=batch_task, llm=llm)
        batch_results = await agent.run()
        results.extend(batch_results)
        
        # Пауза между батчами для rate limiting
        if i + batch_size < len(items):
            await asyncio.sleep(2)
    
    return results
```

### 15. Lazy Loading (Ленивая загрузка)

```python
class LazyBrowserData:
    def __init__(self, url, llm):
        self.url = url
        self.llm = llm
        self._data = None
        self._loaded = False
    
    async def get(self, field):
        if not self._loaded:
            await self._load()
        
        if field not in self._data:
            # Загружаем только нужное поле
            agent = Agent(
                task=f"Открой {self.url} и извлеки только {field}",
                llm=self.llm
            )
            self._data[field] = await agent.run()
        
        return self._data[field]
    
    async def _load(self):
        # Загрузка базовых данных
        agent = Agent(
            task=f"Открой {self.url} и извлеки основную информацию",
            llm=self.llm
        )
        self._data = await agent.run()
        self._loaded = True
```

---

## 🎯 Выбор стратегии

### Матрица выбора

| Стратегия | Простота | Контроль | Производительность | Масштабируемость |
|-----------|----------|----------|-------------------|------------------|
| Single Prompt | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Step-by-Step | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Hybrid | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Pipeline | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Parallel | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| State Machine | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

### Когда использовать какую стратегию

**Single Prompt:**
- Простой поиск информации
- Быстрая проверка данных
- Разовые действия

**Step-by-Step:**
- Заполнение форм
- Многоэтапные процессы
- Необходимость валидации

**Hybrid:**
- Комбинированные задачи
- Баланс скорости и контроля
- Разные фазы работы

**Pipeline:**
- Сбор и обработка данных
- ETL процессы
- Последовательные трансформации

**Parallel:**
- Массовая обработка
- Независимые задачи
- Мониторинг нескольких источников

**State Machine:**
- Сложные workflow
- Условная логика
- Регистрации и авторизации

---

## 💻 Примеры кода

### Пример: Airtable Registration (State Machine)

```python
class AirtableRegistration:
    def __init__(self, llm):
        self.llm = llm
        self.state = "INIT"
    
    async def run(self):
        # Шаг 1: Открываем Airtable
        task1 = "Открой https://airtable.com/invite/r/xxx и дождись загрузки"
        agent1 = Agent(task=task1, llm=self.llm)
        await agent1.run()
        self.state = "OPENED"
        
        # Шаг 2: Получаем email
        task2 = """
        1. Открой новую вкладку
        2. Перейди на temp-mail.io
        3. Скопируй email адрес
        """
        agent2 = Agent(task=task2, llm=self.llm)
        result = await agent2.run()
        self.state = "EMAIL_OBTAINED"
        
        # Шаг 3: Заполняем форму
        task3 = f"""
        1. Переключись на первую вкладку с Airtable
        2. Заполни форму регистрации
        3. Отправь форму
        """
        agent3 = Agent(task=task3, llm=self.llm)
        await agent3.run()
        self.state = "COMPLETED"
        self.state = "OPENED"
        
        # Шаг 2
        email = await self.get_temp_email()
        self.state = "EMAIL_OBTAINED"
        
        # Шаг 3
        await self.fill_form(email)
        self.state = "FORM_SUBMITTED"
        
        # Шаг 4
        await self.wait_for_confirmation()
        self.state = "COMPLETED"
```

### Пример: Price Comparison (Pipeline)

```python
pipeline = BrowserPipeline(llm)
pipeline.add_stage("search_ozon", "Найди товар на Ozon")
pipeline.add_stage("search_wb", "Найди товар на Wildberries")
pipeline.add_stage("compare", "Сравни цены")
results = await pipeline.run()
```

### Пример: Multi-tab Search (Parallel)

```python
async def search_all_engines(query):
    engines = ["yandex.ru", "google.com", "duckduckgo.com"]
    tasks = []
    
    for engine in engines:
        agent = Agent(
            task=f"Найди '{query}' на {engine}",
            llm=llm
        )
        tasks.append(agent.run())
    
    return await asyncio.gather(*tasks)
```

---

## 📚 Рекомендации

### Для начинающих
1. Начните с **Single Prompt** для простых задач
2. Переходите к **Step-by-Step** когда нужен контроль
3. Используйте **Hybrid** для баланса

### Для продвинутых
1. **Pipeline** для сложных workflow
2. **State Machine** для условной логики
3. **Parallel** для масштабирования

### Для production
1. Всегда используйте **Retry Strategy**
2. Реализуйте **Circuit Breaker** для устойчивости
3. Добавьте **Caching** для оптимизации
4. Используйте **Monitoring** для отслеживания

---

## 🎓 Заключение

Выбор правильной стратегии - ключ к эффективной автоматизации браузера. Начните с простых подходов и постепенно добавляйте сложность по мере необходимости.

**Золотые правила:**
- 🎯 Простота важнее сложности
- 🛡️ Устойчивость важнее скорости
- 📊 Измеряйте и оптимизируйте
- 🔄 Итерируйте и улучшайте
