"""
🧪 ПРОСТОЙ ТЕСТ: Открываем temp-mail.org и проверяем видимость email

Три варианта:
1. Без stealth (чистый браузер)
2. Со stealth (как в test_agent3_air.py)
3. С полной конфигурацией (stealth + headers + user-agent)
"""

import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def simple_test():
    print("=" * 70)
    print("🧪 ПРОСТОЙ ТЕСТ TEMP-MAIL.ORG")
    print("=" * 70)
    
    stealth = Stealth()
    
    # =============== ТЕСТ 1: БЕЗ STEALTH ===============
    print("\n" + "=" * 70)
    print("📊 ТЕСТ 1: ЧИСТЫЙ БРАУЗЕР (без stealth)")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1440, 'height': 900}
        )
        page = await context.new_page()
        
        print("🌐 Открываем temp-mail.org...")
        await page.goto("https://temp-mail.org/en/", timeout=60000)
        
        print("⏳ Ждём 10 секунд для генерации email...")
        await asyncio.sleep(10)
        
        # Проверяем email
        email = await page.evaluate("""
            document.querySelector('#mail')?.value || 'НЕ НАЙДЕНО'
        """)
        
        print(f"\n📧 Результат: {email}")
        if email and email != 'НЕ НАЙДЕНО' and '@' in email:
            print("✅ EMAIL ВИДЕН!")
        else:
            print("❌ EMAIL НЕ ВИДЕН")
        
        print("\n💤 Браузер остается открытым 15 сек для проверки...")
        await asyncio.sleep(15)
        await browser.close()
    
    # =============== ТЕСТ 2: СО STEALTH ===============
    print("\n" + "=" * 70)
    print("📊 ТЕСТ 2: СО STEALTH (как в test_agent3_air.py)")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            viewport={'width': 1440, 'height': 900}
        )
        
        # ✅ Применяем stealth
        print("🕵️  Применяем stealth...")
        await stealth.apply_stealth_async(context)
        
        page = await context.new_page()
        
        print("🌐 Открываем temp-mail.org...")
        await page.goto("https://temp-mail.org/en/", timeout=60000)
        
        print("⏳ Ждём 10 секунд для генерации email...")
        await asyncio.sleep(10)
        
        # Проверяем email
        email = await page.evaluate("""
            document.querySelector('#mail')?.value || 'НЕ НАЙДЕНО'
        """)
        
        print(f"\n📧 Результат: {email}")
        if email and email != 'НЕ НАЙДЕНО' and '@' in email:
            print("✅ EMAIL ВИДЕН!")
        else:
            print("❌ EMAIL НЕ ВИДЕН")
        
        print("\n💤 Браузер остается открытым 15 сек для проверки...")
        await asyncio.sleep(15)
        await browser.close()
    
    # =============== ТЕСТ 3: ПОЛНАЯ КОНФИГУРАЦИЯ ===============
    print("\n" + "=" * 70)
    print("📊 ТЕСТ 3: ПОЛНАЯ КОНФИГУРАЦИЯ (stealth + headers + user-agent)")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized', '--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1440, 'height': 900},
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Cache-Control': 'max-age=0',
            }
        )
        
        # ✅ Применяем stealth
        print("🕵️  Применяем stealth...")
        await stealth.apply_stealth_async(context)
        
        # Дополнительные headers
        await context.set_extra_http_headers({
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        })
        
        page = await context.new_page()
        
        print("🌐 Открываем temp-mail.org...")
        await page.goto("https://temp-mail.org/en/", timeout=60000)
        
        print("⏳ Ждём 15 секунд для генерации email...")
        await asyncio.sleep(15)
        
        # Расширенная проверка
        result = await page.evaluate("""() => {
            const input = document.querySelector('#mail');
            return {
                exists: !!input,
                visible: input ? (input.offsetWidth > 0 && input.offsetHeight > 0) : false,
                value: input ? input.value : 'НЕ НАЙДЕНО',
                placeholder: input ? input.placeholder : '',
                readyState: document.readyState,
                scriptsLoaded: document.scripts.length
            };
        }""")
        
        print(f"\n📧 Результат:")
        print(f"   Input существует: {result['exists']}")
        print(f"   Input видимый: {result['visible']}")
        print(f"   Email: {result['value']}")
        print(f"   Placeholder: {result['placeholder']}")
        print(f"   Page ready: {result['readyState']}")
        print(f"   Scripts: {result['scriptsLoaded']}")
        
        if result['value'] and result['value'] != 'НЕ НАЙДЕНО' and '@' in result['value']:
            print("\n✅ EMAIL ВИДЕН!")
        else:
            print("\n❌ EMAIL НЕ ВИДЕН")
        
        print("\n💤 Браузер остается открытым 20 сек для проверки...")
        await asyncio.sleep(20)
        await browser.close()
    
    print("\n" + "=" * 70)
    print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(simple_test())
