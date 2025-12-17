"""
🔍 ДИАГНОСТИКА: Почему не находит письмо на temp-mail.org

Запускает браузер, открывает temp-mail.org и выводит:
1. Какие элементы inbox видит
2. Всю структуру HTML в области писем
3. Что находит по текущим селекторам
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from browser_framework.browser_agent import BrowserAgent
from email_providers import TempMailProvider


async def diagnose():
    print("=" * 70)
    print("🔍 ДИАГНОСТИКА TEMP-MAIL.ORG")
    print("=" * 70)
    
    agent = BrowserAgent()
    profile_path = Path(__file__).parent / "temp_diagnose_profile"
    profile_path.mkdir(exist_ok=True)
    
    try:
        print("\n1️⃣ Запуск браузера...")
        await agent.init(profile_path, headless=False)
        context = agent.context
        
        print("\n2️⃣ Открытие temp-mail.org...")
        page = await context.new_page()
        await page.goto("https://temp-mail.org/en/", wait_until="domcontentloaded")
        await asyncio.sleep(5)
        
        print(f"\n   📍 URL: {page.url}")
        
        # Получаем email
        provider = TempMailProvider()
        print("\n3️⃣ Получение email через провайдер...")
        email = await provider.get_email(page)
        print(f"   📧 Email: {email}")
        
        print("\n" + "=" * 70)
        print("⏳ ОЖИДАНИЕ: Отправьте тестовое письмо на этот адрес")
        print("   Нажмите Enter когда письмо придёт (или подождите 30 сек)...")
        print("=" * 70)
        
        # Ждём письмо или Enter
        await asyncio.sleep(30)
        
        print("\n4️⃣ ДИАГНОСТИКА INBOX...")
        
        # Перезагружаем страницу
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # Сохраняем скриншот
        screenshot_path = Path("debug_screenshots") / f"diagnose_{datetime.now().strftime('%H%M%S')}.png"
        screenshot_path.parent.mkdir(exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        print(f"   📸 Скриншот: {screenshot_path}")
        
        # Сохраняем HTML
        html_path = Path("debug_screenshots") / f"diagnose_{datetime.now().strftime('%H%M%S')}.html"
        html_content = await page.content()
        html_path.write_text(html_content, encoding="utf-8")
        print(f"   📄 HTML: {html_path}")
        
        print("\n5️⃣ АНАЛИЗ СЕЛЕКТОРОВ...")
        
        # Проверяем текущие селекторы
        selectors_to_check = [
            # Текущие селекторы в коде
            '.inbox-area.onemail',
            '.inbox-area[data-id]',
            'div.inbox-area',
            # Возможные альтернативные селекторы
            '.inbox-dataList',
            '.mail',
            '[class*="inbox"]',
            '[class*="mail"]',
            '[class*="message"]',
            'table.inbox',
            '#mails',
            '#inbox',
            '.emails',
            'li[class*="mail"]',
            'div[class*="mail"]',
            'tr[class*="mail"]',
        ]
        
        print("\n   🔍 Проверка селекторов:")
        for selector in selectors_to_check:
            try:
                elements = await page.query_selector_all(selector)
                count = len(elements)
                if count > 0:
                    print(f"   ✅ {selector}: {count} элементов")
                    # Выводим первый элемент
                    if elements:
                        try:
                            text = await elements[0].inner_text()
                            text_preview = text[:100].replace('\n', ' ') if text else "(пусто)"
                            print(f"      └─ Текст: {text_preview}...")
                        except:
                            pass
                else:
                    print(f"   ❌ {selector}: не найдено")
            except Exception as e:
                print(f"   ⚠️  {selector}: ошибка - {e}")
        
        print("\n6️⃣ ПОИСК ВСЕХ ЭЛЕМЕНТОВ С 'MAIL' В КЛАССЕ...")
        
        all_mail_elements = await page.evaluate("""
            () => {
                const results = [];
                const elements = document.querySelectorAll('*');
                for (const el of elements) {
                    const className = el.className;
                    const id = el.id;
                    if ((className && className.toString().toLowerCase().includes('mail')) ||
                        (id && id.toLowerCase().includes('mail')) ||
                        (className && className.toString().toLowerCase().includes('inbox'))) {
                        
                        const text = el.innerText || '';
                        const textPreview = text.substring(0, 100).replace(/\\n/g, ' ');
                        
                        results.push({
                            tag: el.tagName,
                            id: id,
                            class: className.toString().substring(0, 100),
                            text: textPreview,
                            childCount: el.children.length
                        });
                    }
                }
                return results.slice(0, 30); // Лимит 30 элементов
            }
        """)
        
        print(f"\n   Найдено элементов с 'mail/inbox' в классе/id: {len(all_mail_elements)}")
        for i, elem in enumerate(all_mail_elements):
            print(f"\n   [{i+1}] <{elem['tag']}> id='{elem['id']}' class='{elem['class'][:50]}'")
            print(f"       children={elem['childCount']}, text='{elem['text'][:60]}...'")
        
        print("\n7️⃣ ПРОВЕРКА check_inbox() ПРОВАЙДЕРА...")
        
        emails = await provider.check_inbox(page)
        print(f"\n   📬 Найдено писем через check_inbox(): {len(emails)}")
        for i, email_data in enumerate(emails):
            print(f"\n   [{i+1}] From: {email_data.get('from', 'N/A')}")
            print(f"       Subject: {email_data.get('subject', 'N/A')}")
            print(f"       ID: {email_data.get('id', 'N/A')}")
        
        print("\n8️⃣ ПОИСК ЛЮБЫХ ССЫЛОК НА AIRTABLE...")
        
        airtable_links = await page.query_selector_all('a[href*="airtable"]')
        print(f"\n   🔗 Ссылок на airtable.com: {len(airtable_links)}")
        for link in airtable_links:
            href = await link.get_attribute('href')
            print(f"      - {href[:80]}...")
        
        print("\n" + "=" * 70)
        print("📊 ДИАГНОСТИКА ЗАВЕРШЕНА")
        print("=" * 70)
        print("\nПроверьте файлы:")
        print(f"  - Скриншот: {screenshot_path}")
        print(f"  - HTML: {html_path}")
        print("\nНажмите Enter для закрытия браузера...")
        
        input()
        
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(diagnose())
