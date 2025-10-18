#!/usr/bin/env python3
"""
🧪 Тестирование обхода блокировки Temp-Mail

Этот скрипт проверяет различные стратегии для успешной навигации на temp-mail.org:
1. wait_until strategies
2. Headers маскировки
3. Задержки
4. Обработка Cloudflare
5. Persistent cookies
"""

import asyncio
import json
from playwright.async_api import async_playwright
from pathlib import Path
from datetime import datetime

# Стратегии навигации с разными wait_until значениями
STRATEGIES = [
    {
        "name": "domcontentloaded (рекомендуется)",
        "wait_until": "domcontentloaded",
        "timeout": 20000,
        "post_delay": 1500,
        "description": "Ждёт загрузки DOM элементов, оптимально для большинства сайтов"
    },
    {
        "name": "load",
        "wait_until": "load",
        "timeout": 15000,
        "post_delay": 1000,
        "description": "Ждёт загрузки основного контента"
    },
    {
        "name": "networkidle (старая)",
        "wait_until": "networkidle",
        "timeout": 30000,
        "post_delay": 500,
        "description": "Ждёт когда сетевые запросы затихнут (может зависнуть)"
    },
    {
        "name": "minimal (без ожидания)",
        "wait_until": None,
        "timeout": 3000,
        "post_delay": 3000,
        "description": "Запускает навигацию и ждёт N сек вместо ожидания события"
    }
]

