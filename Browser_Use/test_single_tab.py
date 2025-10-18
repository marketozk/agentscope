"""
🧪 Тест количества вкладок при запуске

Проверяет, что при создании браузера открывается ТОЛЬКО ОДНА вкладка.
"""

import asyncio
from playwright.async_api import async_playwright

try:
    from playwright_stealth import Stealth
    stealth_instance = Stealth()
    stealth_async = stealth_instance.apply_stealth_async
    STEALTH_AVAILABLE = True
except ImportError:
    stealth_async = None
    STEALTH_AVAILABLE = False


async def main():
    print("=" * 70)
    print("🧪 ТЕСТ КОЛИЧЕСТВА ВКЛАДОК")
    print("=" * 70)
    
    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 900
    
    async with async_playwright() as p:
        print("\n📦 Запуск браузера...")
        
        browser = await p.chromium.launch(
            headless=False, 
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': SCREEN_WIDTH, 'height': SCREEN_HEIGHT},
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            },
            java_script_enabled=True,
        )
        
        if stealth_async and STEALTH_AVAILABLE:
            print("🕵️  Применяем playwright-stealth...")
            await stealth_async(context)
        
        # 🎯 ПРОВЕРКА: Сколько вкладок создано автоматически?
        pages_before = context.pages
        print(f"\n📊 Вкладок после создания контекста: {len(pages_before)}")
        
        # 🎯 ИСПОЛЬЗУЕМ существующую вкладку
        if pages_before:
            page = pages_before[0]
            print(f"✅ Используем существующую вкладку")
        else:
            page = await context.new_page()
            print(f"📄 Создали новую вкладку (не было автоматических)")
        
        pages_after = context.pages
        print(f"📊 Вкладок после получения page: {len(pages_after)}")
        
        # Открываем temp-mail
        print("\n🌐 Открываем temp-mail.org...")
        await page.goto("https://temp-mail.org/en/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        
        pages_final = context.pages
        print(f"📊 Вкладок после загрузки сайта: {len(pages_final)}")
        
        # Финальная проверка
        print("\n" + "=" * 70)
        if len(pages_final) == 1:
            print("✅ ТЕСТ ПРОЙДЕН: Открыта ТОЛЬКО ОДНА вкладка")
        else:
            print(f"❌ ТЕСТ НЕ ПРОЙДЕН: Открыто {len(pages_final)} вкладок")
            print("\n📋 Список вкладок:")
            for i, p in enumerate(pages_final, 1):
                url = p.url
                print(f"   {i}. {url}")
        print("=" * 70)
        
        print("\n💤 Браузер остается открытым 10 сек для визуальной проверки...")
        await asyncio.sleep(10)
        
        await browser.close()
        print("\n✅ Тест завершен")


if __name__ == "__main__":
    asyncio.run(main())
