import asyncio
from camoufox.async_api import AsyncCamoufox
from pathlib import Path

async def check_stealth_camoufox():
    print("🦊 Запуск проверки анонимности через Camoufox...")
    
    # Создаем папку для результатов
    results_dir = Path("Browser_Use/stealth_check_results_camoufox")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Запускаем Camoufox
    # Он автоматически генерирует уникальный fingerprint при каждом запуске
    async with AsyncCamoufox(headless=False) as browser:
        page = await browser.new_page()
        
        # 1. Pixelscan
        print("\n1️⃣ Проверка на pixelscan.net...")
        try:
            await page.goto("https://pixelscan.net/", wait_until="networkidle")
            print("   👀 Браузер открыт. Посмотрите результат.")
            input("   ⌨️  Нажмите ENTER в этом терминале, чтобы сделать скриншот и продолжить...")
            await page.screenshot(path=str(results_dir / "1_pixelscan.png"), full_page=True)
            print("   📸 Скриншот сохранен: 1_pixelscan.png")
        except Exception as e:
            print(f"   ❌ Ошибка pixelscan: {e}")

        # 2. Iphey
        print("\n2️⃣ Проверка на iphey.com...")
        try:
            await page.goto("https://iphey.com/", wait_until="networkidle")
            print("   👀 Браузер открыт. Посмотрите результат.")
            input("   ⌨️  Нажмите ENTER в этом терминале, чтобы сделать скриншот и продолжить...")
            await page.screenshot(path=str(results_dir / "2_iphey.png"), full_page=True)
            print("   📸 Скриншот сохранен: 2_iphey.png")
        except Exception as e:
            print(f"   ❌ Ошибка iphey: {e}")
            
        # 3. CreepJS
        print("\n3️⃣ Проверка на CreepJS...")
        try:
            await page.goto("https://abrahamjuliot.github.io/creepjs/", wait_until="networkidle")
            print("   👀 Браузер открыт. Посмотрите результат.")
            input("   ⌨️  Нажмите ENTER в этом терминале, чтобы сделать скриншот и завершить...")
            await page.screenshot(path=str(results_dir / "3_creepjs.png"), full_page=True)
            print("   📸 Скриншот сохранен: 3_creepjs.png")
        except Exception as e:
            print(f"   ❌ Ошибка CreepJS: {e}")

        print(f"\n✅ Проверка завершена! Результаты в папке: {results_dir.absolute()}")

if __name__ == "__main__":
    asyncio.run(check_stealth_camoufox())
