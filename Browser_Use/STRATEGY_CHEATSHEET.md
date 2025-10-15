# 🎯 Шпаргалка по выбору стратегии Browser-Use

## 🚀 Быстрый выбор

### Если задача...

**✅ Простая (1-3 шага, линейная)**
```python
# Используйте Single Prompt
agent = Agent(task="Открой сайт и найди информацию", llm=llm)
await agent.run()
```

**📊 Требует извлечения данных**
```python
# Используйте Extraction Strategy
task = "Открой сайт и извлеки: заголовок, цену, описание"
```

**🔄 Повторяющаяся**
```python
# Используйте Batch Processing
await batch_process(items, batch_size=5)
```

**⚡ Требует скорости**
```python
# Используйте Parallel + Caching
tasks = [create_task(item) for item in items]
results = await asyncio.gather(*tasks)
```

**🛡️ Критична к ошибкам**
```python
# Используйте Retry + Circuit Breaker
result = await retry_with_backoff(task, max_retries=3)
```

**🌳 Имеет условия**
```python
# ⚠️ ВАЖНО: execute_task() не существует!
# Правильный подход - создавать агентов для каждого условия

if condition:
    task_a = "Сделай действие A"
    agent = Agent(task=task_a, llm=llm)
    await agent.run()
else:
    task_b = "Сделай действие B"
    agent = Agent(task=task_b, llm=llm)
    await agent.run()
```

---

## 📋 Матрица решений

| Ваша задача | Рекомендуемая стратегия | Пример |
|-------------|------------------------|---------|
| Поиск информации | Single Prompt | Найти новость |
| Заполнение формы | Step-by-Step | Регистрация |
| Мониторинг цен | Observer + Cache | Отслеживание |
| Сбор данных | Pipeline + Extraction | Парсинг |
| Массовая обработка | Batch + Parallel | 100+ товаров |
| Сложный workflow | State Machine | Покупка |
| Работа с вкладками | Step-by-Step | Многооконный |
| Ожидание событий | Observer | Email confirm |

---

## 🔥 Комбинации стратегий

### Надёжный сбор данных
```
Retry → Cache → Extraction → Validation
```

### Быстрый мониторинг
```
Parallel → Observer → Notification
```

### Умная автоматизация
```
State Machine → Pipeline → Fallback
```

### Регистрация аккаунта
```
State Machine → Step-by-Step → Observer
```

---

## ⚠️ Антипаттерны

❌ **НЕ используйте:**
- Single Prompt для 10+ шагов
- Step-by-Step для простого поиска
- Parallel без rate limiting
- State Machine для линейных задач

---

## 💡 Правило 80/20

80% задач решаются тремя стратегиями:
1. **Single Prompt** - простые задачи
2. **Step-by-Step** - средние задачи
3. **Hybrid** - сложные задачи

Остальные 20% требуют продвинутых паттернов.

---

## 🎯 Дерево решений

```
┌─────────────────────┐
│  Анализ задачи      │
└──────────┬──────────┘
           │
    ┌──────▼──────┐
    │  Простая?   │
    └──┬───────┬──┘
       │       │
      Да       Нет
       │       │
       │    ┌──▼──────────┐
       │    │ Контроль?   │
       │    └──┬───────┬──┘
       │       │       │
       │      Да       Нет
       │       │       │
       │       │    ┌──▼─────┐
       │       │    │ Hybrid │
       │       │    └────────┘
       │       │
       │    ┌──▼──────────┐
       │    │ Условия?    │
       │    └──┬───────┬──┘
       │       │       │
       │      Да       Нет
       │       │       │
       │   ┌───▼────┐  │
       │   │ State  │  │
       │   │Machine │  │
       │   └────────┘  │
       │               │
       │            ┌──▼─────┐
       │            │ Step-  │
       │            │by-Step │
       │            └────────┘
       │
    ┌──▼────────┐
    │  Single   │
    │  Prompt   │
    └───────────┘
```

---

## 📊 Сравнительная таблица

| Критерий | Single | Step-by-Step | Hybrid | Pipeline | State Machine |
|----------|--------|--------------|--------|----------|---------------|
| **Простота** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| **Контроль** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Скорость** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **API вызовов** | Минимум | Много | Средне | Средне | Много |
| **Отладка** | Сложно | Легко | Средне | Легко | Легко |

---

## 🛠️ Практические примеры

### Задача: Поиск на Яндекс
**Стратегия:** Single Prompt
```python
agent = Agent(
    task="Открой yandex.ru и найди 'погода в Москве'",
    llm=llm
)
```

### Задача: Регистрация в Airtable
**Стратегия:** State Machine + Step-by-Step
```python
class Registration:
    state = "INIT"
    
    async def run(self):
        await self.open_site()       # state → OPENED
        await self.get_email()        # state → EMAIL
        await self.fill_form()        # state → FILLED
        await self.confirm()          # state → CONFIRMED
```

### Задача: Сбор цен с 10 сайтов
**Стратегия:** Parallel Execution
```python
tasks = [search_site(site) for site in sites]
results = await asyncio.gather(*tasks)
```

### Задача: Заполнение 100 форм
**Стратегия:** Batch Processing
```python
for i in range(0, 100, 10):
    batch = forms[i:i+10]
    await process_batch(batch)
    await asyncio.sleep(2)  # Rate limiting
```

---

## 🎓 Рекомендации по уровням

### Новичок
- Начните с Single Prompt
- Изучите Step-by-Step
- Практикуйте на простых задачах

### Средний уровень
- Используйте Hybrid для баланса
- Экспериментируйте с Pipeline
- Добавьте Retry Strategy

### Эксперт
- Комбинируйте стратегии
- Используйте State Machine
- Оптимизируйте с Caching

---

## ⚡ Быстрые советы

1. **Всегда начинайте с простого** - Single Prompt → Step-by-Step → State Machine
2. **Тестируйте отдельно** - каждый шаг должен работать независимо
3. **Добавляйте retry** - сеть не всегда стабильна
4. **Используйте rate limiting** - избегайте блокировок
5. **Логируйте состояния** - упрощает отладку

---

## 🔍 Чеклист перед выбором

- [ ] Сколько шагов в задаче? (1-3 = Simple, 4-10 = Medium, 10+ = Complex)
- [ ] Нужна ли условная логика? (Да → State Machine)
- [ ] Нужен ли контроль каждого шага? (Да → Step-by-Step)
- [ ] Есть ли независимые задачи? (Да → Parallel)
- [ ] Требуется ли обработка данных? (Да → Pipeline)
- [ ] Важна ли скорость? (Да → Single Prompt/Parallel)
- [ ] Критична ли надежность? (Да → Retry + Circuit Breaker)

---

## 📚 Связанные документы

- `BROWSER_USE_STRATEGIES.md` - Полное руководство
- `AIRTABLE_REGISTRATION_GUIDE.md` - Пример State Machine
- `multi_scenario.py` - Примеры всех стратегий

---

**Помните:** Правильная стратегия = успешная автоматизация! 🚀
