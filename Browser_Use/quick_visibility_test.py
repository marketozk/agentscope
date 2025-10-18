"""
🎯 ФИНАЛЬНЫЙ ТЕСТ: Проверяем видимость email с нашей конфигурацией

Быстрый тест - только проверка видимости, без долгих ожиданий
"""

import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def quick_visibility_test():
    print("=" * 70)
    print("🎯 БЫСТРЫЙ ТЕСТ ВИДИМОСТИ EMAIL")
    print("=" * 70)
    
    stealth = Stealth()
    
    # ТЕСТ: С нашей полной конфигурацией (stealth + headers)
    print("\n🔧 Конфигурация: stealth + headers + user-agent (как в test_agent3_air.py)")
    print("-" * 70)
    
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
        
        # Применяем stealth
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
        print("📋 Headers установлены")
        
        page = await context.new_page()
        
        print("\n🌐 Открываем temp-mail.org...")
        try:
            await page.goto("https://temp-mail.org/en/", wait_until="domcontentloaded", timeout=30000)
            print("✅ Страница загружена")
        except Exception as e:
            print(f"⚠️  Ошибка загрузки: {str(e)[:100]}")
        
        # Ждём генерацию email с проверками
        print("\n⏳ Проверяем появление email...")
        for attempt in range(20):  # 20 попыток × 1 сек = 20 сек макс
            email = await page.evaluate("""
                document.querySelector('#mail')?.value || null
            """)
            
            if email and '@' in email:
                print(f"\n✅ EMAIL НАЙДЕН НА ПОПЫТКЕ {attempt + 1}: {email}")
                break
            
            if attempt % 5 == 0 and attempt > 0:
                print(f"   ... попытка {attempt}/20")
            
            await asyncio.sleep(1)
        else:
            print("\n❌ EMAIL НЕ ПОЯВИЛСЯ ЗА 20 СЕКУНД")
            
            # Дополнительная диагностика
            debug_info = await page.evaluate("""() => {
                const input = document.querySelector('#mail');
                return {
                    input_exists: !!input,
                    input_value: input ? input.value : null,
                    placeholder: input ? input.placeholder : null,
                    html_length: document.body.innerHTML.length,
                    readyState: document.readyState
                };
            }""")
            
            print(f"\n🔍 Диагностика:")
            print(f"   Input существует: {debug_info['input_exists']}")
            print(f"   Input value: {debug_info['input_value']}")
            print(f"   Placeholder: {debug_info['placeholder']}")
            print(f"   HTML size: {debug_info['html_length']}")
            print(f"   Ready state: {debug_info['readyState']}")
        
        print("\n💤 Держим браузер открытым 10 сек для визуальной проверки...")
        print("   👁️  Проверьте визуально - видна ли почта в браузере?")
        await asyncio.sleep(10)
        
        await browser.close()
    
    print("\n" + "=" * 70)
    print("✅ ТЕСТ ЗАВЕРШЁН")
    print("=" * 70)

if __name__ == "__main__":
    try:
        asyncio.run(quick_visibility_test())
    except KeyboardInterrupt:
        print("\n\n⚠️  Тест прерван пользователем")
