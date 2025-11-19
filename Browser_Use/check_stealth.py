import asyncio
import os
from pathlib import Path
from autonomous_registration_loop import AutonomousRegistration
from fingerprint_generator import FingerprintGenerator

async def check_stealth():
    print("🕵️‍♂️ Запуск проверки анонимности браузера...")
    
    # Создаем папку для результатов
    results_dir = Path("Browser_Use/stealth_check_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Инициализируем основной класс
    loop = AutonomousRegistration()
    
    # Генерируем fingerprint
    fingerprint_gen = FingerprintGenerator()
    fingerprint = fingerprint_gen.generate_complete_fingerprint()
    
    # Создаем профиль
    profile_data = loop.profile_manager.create_profile()
    profile_path = Path(profile_data["profile_path"])
    
    try:
        # Запускаем браузер с теми же настройками, что и бот
        await loop.init_browser(fingerprint, profile_path)
        page = await loop.context.new_page()
        
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
            
        # 3. CreepJS (самый жесткий тест)
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
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        if loop.context:
            await loop.context.close()
        if loop.browser:
            await loop.browser.close()
        if loop.playwright:
            await loop.playwright.stop()

if __name__ == "__main__":
    asyncio.run(check_stealth())
