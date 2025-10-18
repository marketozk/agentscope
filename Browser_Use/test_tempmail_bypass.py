"""
🧪 ТЕСТИРОВАНИЕ ОБХОДА TEMP-MAIL И CLOUDFLARE

Это минимальный скрипт для диагностики проблем с открытием temp-mail.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def test_tempmail_access():
    """Простой тест открытия temp-mail с разными стратегиями"""
    
    print("=" * 70)
    print("🧪 ТЕСТ ОТКРЫТИЯ TEMP-MAIL")
    print("=" * 70)
    
    playwright = await async_playwright().start()
    
    # Получаем profile path
    user_data_dir = str(Path.cwd() / "profiles" / "unified_default")
    Path(user_data_dir).mkdir(parents=True, exist_ok=True)
    
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=False,
        viewport={'width': 1440, 'height': 900},
        locale='ru-RU',
        timezone_id='Europe/Moscow',
        # 🕵️ Маскировка
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        extra_http_headers={
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        },
        args=['--start-maximized', '--disable-blink-features=AutomationControlled']
    )
    
    page = await context.new_page()
    
    try:
        # СТРАТЕГИЯ 1: Простой goto с load
        print("\n📍 СТРАТЕГИЯ 1: goto с wait_until='load' (15 сек)")
        print("   Переходим на https://temp-mail.org/en/")
        
        try:
            await page.goto("https://temp-mail.org/en/", wait_until="load", timeout=15000)
            print("   ✅ Страница загружена")
        except Exception as e:
            print(f"   ❌ Ошибка: {str(e)[:100]}")
        
        # Проверяем URL
        current_url = page.url
        print(f"   📌 Текущий URL: {current_url}")
        
        # Проверяем на Cloudflare
        title = await page.title()
        body_text = await page.evaluate("() => document.body ? document.body.innerText.slice(0, 500) : ''")
        
        print(f"   🔍 Заголовок: {title[:60]}")
        print(f"   📝 Текст (первые 100 символов): {body_text[:100]}")
        
        if "Attention Required" in title or "Cloudflare" in title:
            print("   🛡️  CLOUDFLARE BLOCK DETECTED!")
            print("   ⏳ Ждём 15 сек для автоматического прохождения...")
            await asyncio.sleep(15)
            
            # Проверяем снова
            title2 = await page.title()
            print(f"   🔍 После ожидания: {title2[:60]}")
        
        # СТРАТЕГИЯ 2: Попробуем получить email
        print("\n📍 СТРАТЕГИЯ 2: Извлечение email")
        
        try:
            # ⏳ КРИТИЧЕСКИ ВАЖНО: Ждём пока email загрузится в поле
            # Email может загружаться до 10 сек после загрузки страницы
            print("   ⏳ Ожидание загрузки email (до 15 сек)...")
            
            email_loaded = False
            for attempt in range(30):  # 30 попыток × 0.5 сек = 15 сек макс
                email = await page.evaluate("""() => {
                    const input = document.querySelector('#mail');
                    return input ? input.value : null;
                }""")
                
                if email and email.strip() and '@' in email:
                    print(f"   ✅ EMAIL НАЙДЕН (попытка {attempt+1}): {email}")
                    email_loaded = True
                    break
                else:
                    # Показываем прогресс
                    if attempt % 2 == 0:
                        print(f"   ⏳ Попытка {attempt+1}/30... (текущее значение: '{email}')")
                    await asyncio.sleep(0.5)
            
            if not email_loaded:
                print("   ❌ Email НЕ загрузился за 15 сек")
                
                # Пробуем альтернативные селекторы
                print("   🔍 Пробуем альтернативные селекторы...")
                alts = await page.evaluate("""() => {
                    const selectors = [
                        'input[type="email"]', 
                        'input[placeholder*="mail"]', 
                        'input[value*="@"]',
                        'input#email',
                        '[data-testid="email"]'
                    ];
                    for (let sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.value && el.value.includes('@')) {
                            return el.value;
                        }
                    }
                    
                    // Последняя попытка - все input'ы
                    const inputs = document.querySelectorAll('input');
                    for (let inp of inputs) {
                        if (inp.value && inp.value.includes('@')) {
                            return inp.value;
                        }
                    }
                    return null;
                }""")
                
                if alts:
                    print(f"   ✅ EMAIL (альтернативный селектор): {alts}")
                else:
                    print("   ⚠️  Email не найден даже в альтернативных селекторах")
        
        except Exception as e:
            print(f"   ❌ Ошибка извлечения: {e}")
        
        # СТРАТЕГИЯ 3: Screenshot для отладки
        print("\n📍 СТРАТЕГИЯ 3: Сохранение скриншота")
        
        try:
            screenshot_path = Path("logs") / "test_tempmail_debug.png"
            screenshot_path.parent.mkdir(exist_ok=True)
            
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"   ✅ Скриншот сохранён: {screenshot_path}")
        except Exception as e:
            print(f"   ❌ Ошибка скриншота: {e}")
        
        # Оставляем браузер открытым для проверки
        print("\n⏱️  Браузер остаётся открытым 30 сек для проверки...")
        await asyncio.sleep(30)
    
    finally:
        await context.close()
        await playwright.stop()
        print("\n✅ Закрыли браузер")


if __name__ == "__main__":
    asyncio.run(test_tempmail_access())
