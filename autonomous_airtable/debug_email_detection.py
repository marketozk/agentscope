"""
🔍 Диагностика: Почему не находит письмо на temp-mail.org

Этот скрипт анализирует структуру страницы и показывает:
1. Какие селекторы находят элементы
2. Какой HTML структура у писем
3. Что возвращает check_inbox
"""
import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from browser_framework.browser_agent import BrowserAgent
from email_providers import TempMailProvider


async def debug_temp_mail():
    """Диагностика temp-mail.org"""
    
    print("\n" + "="*70)
    print("🔍 ДИАГНОСТИКА TEMP-MAIL.ORG")
    print("="*70)
    
    agent = BrowserAgent()
    profile_path = Path(__file__).parent / "debug_profile"
    profile_path.mkdir(exist_ok=True)
    
    await agent.init(profile_path, headless=False)
    
    page = await agent.context.new_page()
    provider = TempMailProvider()
    
    try:
        # 1. Открываем temp-mail.org
        print("\n📧 Открытие temp-mail.org...")
        await page.goto("https://temp-mail.org/en/", wait_until="domcontentloaded")
        await asyncio.sleep(5)
        
        # 2. Получаем email
        print("\n📧 Получение email адреса...")
        email = await provider.get_email(page)
        print(f"   Email: {email}")
        
        # 3. Ждем, чтобы пользователь мог отправить письмо
        print("\n" + "="*70)
        print("⏳ ОЖИДАНИЕ 30 СЕКУНД")
        print("   Сейчас на экране должен быть temp-mail.org")
        print("   Если есть письмо - оно должно отображаться")
        print("="*70)
        await asyncio.sleep(30)
        
        # 4. Анализируем страницу
        print("\n" + "="*70)
        print("🔍 АНАЛИЗ СТРУКТУРЫ СТРАНИЦЫ")
        print("="*70)
        
        # Текущий URL
        print(f"\n📍 URL: {page.url}")
        
        # Скриншот
        screenshot_path = Path(__file__).parent / "debug_screenshots" / "temp_mail_analysis.png"
        screenshot_path.parent.mkdir(exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        print(f"📸 Скриншот: {screenshot_path}")
        
        # Сохраняем HTML
        html_path = Path(__file__).parent / "debug_screenshots" / "temp_mail_page.html"
        html_content = await page.content()
        html_path.write_text(html_content, encoding="utf-8")
        print(f"📄 HTML: {html_path}")
        
        # 5. Проверяем селекторы для писем
        print("\n" + "-"*50)
        print("📬 ПРОВЕРКА СЕЛЕКТОРОВ ДЛЯ ПИСЕМ:")
        print("-"*50)
        
        selectors_to_test = [
            # Текущие селекторы в коде
            '.inbox-area.onemail',
            '.inbox-area[data-id]',
            'div.inbox-area',
            # Альтернативные селекторы
            '.inbox-dataList',
            '.mail',
            '.mail-item',
            'div[class*="inbox"]',
            'div[class*="mail"]',
            'tr[class*="mail"]',
            'li[class*="mail"]',
            # Общие
            '[data-id]',
            'table tbody tr',
            '.list-group-item',
        ]
        
        for selector in selectors_to_test:
            try:
                elements = await page.query_selector_all(selector)
                count = len(elements)
                if count > 0:
                    print(f"   ✅ '{selector}' → {count} элементов")
                    # Показываем содержимое первого элемента
                    if count <= 3:
                        for i, elem in enumerate(elements):
                            try:
                                text = await elem.inner_text()
                                text_preview = text[:100].replace('\n', ' ').strip()
                                print(f"      [{i}]: {text_preview}...")
                            except:
                                pass
                else:
                    print(f"   ❌ '{selector}' → 0 элементов")
            except Exception as e:
                print(f"   ⚠️ '{selector}' → Ошибка: {e}")
        
        # 6. Вызываем check_inbox провайдера
        print("\n" + "-"*50)
        print("📬 РЕЗУЛЬТАТ check_inbox():")
        print("-"*50)
        
        emails = await provider.check_inbox(page)
        print(f"   Найдено писем: {len(emails)}")
        
        for i, email_data in enumerate(emails):
            print(f"\n   📧 Письмо #{i+1}:")
            print(f"      From: {email_data.get('from', 'N/A')}")
            print(f"      Subject: {email_data.get('subject', 'N/A')}")
            print(f"      Text: {email_data.get('text', 'N/A')[:100]}...")
        
        # 7. Ищем любые элементы с "airtable" в тексте
        print("\n" + "-"*50)
        print("🔍 ПОИСК 'airtable' НА СТРАНИЦЕ:")
        print("-"*50)
        
        # Через JavaScript
        airtable_elements = await page.evaluate("""
            () => {
                const results = [];
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    const text = el.textContent || '';
                    if (text.toLowerCase().includes('airtable') && el.children.length === 0) {
                        results.push({
                            tag: el.tagName,
                            class: el.className,
                            text: text.substring(0, 200)
                        });
                    }
                }
                return results.slice(0, 10);
            }
        """)
        
        if airtable_elements:
            print(f"   ✅ Найдено {len(airtable_elements)} элементов с 'airtable':")
            for elem in airtable_elements:
                print(f"      <{elem['tag']} class='{elem['class']}'> {elem['text'][:50]}...")
        else:
            print("   ❌ Элементы с 'airtable' не найдены")
        
        # 8. Анализ всех видимых блоков на странице
        print("\n" + "-"*50)
        print("📋 СТРУКТУРА INBOX ОБЛАСТИ:")
        print("-"*50)
        
        inbox_html = await page.evaluate("""
            () => {
                // Ищем основной контейнер с письмами
                const containers = document.querySelectorAll('#mails, .inbox, [class*="inbox"], [class*="mail-list"]');
                const results = [];
                for (const container of containers) {
                    results.push({
                        tag: container.tagName,
                        id: container.id,
                        class: container.className,
                        childCount: container.children.length,
                        innerHTML: container.innerHTML.substring(0, 500)
                    });
                }
                return results;
            }
        """)
        
        for container in inbox_html:
            print(f"\n   📦 <{container['tag']} id='{container['id']}' class='{container['class']}'>")
            print(f"      Children: {container['childCount']}")
            print(f"      HTML preview: {container['innerHTML'][:200]}...")
        
        print("\n" + "="*70)
        print("✅ ДИАГНОСТИКА ЗАВЕРШЕНА")
        print("   Проверьте скриншот и HTML файл для детального анализа")
        print("="*70)
        
        # Ждем еще немного чтобы посмотреть результат
        print("\n⏳ Браузер закроется через 60 секунд...")
        await asyncio.sleep(60)
        
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(debug_temp_mail())