async def test_strategy(strategy, test_url="https://temp-mail.org/en/"):
    """Тестирует одну стратегию навигации"""
    print(f"\n{'='*70}")
    print(f"🧪 СТРАТЕГИЯ: {strategy['name']}")
    print(f"{'='*70}")
    print(f"📝 {strategy['description']}")
    print(f"⚙️  Параметры: wait_until={strategy['wait_until']}, timeout={strategy['timeout']}ms, delay={strategy['post_delay']}ms")
    
    result = {
        "strategy": strategy['name'],
        "url": test_url,
        "success": False,
        "duration": 0,
        "final_url": None,
        "page_title": None,
        "html_length": 0,
        "cloudflare_detected": False,
        "error": None,
        "timestamp": datetime.now().isoformat()
    }
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Используем persistent context с сохранённым профилем
        user_data_dir = str(Path(__file__).parent / "profiles" / "test_tempmail")
        context = await browser.new_context(
            viewport={'width': 1440, 'height': 900},
            locale='ru-RU'
        )
        
        # Добавляем Human-like headers
        await context.set_extra_http_headers({
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        page = await context.new_page()
        
        # Задержка перед навигацией
        await page.wait_for_timeout(1000)
        
        print(f"\n⏳ Начинаем навигацию...")
        
        # Применяем стратегию
        if strategy['wait_until'] is None:
            # Стратегия без ожидания: запустить и просто ждать N сек
            print(f"   🚀 goto(wait_until=None) + sleep({strategy['post_delay']}ms)")
            nav_task = page.goto(test_url)
            await asyncio.sleep(strategy['post_delay'] / 1000)
            try:
                await asyncio.wait_for(nav_task, timeout=strategy['timeout'] / 1000)
            except asyncio.TimeoutError:
                print(f"   ⏱️  goto timeout, но ждём всё равно...")
        else:
            # Стандартная стратегия
            print(f"   🚀 goto(wait_until={strategy['wait_until']}, timeout={strategy['timeout']}ms)")
            await page.goto(test_url, wait_until=strategy['wait_until'], timeout=strategy['timeout'])
        
        # Пост-задержка для стабилизации
        if strategy['post_delay'] > 0:
            await page.wait_for_timeout(strategy['post_delay'])
        
        # Сбор информации
        final_url = page.url
        title = await page.title()
        html_content = await page.content()
        
        result['final_url'] = final_url
        result['page_title'] = title
        result['html_length'] = len(html_content)
        
        # Проверка на Cloudflare
        if "Attention Required" in title or "Cloudflare" in title or "Sorry, you have been blocked" in html_content:
            result['cloudflare_detected'] = True
            print(f"   🛡️  ⚠️ CLOUDFLARE DETECTED!")
        else:
            print(f"   ✅ NO CLOUDFLARE DETECTED")
        
        # Проверка что получили реальный контент
        if "temp-mail" in html_content.lower() and result['html_length'] > 500:
            result['success'] = True
            print(f"   ✅ УСПЕШНО ЗАГРУЖЕНО (HTML: {result['html_length']} байт)")
            print(f"   📍 URL: {final_url}")
            print(f"   📄 Title: {title}")
        else:
            print(f"   ⚠️  ЗАГРУЖЕНО, но контент сомнительный (HTML: {result['html_length']} байт)")
            print(f"   📍 URL: {final_url}")
            print(f"   📄 Title: {title[:50]}...")
        
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        result['error'] = str(e)
        print(f"   ❌ ОШИБКА: {e}")
    
    finally:
        result['duration'] = asyncio.get_event_loop().time() - start_time
        print(f"\n⏱️  Время выполнения: {result['duration']:.2f} сек")
    
    return result


async def main():
    """Основная функция тестирования"""
    print("\n" + "="*70)
    print("🧪 ТЕСТИРОВАНИЕ ОБХОДА БЛОКИРОВКИ TEMP-MAIL.ORG")
    print("="*70)
    print("\nЭтот скрипт проверит различные стратегии навигации и выберет лучшую.")
    print("\n⚠️  Примечание: Результаты могут зависеть от вашего IP и времени суток!")
    
    results = []
    
    # Тестируем все стратегии
    for strategy in STRATEGIES:
        result = await test_strategy(strategy)
        results.append(result)
        await asyncio.sleep(2)  # Пауза между попытками
    
    # Анализ результатов
    print("\n" + "="*70)
    print("📊 ИТОГИ")
    print("="*70)
    
    successful = [r for r in results if r['success']]
    if successful:
        print(f"\n✅ УСПЕШНЫЕ СТРАТЕГИИ: {len(successful)}/{len(results)}")
        for r in successful:
            print(f"   • {r['strategy']}: {r['duration']:.2f}s, HTML={r['html_length']} байт")
        
        best = min(successful, key=lambda x: x['duration'])
        print(f"\n🏆 РЕКОМЕНДУЕТСЯ: {best['strategy']} ({best['duration']:.2f}s)")
    else:
        print(f"\n❌ НЕ УДАЛОСЬ ЗАГРУЗИТЬ С КАКОЙ-ЛИБО СТРАТЕГИЕЙ")
        print("\nВозможные причины:")
        print("  1. IP заблокирован temp-mail.org")
        print("  2. VPN/Proxy требуется")
        print("  3. Temporal блокировка (рассеяется через 5-10 минут)")
        print("  4. Требуется более сложный обход")
    
    # Сохраняем результаты
    results_file = Path(__file__).parent / f"tempmail_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n📁 Результаты сохранены: {results_file}")
    
    # Итоговые рекомендации
    print("\n" + "="*70)
    print("💡 РЕКОМЕНДАЦИИ")
    print("="*70)
    print("""
1. ЛУЧШАЯ СТРАТЕГИЯ:
   • Используй: wait_until="domcontentloaded"
   • Это даёт хороший баланс между скоростью и надёжностью
   
2. ЕСЛИ НЕ РАБОТАЕТ DOMCONTENTLOADED:
   • Попробуй: wait_until="load"
   • Это более мягкое ожидание
   
3. ДЛЯ СЛОЖНЫХ СЛУЧАЕВ:
   • Используй стратегию "minimal" (без ожидания)
   • + добавь задержку 3-5 сек
   
4. ЕСЛИ ВСЕГО НЕ РАБОТАЕТ:
   • Проверь IP (возможно заблокирован)
   • Используй VPN или попробуй позже
   • Рассмотри альтернативные сервисы почты
    """)


if __name__ == "__main__":
    asyncio.run(main())
