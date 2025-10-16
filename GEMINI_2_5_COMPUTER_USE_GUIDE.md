# 🔥 Gemini 2.5 Computer Use API - Руководство

## Что это?

**gemini-2.5-computer-use-preview-10-2025** - это НОВАЯ модель от Google, специально разработана для browser automation и выполнения действий на компьютере. Это именно то, что нужно для browser-use!

## ✅ Преимущества

| Параметр | Описание |
|----------|---------|
| **Назначение** | Нативная поддержка browser automation (лучше чем flash для этого) |
| **Качество** | Отличное понимание UI/UX, может взаимодействовать с элементами напрямую |
| **Speed** | Быстрая (промежуточная между flash и pro) |
| **Цена** | Стандартная rate (примерно как gemini-2.5-flash) |
| **API Access** | Требует доступа к preview API |

## 🔧 Как использовать

### 1. Включить модель в конфиге

Отредактируйте `Browser_Use/models_config.json`:

```json
"gemini-2.5-computer-use": {
  "enabled": true,  // ← Измените на true
  "model_string": "gemini-2.5-computer-use-preview-10-2025",
  "requests_per_minute": 10,
  "requests_per_day": 250,
  ...
}
```

**Важно:** Убедитесь, что другие модели имеют `"enabled": false`

### 2. Убедитесь, что API ключ имеет доступ

1. Перейдите на [Google AI Studio](https://aistudio.google.com/app/apikeys)
2. Проверьте, что ваш API ключ активен
3. Убедитесь в файле `.env`:
   ```bash
   GOOGLE_API_KEY=ваш_ключ_здесь
   ```

### 3. Запустите приложение

Просто запустите ваш скрипт как обычно:

```bash
python Browser_Use/airtable_registration_dual_browser.py
```

Приложение автоматически загрузит `gemini-2.5-computer-use` из конфига.

## 📊 Сравнение моделей

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COMPARISON TABLE                                 │
├──────────────────────┬──────────────────┬──────────────────────────┤
│ Параметр             │ gemini-2.5-flash │ gemini-2.5-computer-use  │
├──────────────────────┼──────────────────┼──────────────────────────┤
│ Назначение           │ General purpose  │ 🎯 Browser automation    │
│ UI/UX понимание      │ Хорошее          │ 🔥 Отличное              │
│ Browser interaction  │ Хорошее          │ 🔥 Нативное              │
│ Скорость             │ Быстрая          │ Средняя                  │
│ Rate Limit           │ 10 req/min       │ 10 req/min               │
│ API Access           │ Доступна всем    │ Preview (может быть)     │
│ Рекомендуется для    │ Быстрые тесты    │ Production browser tasks │
└──────────────────────┴──────────────────┴──────────────────────────┘
```

## ⚠️ Важные замечания

### Access Requirements
- ✅ Обычно доступна для всех с Google AI API доступом
- ⚠️ Если получите ошибку "Model not found" - свяжитесь с Google или используйте flash

### Error Handling
Если модель недоступна, автоматически используется fallback:
```python
# Если gemini-2.5-computer-use не доступна:
# 1. Будет ошибка при инициализации
# 2. Измените в models_config.json обратно на gemini-2.5-flash
# 3. Перезапустите
```

## 🚀 Пример использования

```python
from config import get_llm, ModelConfig

# Проверить активную модель
config = ModelConfig.get_enabled_model()
print(f"Используется модель: {config['name']}")
print(f"Model string: {config['model_string']}")

# Получить LLM
llm = get_llm()

# Использовать в agent
agent = Agent(
    task="Зарегистрируйся на airtable.com",
    llm=llm,
    # ... другие параметры
)

result = await agent.run()
```

## 📈 Rate Limits

```
Текущие лимиты для gemini-2.5-computer-use:
- 10 запросов в минуту
- 250 запросов в день
- При превышении будет delay или ошибка

Это достаточно для:
- ~250 независимых регистраций/день
- ~30 регистраций/час
```

## 🔍 Отладка

### Проверить конфигурацию
```bash
python -c "from config import ModelConfig; ModelConfig.list_models()"
```

### Проверить активную модель
```bash
python -c "from config import ModelConfig; print(ModelConfig.get_enabled_model())"
```

### Логи
Приложение выведет в консоль:
```
⚙️  Модель: gemini-2.5-computer-use-preview-10-2025
📊 Rate: 10 запросов/мин, 250 запросов/день
```

## 🎯 Рекомендации

### Когда использовать gemini-2.5-computer-use
- ✅ Production браузер tasks
- ✅ Сложные регистрации с нестандартными формами
- ✅ Когда flash дает ValidationError
- ✅ Когда нужна лучшая надежность

### Когда использовать gemini-2.5-flash
- ✅ Быстрые тесты
- ✅ Простые задачи
- ✅ Когда скорость критична
- ✅ Экономия rate limit

## 📞 Проблемы

### "Model not found" ошибка
```
❌ Ошибка: Model not found: gemini-2.5-computer-use-preview-10-2025
```
**Решение:** Ваш API ключ не имеет доступа к этой модели. Используйте gemini-2.5-flash.

### "Quota exceeded" ошибка
```
❌ Ошибка: Resource has been exhausted
```
**Решение:** Превышены rate limits. Подождите или используйте другой API ключ.

### ValidationError с computer-use
```
❌ ValidationError: action Field required
```
**Решение:** Даже computer-use иногда возвращает только thinking. Отключите use_thinking:
```python
agent = Agent(
    ...,
    use_thinking=False,  # Добавьте это
    ...
)
```

## 📚 Ссылки

- [Google AI Studio API Keys](https://aistudio.google.com/app/apikeys)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Browser Use Documentation](https://browser-use.com)

---

**Версия:** 1.0  
**Дата:** 17 октября 2025  
**Статус:** ✅ Готово к использованию
