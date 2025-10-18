# 🔐 Настройка переменных окружения

## Для запуска тестов CoolPrompt и GPT-5

Все скрипты используют переменные окружения для API ключей (безопасность).

### Шаг 1: Установите переменную окружения

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY = "your-api-key-here"
```

**Windows (CMD):**
```cmd
set OPENAI_API_KEY=your-api-key-here
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### Шаг 2: Или создайте .env файл

Скопируйте `.env.example` в `.env` и укажите свой ключ:

```bash
cp .env.example .env
# Отредактируйте .env и добавьте свой API ключ
```

### Шаг 3: Запустите тесты

```bash
python test_coolprompt_gpt5.py
python test_gpt5_final.py
```

## 📝 Важно

- **Никогда** не коммитьте API ключи в Git
- Файл `.env` добавлен в `.gitignore`
- Используйте `.env.example` как шаблон
