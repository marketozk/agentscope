"""
🧪 Тест полной конфигурации браузера для temp-mail.org

Проверяет, что с новой конфигурацией (stealth + headers + user-agent + JS) 
email корректно отображается на странице.

Это ТОЧНАЯ копия конфигурации из test_agent3_air.py после исправлений.
"""

import asyncio
import re
from playwright.async_api import async_playwright

try:
    from playwright_stealth import Stealth
    stealth_instance = Stealth()
    stealth_async = stealth_instance.apply_stealth_async
    STEALTH_AVAILABLE = True
except ImportError:
    stealth_async = None
    STEALTH_AVAILABLE = False


async def extract_email_with_retries(page, max_attempts=20):
    """
    Извлекает email с активным ожиданием.
    
    Args:
        page: Playwright page
        max_attempts: Максимум попыток (20 × 0.5s = 10 сек)
    
    Returns:
        Email или None
    """
    print(f"⏳ Ожидание появления email (до {max_attempts * 0.5} сек)...")
    
    for attempt in range(1, max_attempts + 1):
        email = await page.evaluate('''() => {
            // Способ 1: прямой поиск в #mail
            let input = document.querySelector('#mail');
            if (input && input.value && input.value.includes('@')) {
                return input.value;
            }
            
            // Способ 2: поиск всех input элементов
            let inputs = document.querySelectorAll('input');
            for (let inp of inputs) {
                if (inp.value && inp.value.includes('@') && inp.value.includes('.')) {
                    // Пропускаем placeholder'ы
                    if (!inp.placeholder || !inp.placeholder.includes('@')) {
                        return inp.value;
                    }
                }
            }
            
            // Способ 3: поиск в текстовых полях по классам
            let elements = document.querySelectorAll('[class*="mail"], [class*="email"], [id*="mail"], [id*="email"]');
            for (let el of elements) {
                if (el.value && el.value.includes('@')) {
                    return el.value;
                }
                if (el.innerText && el.innerText.includes('@')) {
                    return el.innerText;
                }
            }
            
            return null;
        }''')
        
        if email and email.strip() and '@' in email and '.' in email:
            print(f"✅ EMAIL НАЙДЕН НА ПОПЫТКЕ {attempt}: {email}")
            return email
        
        # Логируем каждую 4-ю попытку
        if attempt % 4 == 0:
            print(f"   ... попытка {attempt}/{max_attempts} (текущее значение: '{email}')")
        
        await asyncio.sleep(0.5)
    
    print(f"❌ Email не найден за {max_attempts * 0.5} сек")
    return None


async def main():
    print("=" * 70)
    print("🧪 ТЕСТ ПОЛНОЙ КОНФИГУРАЦИИ БРАУЗЕРА")
    print("=" * 70)
    
    if not STEALTH_AVAILABLE:
        print("⚠️  playwright-stealth не установлен! Stealth будет пропущен.")
    
    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 900
    
    async with async_playwright() as p:
        print("\n📦 Запуск браузера с полной конфигурацией...")
        
        # Точная копия конфигурации из test_agent3_air.py
        browser = await p.chromium.launch(
            headless=False, 
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        # 🔧 Полная конфигурация контекста
        context = await browser.new_context(
            viewport={'width': SCREEN_WIDTH, 'height': SCREEN_HEIGHT},
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            },
            java_script_enabled=True,  # Явно включаем JS
        )
        
        # 🛡️ Применяем stealth
        if stealth_async and STEALTH_AVAILABLE:
            print("🕵️  Применяем playwright-stealth...")
            await stealth_async(context)
        
        page = await context.new_page()
        
        print("🌐 Открываем temp-mail.org...")
        await page.goto("https://temp-mail.org/en/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)  # Даем странице стабилизироваться
        print("✅ Страница загружена")
        
        # Проверка JS
        js_enabled = await page.evaluate("() => typeof document !== 'undefined'")
        print(f"📋 JavaScript включен: {js_enabled}")
        
        # Проверка user-agent
        user_agent = await page.evaluate("() => navigator.userAgent")
        print(f"🔍 User-Agent: {user_agent[:80]}...")
        
        # Проверка webdriver
        webdriver_hidden = await page.evaluate("() => navigator.webdriver")
        print(f"🛡️  navigator.webdriver: {webdriver_hidden} (должно быть False/undefined)")
        
        # Извлекаем email
        email = await extract_email_with_retries(page, max_attempts=20)
        
        if email:
            print("\n" + "=" * 70)
            print("✅ ТЕСТ ПРОЙДЕН")
            print("=" * 70)
            print(f"📧 Извлеченный email: {email}")
            print("\nВсе параметры конфигурации работают корректно!")
        else:
            print("\n" + "=" * 70)
            print("❌ ТЕСТ НЕ ПРОЙДЕН")
            print("=" * 70)
            print("Email не был найден на странице.")
            
            # Дополнительная диагностика
            print("\n🔍 Диагностика:")
            
            # Проверка HTML
            html = await page.content()
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            matches = re.findall(email_pattern, html)
            
            if matches:
                print(f"   В HTML найдены email'ы через regex: {matches}")
            else:
                print("   В HTML нет email'ов (даже через regex)")
            
            # Проверка input элементов
            inputs_count = await page.evaluate("() => document.querySelectorAll('input').length")
            print(f"   Количество input элементов: {inputs_count}")
            
            # Проверка #mail
            mail_input = await page.query_selector('#mail')
            if mail_input:
                value = await mail_input.input_value()
                print(f"   Значение #mail input: '{value}'")
            else:
                print("   Элемент #mail не найден!")
        
        print("\n💤 Браузер остается открытым 10 сек для визуальной проверки...")
        await asyncio.sleep(10)
        
        await browser.close()
        print("\n✅ Тест завершен")


if __name__ == "__main__":
    asyncio.run(main())
