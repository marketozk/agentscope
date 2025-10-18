# 📧 Стратегии Обхода Блокировки Temp-Mail

## Проблема
- Блокировка при навигации на temp-mail.org 
- Cloudflare/другие анти-бот системы
- Timeout при ожидании load

## Решение: Многоуровневая Стратегия

### 1️⃣ Модификация navigate() действия

**Текущий код (ненадежный):**
```python
await page.goto(url, wait_until="networkidle", timeout=30000)
```

**Проблемы:**
- `networkidle` слишком строгий - ждёт когда все сетевые запросы завершатся
- temp-mail часто имеет фоновые запросы
- Может зависнуть на 30+ секунд

**Решение:**
```python
# Вариант 1: Более мягкое ожидание
await page.goto(url, wait_until="domcontentloaded", timeout=20000)

# Вариант 2: С дополнительным ожиданием
await page.goto(url, wait_until="load", timeout=15000)
await page.wait_for_timeout(2000)  # Даём странице 2 сек на стабилизацию

# Вариант 3: Без ожидания (для особенно сложных случаев)
asyncio.create_task(page.goto(url))
await page.wait_for_timeout(5000)  # Просто ждём 5 сек
```

### 2️⃣ Добавить Headers для Маскировки

**Перед навигацией:**
```python
# Установить Human-like headers
await page.set_extra_http_headers({
    'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
})

# Установить User-Agent (необходимо ДО создания context!)
context = await browser.new_context(
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
```

### 3️⃣ Добавить Задержки Перед Навигацией

```python
# Перед navigate:
await page.wait_for_timeout(2000)  # 2 сек пауза
```

Это помогает избежать триггеров анти-бота по скорости.

### 4️⃣ Обработать Cloudflare Challenge

```python
async def handle_cloudflare_challenge(page, timeout=60):
    """Если Cloudflare challenge - ждём его прохождения"""
    try:
        # Ждём исчезновения Cloudflare элементов
        await page.wait_for_selector('body:not(:has(iframe#challenge-form))', timeout=timeout*1000)
        return True
    except:
        return False
```

### 5️⃣ Альтернативные URL для Temp-Mail

```
# Основной (может быть заблокирован)
https://temp-mail.org/en/

# Альтернативы:
https://temp-mail.org/  (без /en/)
https://www.temp-mail.org/en/
https://tempmail.com/  (другой сервис)
https://guerrillamail.com/  (альтернатива)
https://maildrop.cc/  (альтернатива)
```

## Применение Стратегии в Коде

Нужно модифицировать `execute_computer_use_action()` функцию, раздел `navigate`:

```python
elif action == "navigate":
    url = args.get("url", "")
    if not is_allowed_url(url):
        return {"success": False, "message": f"Navigation blocked by policy: {url}", "url": page.url}
    
    try:
        # СТРАТЕГИЯ 1: Добавить delay перед навигацией
        await page.wait_for_timeout(1000)
        
        # СТРАТЕГИЯ 2: Использовать domcontentloaded вместо networkidle
        try:
            print(f"  🌐 Navigating to {url}...")
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(1500)  # Даём странице стабилизироваться
        except Exception as e:
            print(f"  ⚠️  domcontentloaded не сработал ({str(e)[:50]}). Попытка 2...")
            
            # СТРАТЕГИЯ 3: load вместо domcontentloaded
            try:
                await page.goto(url, wait_until="load", timeout=15000)
            except Exception as e2:
                print(f"  ⚠️  load не сработал ({str(e2)[:50]}). Попытка 3...")
                
                # СТРАТЕГИЯ 4: Минимальное ожидание
                try:
                    # Запустить навигацию без ожидания
                    navigation = page.goto(url, wait_until=None)
                    await asyncio.sleep(3)  # Просто ждём 3 сек
                    await navigation
                except:
                    # СТРАТЕГИЯ 5: Даже если goto фейлится, проверим что загрузилось
                    await page.wait_for_timeout(5000)
                    print(f"  ℹ️  Page loaded after timeout: {page.url}")
        
        # СТРАТЕГИЯ 6: Обработать Cloudflare challenge если есть
        blocked, signal = await detect_cloudflare_block(page)
        if blocked:
            print(f"  🛡️  Cloudflare detected: {signal}")
            # Ждём 10 сек для автоматического прохождения
            await page.wait_for_timeout(10000)
            # Проверяем снова
            blocked, signal = await detect_cloudflare_block(page)
            if not blocked:
                print(f"  ✅ Cloudflare challenge passed!")
        
        return {"success": True, "message": f"Navigated to {page.url}", "url": page.url}
        
    except Exception as e:
        print(f"  ❌ Navigation failed: {str(e)}")
        return {"success": False, "message": f"Navigate failed: {str(e)}", "url": page.url}
```

## Дополнительно: Persistence Profile

Использование persistent profile с сохраненными cookies:
- Cookies от temp-mail.org сохраняются в профиле
- При повторной навигации browser уже "известен" сервису
- Это снижает шанс блокировки

**Текущий файл профиля:**
```
C:\Users\regis\...\profiles\unified_default
```

## Рекомендации

1. **Приоритет методов обхода:**
   - [ ] 1. Persistent profile + cookies (уже реализовано)
   - [ ] 2. Задержка перед навигацией (1-2 сек)
   - [ ] 3. `wait_until="domcontentloaded"` вместо "networkidle"
   - [ ] 4. Дополнительное ожидание после load (1-2 сек)
   - [ ] 5. Handling Cloudflare challenge (10-15 сек)
   - [ ] 6. Попытка с другим User-Agent
   - [ ] 7. Использовать альтернативный URL temp-mail

2. **Максимальное время на навигацию:** 60 сек (включая все retry)

3. **Логирование:** Все попытки навигации должны быть залогированы

## Быстрое Применение

Нужно изменить в файле `test_agent3_air.py`, строки ~440-455:

```python
# ВЕС НА ТЕКУЩЕЕ:
await page.goto(url, wait_until="networkidle", timeout=30000)

# НА ЭТО:
await page.goto(url, wait_until="domcontentloaded", timeout=20000)
await page.wait_for_timeout(1500)
```

Это даст первый прирост в надежности!
