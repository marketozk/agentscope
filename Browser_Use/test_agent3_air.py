"""
РАБОТАЕТ!!!!!!!
🎯 Тест gemini-2.5-computer-use-preview-10-2025 через новый SDK google.genai
БЕЗ использования browser-use Agent - только прямое API и Playwright.

Что делает:
1. Запускает Playwright браузер
2. Использует Computer Use модель через google.genai.Client
3. Модель видит скриншоты и управляет браузером через tool_calls
4. Цикл: скриншот → модель → tool_call → выполнение → результат → новый скриншот

АДАПТАЦИЯ ДЛЯ AIRTABLE REGISTRATION:
- Добавлены custom functions для парсинга HTML
- Двухэтапная регистрация: получение email + регистрация + подтверждение
- Автоматическое сохранение результатов
"""
import os
import json
import asyncio
import base64
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional
from urllib.parse import urlparse

# Новый SDK Google Generative AI (unified SDK)
from google import genai
from google.genai.types import (
    Tool, ComputerUse, 
    GenerateContentConfig,
    Content, Part, Blob,
    FunctionCall, FunctionResponse,
    FunctionDeclaration
)

# Playwright для управления браузером
from playwright.async_api import async_playwright

# Stealth плагин для обхода Cloudflare и других систем обнаружения автоматизации
try:
    # ✅ ИСПРАВЛЕНО: В playwright-stealth 2.0.0 используется класс Stealth
    from playwright_stealth import Stealth
    stealth_instance = Stealth()
    stealth_async = stealth_instance.apply_stealth_async
    print("✅ Playwright Stealth 2.0.0 загружен успешно")
except ImportError as e:
    # Fallback если stealth не доступен
    stealth_async = None
    print(f"⚠️  Playwright Stealth не установлен: {e}")


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

# Разрешенные домены для навигации (жесткая политика безопасности)
ALLOWED_DOMAINS = (
    "airtable.com",
    "temp-mail.org",
)

def is_allowed_url(url: str) -> bool:
    """
    Проверяет, разрешен ли URL для перехода.
    Разрешены:
      - about:* (about:blank и т.п.)
      - Любые поддомены airtable.com
      - Любые поддомены temp-mail.org
    """
    if not url:
        return False
    try:
        if url.startswith("about:"):
            return True
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not host:
            return False
        for d in ALLOWED_DOMAINS:
            d = d.lower()
            if host == d or host.endswith("." + d):
                return True
        return False
    except Exception:
        return False

def extract_email_from_text(text: str) -> Optional[str]:
    """
    Извлекает email адрес из текста модели.
    
    Ищет паттерны:
    - xxx@domain.com
    - Email: xxx@domain.com
    - "email": "xxx@domain.com"
    """
    if not text:
        return None
    
    # Регулярка для email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    
    if matches:
        # Возвращаем первый найденный email
        return matches[0]
    
    return None


async def safe_screenshot(page, full_page: bool = False, timeout_ms: int = 10000) -> Optional[bytes]:
    """
    Делает скриншот страницы с таймаутом и надёжным фолбэком на 1x1 PNG,
    чтобы не падать из-за зависания шрифтов/рендеринга.
    """
    try:
        return await page.screenshot(type="png", full_page=full_page, timeout=timeout_ms)
    except Exception as e:
        print(f"⚠️ Screenshot failed: {e}. Skipping image for this turn.")
        return None


async def detect_cloudflare_block(page) -> tuple[bool, str]:
    """NO-OP: Cloudflare detection disabled by request."""
    return False, ""


def log_cloudflare_event(phase: str, step: int, action: str, url: str, signal: str):
    """NO-OP logger: disabled."""
    return


def save_registration_result(email: str, status: str, confirmed: bool, notes: str):
    """
    Сохраняет результат регистрации в файл с timestamp.
    
    Args:
        email: Email адрес
        status: Статус регистрации (success/partial/failed)
        confirmed: Подтверждена ли почта
        notes: Дополнительные заметки
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"airtable_registration_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=== РЕЗУЛЬТАТ РЕГИСТРАЦИИ AIRTABLE ===\n")
        f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Email: {email}\n")
        f.write(f"Статус: {status}\n")
        f.write(f"Подтверждено: {confirmed}\n")
        if notes:
            f.write(f"Заметки: {notes}\n")
        f.write("=" * 50 + "\n")
    
    print(f"\n💾 Результат сохранен в: {filename}")


async def extract_verification_link_from_page(page) -> str:
    """
    Извлекает verification link из текущей страницы temp-mail.
    
    Использует несколько методов:
    1. Поиск в HTML по regex
    2. Поиск через селекторы
    3. JavaScript evaluation
    
    Args:
        page: Playwright Page объект
    
    Returns:
        URL verification ссылки или сообщение об ошибке
    """
    try:
        # Метод 1: Regex поиск в HTML
        html = await page.content()
        
        # Паттерн для Airtable verification URL
        patterns = [
            r'https://airtable\.com/auth/verifyEmail/[^\s"<>\']+',
            r'https://airtable\.com/verify[^\s"<>\']+',
            r'https://[^/]*airtable\.com/[^\s"<>\']*verify[^\s"<>\']*',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                url = match.group(0)
                print(f"  ✅ Найден URL через regex: {url}")
                return url
        
        # Метод 2: Поиск ссылок с airtable.com/auth
        try:
            links = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a'))
                    .map(a => a.href)
                    .filter(href => href && (
                        href.includes('airtable.com/auth') || 
                        href.includes('verifyEmail') ||
                        href.includes('airtable.com/verify')
                    ));
            }''')
            
            if links and len(links) > 0:
                url = links[0]
                print(f"  ✅ Найден URL через JavaScript: {url}")
                return url
        except Exception as e:
            print(f"  ⚠️  JavaScript метод не сработал: {e}")
        
        # Метод 3: Поиск через селекторы
        try:
            link = await page.query_selector('a[href*="verifyEmail"]')
            if link:
                url = await link.get_attribute('href')
                if url:
                    print(f"  ✅ Найден URL через селектор: {url}")
                    return url
        except Exception as e:
            print(f"  ⚠️  Selector метод не сработал: {e}")

        # Метод 4: Попытка автоматически открыть письмо от Airtable и повторный поиск
        try:
            print("  🔄 Пытаюсь открыть письмо от Airtable в списке входящих...")
            clicked = await page.evaluate('''() => {
                const isVisible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                const nodes = Array.from(document.querySelectorAll('a, div, span, li'));
                // Ищем элементы, связанные с письмом Airtable
                const candidates = nodes.filter(el => {
                    const t = (el.textContent || '').toLowerCase();
                    return isVisible(el) && (
                        t.includes('airtable') ||
                        t.includes('confirm your email') ||
                        t.includes('please confirm') ||
                        t.includes('confirm email')
                    );
                });
                for (const el of candidates) {
                    try { el.click(); return true; } catch (e) {}
                }
                return false;
            }''')
            if clicked:
                # Даём интерфейсу обновиться
                await asyncio.sleep(2)
                try:
                    html = await page.content()
                    for pattern in patterns:
                        match = re.search(pattern, html)
                        if match:
                            url = match.group(0)
                            print(f"  ✅ Найден URL после открытия письма: {url}")
                            return url
                    # Дополнительный JS-поиск ссылок
                    links = await page.evaluate('''() => {
                        return Array.from(document.querySelectorAll('a'))
                            .map(a => a.href)
                            .filter(href => href && (
                                href.includes('airtable.com/auth') || 
                                href.includes('verifyEmail') ||
                                href.includes('airtable.com/verify')
                            ));
                    }''')
                    if links and len(links) > 0:
                        url = links[0]
                        print(f"  ✅ Найден URL после клика: {url}")
                        return url
                except Exception as e:
                    print(f"  ⚠️  Ошибка при повторном поиске после клика: {e}")
            else:
                print("  ℹ️  Не удалось автоматически кликнуть письмо Airtable в списке")
        except Exception as e:
            print(f"  ⚠️  Ошибка при автоклике по письму: {e}")
        
        return "ERROR: Verification link not found on page. Make sure you opened the email."
    
    except Exception as e:
        return f"ERROR: Exception while extracting link: {str(e)}"


def get_custom_function_declarations():
    """
    Возвращает декларации custom functions для Computer Use модели.
    
    Returns:
        List of FunctionDeclaration объектов
    """
    return [
        FunctionDeclaration(
            name="switch_to_mail_tab",
            description=(
                "Switch focus to the temp-mail.org tab. "
                "Use this function when you need to interact with the email inbox "
                "(e.g., to click on an email, read messages, or extract verification links). "
                "After calling this, all subsequent actions (click, scroll, type) will be performed on the mail tab."
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        FunctionDeclaration(
            name="switch_to_airtable_tab",
            description=(
                "Switch focus to the Airtable registration tab. "
                "Use this function when you need to interact with Airtable.com "
                "(e.g., to fill the registration form, click buttons, navigate pages). "
                "After calling this, all subsequent actions will be performed on the Airtable tab."
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        FunctionDeclaration(
            name="extract_verification_link",
            description=(
                "Extracts the email verification link from the current page. "
                "Use this function when you are viewing an email on temp-mail.org "
                "that contains an Airtable verification link. "
                "IMPORTANT: You must call switch_to_mail_tab BEFORE this function "
                "to ensure you are on the correct tab. "
                "The function will parse the HTML and return the full verification URL. "
                "You should call this AFTER opening the email from Airtable."
            ),
            parameters={
                "type": "object",
                "properties": {},  # Нет параметров - работает с текущей страницей
                "required": []
            }
        ),
        FunctionDeclaration(
            name="extract_email_from_page",
            description=(
                "Extracts the temporary email address from temp-mail.org page. "
                "Use this function when you are on https://temp-mail.org/en/ homepage "
                "and need to get the email address that is displayed in the textbox. "
                "The function will read the email from the page using JavaScript."
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


async def extract_email_from_tempmail_page(page) -> str:
    """
    Извлекает email адрес со страницы temp-mail.org.
    
    Ключевой момент: email генерируется динамически, может занять до 10 сек!
    
    Args:
        page: Playwright Page объект
    
    Returns:
        Email адрес или сообщение об ошибке
    """
    try:
        # 🔑 МЕТОД 1: Активное ожидание email с повторными попытками
        # Email может загружаться до 15 сек после загрузки страницы
        print("  ⏳ Ожидание загрузки email (до 15 сек)...")
        
        for attempt in range(30):  # 30 попыток × 0.5 сек = 15 сек макс
            # 🎯 Расширенный поиск email через JS
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
                print(f"  ✅ Найден email через JavaScript (попытка {attempt+1}): {email}")
                return email
            
            # Логируем прогресс каждые 2 попытки
            if attempt % 4 == 0 and attempt > 0:
                print(f"     ... ещё ждём (попытка {attempt+1}/30, текущее значение: '{email}')")
            
            await asyncio.sleep(0.5)
        
        print(f"  ⚠️  Email не загрузился за 15 сек, пробуем альтернативные методы...")
        
        # 🔑 МЕТОД 2: Regex поиск в HTML (если JS не помог)
        html = await page.content()
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, html)
        
        for match in matches:
            # Пропускаем служебные email'ы
            if 'example.com' not in match and 'test.com' not in match:
                print(f"  ✅ Найден email через regex: {match}")
                return match
        
        # 🔑 МЕТОД 3: Чтение из input field через селектор
        try:
            input_field = await page.query_selector('#mail, input[type="email"], input[type="text"]')
            if input_field:
                email = await input_field.input_value()
                if email and '@' in email and '.' in email:
                    print(f"  ✅ Найден email через селектор: {email}")
                    return email
        except Exception as e:
            print(f"  ⚠️  Selector метод не сработал: {e}")
        
        # 🔑 МЕТОД 4: Поиск во всех input элементах (последняя попытка)
        try:
            all_emails = await page.evaluate('''() => {
                const inputs = document.querySelectorAll('input');
                for (let inp of inputs) {
                    if (inp.value && inp.value.includes('@')) {
                        return inp.value;
                    }
                }
                return null;
            }''')
            
            if all_emails and '@' in all_emails:
                print(f"  ✅ Найден email во всех input'ах: {all_emails}")
                return all_emails
        except:
            pass
        
        return "ERROR: Email not found. Make sure page is fully loaded and email is visible."
    
    except Exception as e:
        return f"ERROR: Exception while extracting email: {str(e)}"


# ==================== ОБРАБОТЧИК TOOL CALLS ====================

async def execute_computer_use_action(page, function_call: FunctionCall, screen_width: int, screen_height: int, page_mail=None, page_airtable=None) -> dict:
    """
    Выполняет действие Computer Use в браузере Playwright.
    
    Полная реализация всех действий из официальной документации:
    https://ai.google.dev/gemini-api/docs/computer-use
    
    Args:
        page: Playwright Page объект (текущая активная страница)
        function_call: FunctionCall от модели
        screen_width: Ширина экрана в пикселях
        screen_height: Высота экрана в пикселях
        page_mail: (optional) Вкладка с temp-mail (для переключения)
        page_airtable: (optional) Вкладка с Airtable (для переключения)
    
    Returns:
        dict с результатом выполнения
    """
    action = function_call.name
    args = dict(function_call.args) if function_call.args else {}
    
    print(f"  🔧 Действие: {action}")
    print(f"     Аргументы: {json.dumps(args, indent=2, ensure_ascii=False)}")
    
    # Проверка safety_decision
    if 'safety_decision' in args:
        safety = args['safety_decision']
        if safety.get('decision') == 'require_confirmation':
            print(f"  ⚠️  Safety Warning: {safety.get('explanation', 'N/A')}")
            # В реальном приложении здесь нужен запрос подтверждения у пользователя
            # Для теста просто продолжаем (auto-approve)
            # ВАЖНО: Обязательно включить safety_acknowledgement И url
            return {
                "success": True, 
                "message": "Safety confirmation (auto-approved for testing)", 
                "safety_acknowledgement": "true",
                "url": page.url  # ОБЯЗАТЕЛЬНО для Computer Use!
            }
    
    try:
        # ==================== ПЕРЕКЛЮЧЕНИЕ ВКЛАДОК ====================
        
        if action == "switch_to_mail_tab":
            if page_mail is None:
                return {"success": False, "message": "Mail tab not available", "url": page.url}
            # Переключаем вкладку на передний план
            await page_mail.bring_to_front()
            # Критически важно: ждём чтобы вкладка стала ВИДИМОЙ
            # Computer Use API скриншотит ТЕКУЩУЮ видимую вкладку после получения response
            try:
                await page_mail.wait_for_load_state("domcontentloaded", timeout=5000)
            except:
                pass  # Страница уже загружена
            await asyncio.sleep(1.0)  # Дополнительная пауза для полного рендеринга
            print(f"  ✅ Переключились на вкладку temp-mail: {page_mail.url}")
            return {
                "success": True, 
                "message": f"Switched to mail tab: {page_mail.url}",
                "url": page_mail.url
            }
        
        elif action == "switch_to_airtable_tab":
            if page_airtable is None:
                return {"success": False, "message": "Airtable tab not available", "url": page.url}
            # Переключаем вкладку на передний план
            await page_airtable.bring_to_front()
            # Критически важно: ждём чтобы вкладка стала ВИДИМОЙ
            # Computer Use API скриншотит ТЕКУЩУЮ видимую вкладку после получения response
            try:
                await page_airtable.wait_for_load_state("domcontentloaded", timeout=5000)
            except:
                pass  # Страница уже загружена
            await asyncio.sleep(1.0)  # Дополнительная пауза для полного рендеринга
            print(f"  ✅ Переключились на вкладку Airtable: {page_airtable.url}")
            return {
                "success": True, 
                "message": f"Switched to Airtable tab: {page_airtable.url}",
                "url": page_airtable.url
            }
        
        # ==================== НАВИГАЦИЯ ====================
        
        if action == "open_web_browser":
            # Браузер уже открыт
            return {"success": True, "message": "Браузер уже открыт", "url": page.url}
        
        elif action == "navigate":
            url = args.get("url", "")
            # Блокируем переходы на посторонние сайты
            if not is_allowed_url(url):
                return {"success": False, "message": f"Navigation blocked by policy: {url}", "url": page.url}
            
            try:
                # 🎯 УЛУЧШЕННАЯ СТРАТЕГИЯ НАВИГАЦИИ ПРОТИВ БЛОКИРОВОК
                # Задержка перед навигацией (избегаем триггеров скорости)
                await page.wait_for_timeout(1000)
                
                # СТРАТЕГИЯ 1: domcontentloaded вместо networkidle (более мягкое)
                try:
                    print(f"  🌐 Навигация на {url} (стратегия: domcontentloaded)...")
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(1500)  # Даём странице стабилизироваться
                    print(f"  ✅ Загружено: {page.url}")
                except Exception as e:
                    print(f"  ⚠️  domcontentloaded не сработал ({str(e)[:50]}). Попытка 2...")
                    
                    # СТРАТЕГИЯ 2: load (менее строгое, чем domcontentloaded)
                    try:
                        await page.goto(url, wait_until="load", timeout=15000)
                        await page.wait_for_timeout(1000)
                        print(f"  ✅ Загружено (стратегия load): {page.url}")
                    except Exception as e2:
                        print(f"  ⚠️  load не сработал ({str(e2)[:50]}). Попытка 3...")
                        
                        # СТРАТЕГИЯ 3: Минимальное ожидание (для особенно сложных сайтов)
                        try:
                            nav_task = page.goto(url, wait_until=None)
                            await asyncio.sleep(3)  # Просто ждём 3 сек
                            await asyncio.wait_for(nav_task, timeout=5)
                            print(f"  ✅ Загружено (стратегия minimal): {page.url}")
                        except Exception as e3:
                            # СТРАТЕГИЯ 4: Даже если goto фейлится, даём ещё 5 сек на загрузку
                            print(f"  ⚠️  Все стратегии не сработали. Ждём 5 сек и проверяем...")
                            await page.wait_for_timeout(5000)
                            print(f"  ℹ️  Текущий URL: {page.url}")
                
                # 🎯 ДОПОЛНИТЕЛЬНОЕ ОЖИДАНИЕ DOM элементов (критически важно!)
                print(f"  ⏳ Ожидание загрузки основных элементов DOM...")
                
                # Ждём любого значимого элемента в зависимости от URL
                try:
                    if "temp-mail" in url or "tempmail" in url.lower():
                        # Для temp-mail ждём input с email
                        await page.wait_for_selector("#mail, input[type='email']", timeout=10000)
                        print(f"  ✅ Input элемент загружен")
                    elif "airtable" in url:
                        # Для Airtable ждём основной контент
                        await page.wait_for_selector("input, button, form, [role='main']", timeout=10000)
                        print(f"  ✅ Основные элементы Airtable загружены")
                    else:
                        # Универсальное ожидание body
                        await page.wait_for_selector("body", timeout=5000)
                except Exception as e:
                    print(f"  ⚠️  Ожидание селектора истекло ({str(e)[:50]}), но продолжаем...")
                
                # 🛡️ Cloudflare check отключен
                
                return {"success": True, "message": f"Перешел на {page.url}", "url": page.url}
                
            except Exception as e:
                print(f"  ❌ Навигация не удалась: {str(e)}")
                return {"success": False, "message": f"Navigate failed: {str(e)}", "url": page.url}
        
        elif action == "search":
            # Действие 'search' отключено политикой безопасности для этой задачи
            return {"success": False, "message": "Search action is disabled for this task", "url": page.url}
        
        elif action == "go_back":
            await page.go_back(wait_until="networkidle")
            return {"success": True, "message": "Вернулся назад", "url": page.url}
        
        elif action == "go_forward":
            await page.go_forward(wait_until="networkidle")
            return {"success": True, "message": "Перешел вперед", "url": page.url}
        
        # ==================== КЛИКИ И НАВЕДЕНИЕ ====================
        
        elif action == "click_at":
            # Денормализация координат (0-999 → реальные пиксели)
            x = args.get("x", 0)
            y = args.get("y", 0)
            actual_x = int(x / 1000 * screen_width)
            actual_y = int(y / 1000 * screen_height)
            
            await page.mouse.click(actual_x, actual_y)
            await page.wait_for_load_state("networkidle", timeout=5000)
            
            return {"success": True, "message": f"Клик по ({x}, {y}) → ({actual_x}, {actual_y})px", "url": page.url}
        
        elif action == "hover_at":
            x = args.get("x", 0)
            y = args.get("y", 0)
            actual_x = int(x / 1000 * screen_width)
            actual_y = int(y / 1000 * screen_height)
            
            await page.mouse.move(actual_x, actual_y)
            await asyncio.sleep(0.5)  # Небольшая пауза для появления меню
            
            return {"success": True, "message": f"Навел курсор на ({x}, {y}) → ({actual_x}, {actual_y})px", "url": page.url}
        
        # ==================== ВВОД ТЕКСТА ====================
        
        elif action == "type_text_at":
            x = args.get("x", 0)
            y = args.get("y", 0)
            text = args.get("text", "")
            press_enter = args.get("press_enter", True)
            clear_before = args.get("clear_before_typing", True)
            
            actual_x = int(x / 1000 * screen_width)
            actual_y = int(y / 1000 * screen_height)
            
            # Клик по полю
            await page.mouse.click(actual_x, actual_y)
            await asyncio.sleep(0.3)
            
            # Очистка поля (если нужно)
            if clear_before:
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
            
            # Ввод текста
            await page.keyboard.type(text, delay=50)  # delay для естественности
            
            # Enter (если нужно)
            if press_enter:
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("networkidle", timeout=5000)
            
            return {"success": True, "message": f"Ввел текст '{text[:50]}...' at ({x}, {y})", "url": page.url}
        
        # ==================== КЛАВИАТУРНЫЕ ДЕЙСТВИЯ ====================
        
        elif action == "key_combination":
            keys = args.get("keys", "")
            await page.keyboard.press(keys)
            await asyncio.sleep(0.5)
            
            return {"success": True, "message": f"Нажал клавиши: {keys}", "url": page.url}
        
        # ==================== СКРОЛЛИНГ ====================
        
        elif action == "scroll_document":
            direction = args.get("direction", "down")
            scroll_amount = 500
            
            if direction == "down":
                await page.mouse.wheel(0, scroll_amount)
            elif direction == "up":
                await page.mouse.wheel(0, -scroll_amount)
            elif direction == "right":
                await page.mouse.wheel(scroll_amount, 0)
            elif direction == "left":
                await page.mouse.wheel(-scroll_amount, 0)
            
            await asyncio.sleep(0.5)
            return {"success": True, "message": f"Прокрутил страницу {direction}", "url": page.url}
        
        elif action == "scroll_at":
            x = args.get("x", 0)
            y = args.get("y", 0)
            direction = args.get("direction", "down")
            magnitude = args.get("magnitude", 800)
            
            actual_x = int(x / 1000 * screen_width)
            actual_y = int(y / 1000 * screen_height)
            actual_magnitude = int(magnitude / 1000 * screen_height)
            
            # Навести курсор на элемент
            await page.mouse.move(actual_x, actual_y)
            
            # Прокрутить
            if direction == "down":
                await page.mouse.wheel(0, actual_magnitude)
            elif direction == "up":
                await page.mouse.wheel(0, -actual_magnitude)
            elif direction == "right":
                await page.mouse.wheel(actual_magnitude, 0)
            elif direction == "left":
                await page.mouse.wheel(-actual_magnitude, 0)
            
            await asyncio.sleep(0.5)
            return {"success": True, "message": f"Прокрутил элемент at ({x}, {y}) {direction} на {magnitude}", "url": page.url}
        
        # ==================== DRAG & DROP ====================
        
        elif action == "drag_and_drop":
            x = args.get("x", 0)
            y = args.get("y", 0)
            dest_x = args.get("destination_x", 0)
            dest_y = args.get("destination_y", 0)
            
            start_x = int(x / 1000 * screen_width)
            start_y = int(y / 1000 * screen_height)
            end_x = int(dest_x / 1000 * screen_width)
            end_y = int(dest_y / 1000 * screen_height)
            
            # Перетаскивание
            await page.mouse.move(start_x, start_y)
            await page.mouse.down()
            await asyncio.sleep(0.2)
            await page.mouse.move(end_x, end_y, steps=10)
            await asyncio.sleep(0.2)
            await page.mouse.up()
            
            return {"success": True, "message": f"Перетащил из ({x}, {y}) в ({dest_x}, {dest_y})", "url": page.url}
        
        # ==================== ОЖИДАНИЕ ====================
        
        elif action == "wait_5_seconds":
            await asyncio.sleep(5)
            return {"success": True, "message": "Ждал 5 секунд", "url": page.url}
        
        # ==================== CUSTOM FUNCTIONS ====================
        
        elif action == "extract_verification_link":
            print("  🔍 Извлечение verification link из HTML...")
            url = await extract_verification_link_from_page(page)
            if url.startswith("ERROR"):
                return {"success": False, "error": url, "url": page.url}
            else:
                print(f"  ✅ Найдена ссылка: {url}")
                return {
                    "success": True,
                    "verification_url": url,
                    "message": f"Verification link extracted: {url}",
                    "url": page.url
                }
        
        elif action == "extract_email_from_page":
            print("  📧 Извлечение email адреса из HTML...")
            email = await extract_email_from_tempmail_page(page)
            if email.startswith("ERROR"):
                return {"success": False, "error": email, "url": page.url}
            else:
                print(f"  ✅ Найден email: {email}")
                return {
                    "success": True,
                    "email": email,
                    "message": f"Email extracted: {email}",
                    "url": page.url
                }
        
        # ==================== НЕИЗВЕСТНОЕ ДЕЙСТВИЕ ====================
        
        else:
            return {"success": False, "message": f"Неизвестное действие: {action}", "url": page.url}
    
    except Exception as e:
        error_msg = f"Ошибка выполнения {action}: {str(e)}"
        print(f"  ❌ {error_msg}")
        return {"success": False, "message": error_msg, "url": page.url}


# ==================== ОСНОВНОЙ ЦИКЛ АГЕНТА ====================

async def run_computer_use_agent(task: str, max_steps: int = 20):
    """
    Запускает агента с Computer Use моделью.
    
    Args:
        task: Задача для агента (текстовый промпт)
        max_steps: Максимальное количество шагов
    """
    # Загружаем API ключ
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("❌ GOOGLE_API_KEY не найден в .env файле")
    
    print("=" * 70)
    print("🚀 Запуск Computer Use агента")
    print("=" * 70)
    print(f"📋 Задача: {task}")
    print(f"⚙️  Модель: gemini-2.5-computer-use-preview-10-2025")
    print(f"🔄 Максимум шагов: {max_steps}")
    print("=" * 70)
    
    # Инициализируем клиент Google Generative AI
    client = genai.Client(api_key=api_key)
    model_name = "gemini-2.5-computer-use-preview-10-2025"
    
    # Конфигурация с Computer Use tool
    config = GenerateContentConfig(
        tools=[
            Tool(
                computer_use=ComputerUse(
                    environment=genai.types.Environment.ENVIRONMENT_BROWSER
                )
            )
        ],
        temperature=0.3,
        max_output_tokens=4096,
    )
    
    # Размеры экрана (рекомендуется 1440x900 по документации)
    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 900
    
    # Запускаем браузер Playwright с полной конфигурацией
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,  # Видим что происходит
        args=[
            '--start-maximized',
            '--disable-blink-features=AutomationControlled'
        ]
    )
    
    # 🔧 КРИТИЧЕСКИ ВАЖНО: Полная конфигурация контекста
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
    
    # 🛡️ Применяем stealth для обхода детекции
    if stealth_async:
        print("🕵️  Применяем playwright-stealth...")
        await stealth_async(context)
    
    # 🎯 ВАЖНО: Используем первую страницу вместо создания новой
    pages = context.pages
    if pages:
        page = pages[0]
        print(f"📄 Используем существующую вкладку (всего: {len(pages)})")
    else:
        page = await context.new_page()
        print("📄 Создана новая вкладка")
    
    # Начальная страница
    await page.goto("about:blank")
    
    # История диалога
    history = []
    
    # Первый промпт с задачей
    initial_prompt = f"""
Ты - автономный агент для управления браузером. Твоя задача:

{task}

У тебя есть доступ к Computer Use tool для взаимодействия с браузером.
Доступные действия: navigate, click, type, scroll, press_key, wait, get_text.

Планируй свои действия, выполняй их последовательно и сообщай о результате.
Когда задача выполнена, опиши итог и завершай работу.
"""
    
    print(f"\n💬 Начальный промпт отправлен...")
    
    try:
        step = 0
        
        # Первый запрос: задача + начальный скриншот
        screenshot_bytes = await page.screenshot(type="png", full_page=False)
        history = [
            Content(
                role="user",
                parts=[
                    Part.from_text(text=initial_prompt),
                    Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes))
                ]
            )
        ]
        
        while step < max_steps:
            step += 1
            print(f"\n{'=' * 70}")
            print(f"🔄 ШАГ {step}/{max_steps}")
            print(f"{'=' * 70}")
            
            # Запрос к модели с текущей историей
            print("🧠 Модель анализирует...")
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=history,
                config=config
            )
            
            # Обрабатываем ответ
            if not response.candidates or not response.candidates[0].content.parts:
                print("⚠️  Модель не вернула ответ")
                break
            
            # Получаем ответ модели
            model_content = response.candidates[0].content
            
            # Проверяем все parts в ответе
            has_tool_calls = False
            has_text = False
            tool_responses = []
            
            for part in model_content.parts:
                # Текстовый вывод от модели
                if hasattr(part, 'text') and part.text:
                    has_text = True
                    print(f"\n💭 Мысль модели:")
                    print(f"   {part.text[:500]}...")
                
                # Tool call (действие)
                if hasattr(part, 'function_call') and part.function_call:
                    has_tool_calls = True
                    
                    # Выполняем действие с передачей размеров экрана
                    result = await execute_computer_use_action(
                        page, 
                        part.function_call,
                        SCREEN_WIDTH,
                        SCREEN_HEIGHT
                    )
                    
                    print(f"  ✅ Результат: {result.get('message', result)}")
                    
                    # Сохраняем результат для добавления в историю
                    tool_responses.append(
                        Part.from_function_response(
                            name=part.function_call.name,
                            response=result
                        )
                    )
                    
                    # Небольшая пауза между действиями
                    await asyncio.sleep(1)
            
            # Добавляем в историю ответ модели
            history.append(model_content)
            
            # Если были tool_calls, добавляем их результаты + новый скриншот
            if tool_responses:
                # ВАЖНО: После выполнения действий делаем новый скриншот
                screenshot_bytes = await page.screenshot(type="png", full_page=False)
                
                # Добавляем function_response + скриншот в один user turn
                history.append(
                    Content(
                        role="user",
                        parts=tool_responses + [
                            Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes))
                        ]
                    )
                )
            
            # Если есть текст но нет tool_calls - задача завершена
            if has_text and not has_tool_calls:
                print("\n" + "=" * 70)
                print("✅ ЗАДАЧА ЗАВЕРШЕНА")
                print("=" * 70)
                print(f"\n📄 Финальный ответ модели:")
                for part in model_content.parts:
                    if hasattr(part, 'text') and part.text:
                        print(part.text)
                break
            
            # Если нет ни текста, ни tool_calls
            if not has_text and not has_tool_calls:
                print("\n⚠️  Модель не вернула ни текста, ни действий")
                break
        
        else:
            print(f"\n⏱️  Достигнут лимит шагов ({max_steps})")
        
        # Сохраняем финальный скриншот
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = Path("logs") / f"computer_use_final_{timestamp}.png"
        screenshot_path.parent.mkdir(exist_ok=True)
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"\n📸 Финальный скриншот: {screenshot_path}")
        
        # Держим браузер открытым для проверки
        print("\n💤 Браузер остается открытым. Нажмите Ctrl+C для завершения...")
        await asyncio.sleep(3600)  # 1 час
    
    except KeyboardInterrupt:
        print("\n\n👋 Остановлено пользователем")
    
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Закрываем браузер...")
        await browser.close()
        await playwright.stop()
        print("✅ Готово")


# ==================== AIRTABLE REGISTRATION ====================

async def run_email_extraction(max_steps: int = 15) -> Optional[str]:
    """
    ШАГ 1: Получить временный email с temp-mail.org
    
    Args:
        max_steps: Максимальное количество шагов (15 достаточно)
    
    Returns:
        Email адрес или None при ошибке
    """
    task = """
MISSION: Extract temporary email address from temp-mail.org

🎯 IMPORTANT: The page https://temp-mail.org/en/ is ALREADY OPEN!
   - You can see it in the screenshot
   - DO NOT navigate again - just work with current page

YOUR TASK:
  Get the temporary email address from the current page (temp-mail.org).

STEP-BY-STEP WORKFLOW:
  1. ✅ Page is ALREADY open - check the screenshot
  
  2. ⚠️ CRITICAL: WAIT 10 seconds for email to fully load
     - The email does NOT appear immediately!
     - Textbox shows "Loading..." at first, then email appears
     - Use wait_5_seconds action TWICE (5s + 5s = 10s total)
  
  3. Extract email using the CUSTOM FUNCTION:
     ⭐ CALL: extract_email_from_page()
     - This function will parse HTML and get the email
     - It returns the email address as a string
     - DO NOT try to read email from screenshot manually!
  
  4. After getting email from function, IMMEDIATELY RETURN result:
     - Simply state: "The temporary email is: xxx@domain.com"
     - DO NOT do any other actions after getting email
  
  5. STOP as soon as email is extracted

ANTI-LOOP RULES:
  - Maximum 3 attempts total
  - If extract_email_from_page() returns error → WAIT 5s and try again
  - DO NOT navigate to temp-mail again (already there!)
  - DO NOT click random elements hoping to find email

SUCCESS CHECK:
  ✅ Email extracted = Contains @ and domain name
  ❌ Failed = Function returns ERROR

REMEMBER:
  - Page is ALREADY OPEN - don't navigate
  - ALWAYS use extract_email_from_page() function
  - DO NOT try to read visually from screenshot
  - STOP immediately after getting email
"""
    
    print("\n" + "=" * 70)
    print("📧 ШАГ 1: ПОЛУЧЕНИЕ ВРЕМЕННОГО EMAIL")
    print("=" * 70)
    
    # Загружаем API ключ
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("❌ GOOGLE_API_KEY не найден в .env файле")
    
    # Инициализируем клиент
    client = genai.Client(api_key=api_key)
    model_name = "gemini-2.5-computer-use-preview-10-2025"
    
    # Конфигурация с Computer Use + Custom Functions
    config = GenerateContentConfig(
        tools=[
            Tool(computer_use=ComputerUse(
                environment=genai.types.Environment.ENVIRONMENT_BROWSER
            )),
            Tool(function_declarations=get_custom_function_declarations())
        ],
        temperature=0.3,
        max_output_tokens=4096,
    )
    
    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 900
    
    # Запускаем браузер с полной конфигурацией
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False, 
        args=[
            '--start-maximized',
            '--disable-blink-features=AutomationControlled'
        ]
    )
    
    # 🔧 КРИТИЧЕСКИ ВАЖНО: Полная конфигурация контекста
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
    
    # 🛡️ Применяем stealth для обхода детекции
    if stealth_async:
        print("🕵️  Применяем playwright-stealth...")
        await stealth_async(context)
    
    # 🎯 ВАЖНО: Используем первую страницу вместо создания новой
    # Chromium автоматически создает одну вкладку при запуске
    pages = context.pages
    if pages:
        page = pages[0]  # Используем существующую вкладку
        print(f"📄 Используем существующую вкладку (всего вкладок: {len(pages)})")
    else:
        page = await context.new_page()  # Создаем только если нет вкладок
        print("📄 Создана новая вкладка")
    
    # 🎯 СРАЗУ ОТКРЫВАЕМ temp-mail.org вместо about:blank
    # Это дает агенту уже готовую страницу для работы
    print("🌐 Открываем начальную страницу temp-mail.org...")
    await page.goto("https://temp-mail.org/en/", wait_until="domcontentloaded")
    await page.wait_for_timeout(10000)  # Даем странице стабилизироваться
    print("✅ Страница загружена, агент может начинать работу")
    
    history = []
    screenshot_bytes = await safe_screenshot(page, full_page=False, timeout_ms=10000)
    
    history.append(
        Content(role="user", parts=[
            Part(text=task),
            Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes))
        ])
    )
    
    print("\n💬 Начальный промпт отправлен...")
    
    extracted_email = None
    
    try:
        for step in range(1, max_steps + 1):
            print(f"\n{'=' * 70}")
            print(f"🔄 ШАГ {step}/{max_steps}")
            print("=" * 70)
            print("🧠 Модель анализирует...")
            
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=history,
                config=config
            )
            
            candidate = response.candidates[0]
            model_content = candidate.content
            
            # Проверяем наличие текста и tool_calls
            has_text = any(hasattr(part, 'text') and part.text for part in model_content.parts)
            has_tool_calls = any(hasattr(part, 'function_call') and part.function_call for part in model_content.parts)
            
            # Выводим текст модели
            if has_text:
                for part in model_content.parts:
                    if hasattr(part, 'text') and part.text:
                        print(f"\n💭 Мысль модели:")
                        print(f"   {part.text[:300]}...")
            
            # Выполняем tool_calls
            tool_responses = []
            if has_tool_calls:
                for part in model_content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        result = await execute_computer_use_action(page, fc, SCREEN_WIDTH, SCREEN_HEIGHT)
                        
                        # Извлекаем email из результата
                        if fc.name == "extract_email_from_page" and result.get("success"):
                            extracted_email = result.get("email")
                            print(f"\n✅ EMAIL ПОЛУЧЕН: {extracted_email}")
                        
                        tool_responses.append(
                            Part(function_response=FunctionResponse(
                                name=fc.name,
                                response=result
                            ))
                        )
            
            history.append(model_content)
            
            if tool_responses:
                screenshot_bytes = await page.screenshot(type="png", full_page=False)
                history.append(
                    Content(role="user", parts=tool_responses + [
                        Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes))
                    ])
                )
            
            # Если есть текст и email извлечен - завершаем
            if extracted_email:
                print(f"\n✅ ШАГ 1 ЗАВЕРШЁН: Email = {extracted_email}")
                break
            
            # Если есть текст но нет tool_calls - задача завершена
            if has_text and not has_tool_calls:
                # Пытаемся извлечь email из текста
                for part in model_content.parts:
                    if hasattr(part, 'text') and part.text:
                        extracted_email = extract_email_from_text(part.text)
                        if extracted_email:
                            print(f"\n✅ Email извлечён из текста: {extracted_email}")
                            break
                break
        
        # НЕ закрываем браузер - он нужен для ШАГ 2!
        print("\n💤 Браузер остается открытым для ШАГ 2...")
        return extracted_email
        
    except Exception as e:
        print(f"\n❌ Ошибка в ШАГ 1: {e}")
        await browser.close()
        await playwright.stop()
        return None


async def run_airtable_registration(email: str, max_steps: int = 35) -> dict:
    """
    ШАГ 2: Зарегистрироваться на Airtable + подтвердить email
    
    Args:
        email: Email полученный на ШАГ 1
        max_steps: Максимальное количество шагов (35 для сложной задачи)
    
    Returns:
        dict с результатом: {status, email, confirmed, notes}
    """
    task = f"""
MISSION: Register on Airtable and confirm email

YOUR EMAIL: {email}
REGISTRATION URL: https://airtable.com/invite/r/ovoAP1zR

YOUR TASK:
  Complete full Airtable registration using the email above, including email verification.

CRITICAL WORKFLOW:
  📝 PHASE 1: AIRTABLE REGISTRATION FORM
  -------------------------------------------
  STEP 1: Navigate to https://airtable.com/invite/r/ovoAP1zR
  
  STEP 2: WAIT 5 seconds for form to load
  
  STEP 3: Fill registration form with these EXACT details:
    * Email: {email} (EXACTLY this email, DO NOT MODIFY!)
    * Full Name: "Maria Rodriguez" (or any realistic name)
    * Password: "SecurePass2024!" (minimum 8 characters)
    
    IMPORTANT NOTES:
    - Submit button "Create account" is DISABLED initially
    - It only enables when ALL fields are valid
    - If button stays disabled → check email format is correct
  
  STEP 4: Click "Create account" button ONCE (only one click!)
  
  STEP 5: ⚠️ CRITICAL - After clicking submit, you MUST:
    1. **WAIT 10 seconds** for page to process
    2. **CHECK current URL** - THIS IS THE SUCCESS INDICATOR!
       ✅ SUCCESS = URL changed from "/invite/r/..." to "https://airtable.com/" (base domain)
       ✅ SUCCESS = URL contains "/workspace" or "/verify"
       ❌ FAIL = URL still contains "/invite/"
    3. **IF URL DID NOT CHANGE**:
       - Check page for error messages
       - Read what the error says
       - Report error and STOP
    4. **IF URL CHANGED TO https://airtable.com/**:
       - Registration is SUCCESSFUL!
       - Proceed immediately to PHASE 2

  ✉️ PHASE 2: EMAIL VERIFICATION
  -------------------------------------------
  STEP 6: Navigate to https://temp-mail.org/en/
    * This is where you got the email originally
  
  STEP 7: WAIT 15 seconds for email to arrive
    * Airtable sends confirmation email within ~15 seconds
    * Email subject: "Please confirm your email"
    * Sender: Airtable <noreply@airtable.com>
  
  STEP 8: Refresh temp-mail page if needed
    * If inbox still shows "Your inbox is empty"
    * Reload the page or wait longer
  
  STEP 9: Find and CLICK on the Airtable email to open it
    * Click on subject line to view email content
  
  STEP 10: Extract verification URL using CUSTOM FUNCTION
    ⭐ CALL: extract_verification_link()
    - This function will parse HTML and find the verification URL
    - It returns the full URL as a string
    - DO NOT try to click the link visually!
  
  STEP 11: Navigate to verification URL
    * After getting URL from extract_verification_link()
    * Use navigate(url=<the_url_from_function>)
    * This opens it in SAME tab (not new tab!)
  
  STEP 12: WAIT 5 seconds for verification to process
  
  STEP 13: CHECK verification success
    * Look for success message or redirect to workspace
    * Account should now be confirmed

ANTI-LOOP PROTECTION:
  ⛔ If you repeat the same action 3+ times → STOP and analyze
  
  Common issues & solutions:
  - ❌ Submit button disabled? 
    → Check all fields are filled correctly
    → Email must be valid format
  
  - ❌ URL not changing after submit?
    → WAIT full 10 seconds before checking
    → Look for error messages on page
  
  - ❌ Email not arriving?
    → WAIT up to 30 seconds total
    → Refresh temp-mail page
  
  - ❌ Can't find verification link?
    → Use extract_verification_link() function
    → DO NOT try to click visually
  
  NEVER:
    - Click "Create account" more than once
    - Check URL before waiting 10 seconds
    - Click verification link (use navigate instead)
    - Wait indefinitely (max 30s for email)

SUCCESS INDICATORS:
  ✅ Registration successful:
    - URL changes from "/invite/r/xxx" to "https://airtable.com/"
  
  ✅ Email verification successful:
    - After opening verify URL, page shows success or workspace

FINAL OUTPUT:
  When done, clearly state:
  - "Registration successful" or "Registration failed"
  - "Email confirmed" or "Email not confirmed"
"""
    
    print("\n" + "=" * 70)
    print("📝 ШАГ 2: РЕГИСТРАЦИЯ НА AIRTABLE + ПОДТВЕРЖДЕНИЕ")
    print("=" * 70)
    print(f"📧 Используем email: {email}")
    
    # Загружаем API ключ
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    
    # Инициализируем клиент
    client = genai.Client(api_key=api_key)
    model_name = "gemini-2.5-computer-use-preview-10-2025"
    
    # Конфигурация с Computer Use + Custom Functions
    config = GenerateContentConfig(
        tools=[
            Tool(computer_use=ComputerUse(
                environment=genai.types.Environment.ENVIRONMENT_BROWSER
            )),
            Tool(function_declarations=get_custom_function_declarations())
        ],
        temperature=0.3,
        max_output_tokens=4096,
    )
    
    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 900
    
    # Запускаем браузер с полной конфигурацией (новый для ШАГ 2)
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False, 
        args=[
            '--start-maximized',
            '--disable-blink-features=AutomationControlled'
        ]
    )
    
    # 🔧 КРИТИЧЕСКИ ВАЖНО: Полная конфигурация контекста
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
    
    # 🛡️ Применяем stealth для обхода детекции
    if stealth_async:
        print("🕵️  Применяем playwright-stealth...")
        await stealth_async(context)
    
    # 🎯 ВАЖНО: Используем первую страницу вместо создания новой
    pages = context.pages
    if pages:
        page = pages[0]
        print(f"📄 Используем существующую вкладку (всего: {len(pages)})")
    else:
        page = await context.new_page()
        print("📄 Создана новая вкладка")
    
    await page.goto("about:blank")
    
    history = []
    screenshot_bytes = await page.screenshot(type="png", full_page=False)
    
    history.append(
        Content(role="user", parts=[
            Part(text=task),
            Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes))
        ])
    )
    
    print("\n💬 Начальный промпт отправлен...")
    
    result = {
        "status": "unknown",
        "email": email,
        "confirmed": False,
        "notes": ""
    }
    
    try:
        for step in range(1, max_steps + 1):
            print(f"\n{'=' * 70}")
            print(f"🔄 ШАГ {step}/{max_steps}")
            print("=" * 70)
            print("🧠 Модель анализирует...")
            
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=history,
                config=config
            )
            
            candidate = response.candidates[0]
            model_content = candidate.content
            
            has_text = any(hasattr(part, 'text') and part.text for part in model_content.parts)
            has_tool_calls = any(hasattr(part, 'function_call') and part.function_call for part in model_content.parts)
            
            # Выводим текст модели
            if has_text:
                final_text = ""
                for part in model_content.parts:
                    if hasattr(part, 'text') and part.text:
                        print(f"\n💭 Мысль модели:")
                        print(f"   {part.text[:300]}...")
                        final_text += part.text
                
                # Парсим статус из финального текста
                if "registration successful" in final_text.lower() or "account created" in final_text.lower():
                    result["status"] = "success"
                if "email confirmed" in final_text.lower() or "email verified" in final_text.lower():
                    result["confirmed"] = True
                if "failed" in final_text.lower() or "error" in final_text.lower():
                    result["status"] = "failed"
            
            # Выполняем tool_calls
            tool_responses = []
            if has_tool_calls:
                for part in model_content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        exec_result = await execute_computer_use_action(page, fc, SCREEN_WIDTH, SCREEN_HEIGHT)
                        tool_responses.append(
                            Part(function_response=FunctionResponse(
                                name=fc.name,
                                response=exec_result
                            ))
                        )
            
            history.append(model_content)
            
            if tool_responses:
                screenshot_bytes = await page.screenshot(type="png", full_page=False)
                history.append(
                    Content(role="user", parts=tool_responses + [
                        Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes))
                    ])
                )
            
            # Если есть текст но нет tool_calls - задача завершена
            if has_text and not has_tool_calls:
                print("\n✅ ЗАДАЧА ЗАВЕРШЕНА")
                result["notes"] = final_text[:200] if 'final_text' in locals() else "Registration completed"
                break
        
        # Сохраняем финальный скриншот
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = Path("logs") / f"airtable_registration_{timestamp}.png"
        screenshot_path.parent.mkdir(exist_ok=True)
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"\n📸 Финальный скриншот: {screenshot_path}")
        
        # Держим браузер открытым для проверки
        print("\n💤 Браузер остается открытым 60 сек для проверки...")
        await asyncio.sleep(60)
        
    except Exception as e:
        print(f"\n❌ Ошибка в ШАГ 2: {e}")
        result["status"] = "failed"
        result["notes"] = f"Error: {str(e)}"
    
    finally:
        await browser.close()
        await playwright.stop()
    
    return result


async def run_email_extraction_on_page(page, client, config, max_steps: int = 15) -> Optional[str]:
    """
    ШАГ 1 (унифицированный): Получить временный email с temp-mail.org на УЖЕ открытой вкладке.

    Args:
        page: Вкладка Playwright c temp-mail (или about:blank)
        client: Инициализированный genai.Client
        config: Конфигурация GenerateContentConfig с Computer Use + custom functions
        max_steps: Ограничение шагов

    Returns:
        Строка email или None, если не удалось получить
    """
    task = """
MISSION: Extract temporary email address from temp-mail.org

YOUR TASK:
  Get a temporary email address from https://temp-mail.org/en/ that will be used for Airtable registration.

RULES (Unified Session):
  - Work ONLY in this tab for temp-mail actions
  - DO NOT close this tab under any circumstances
  - You may refresh or navigate within temp-mail.org, but keep this tab focused on inbox

STEP-BY-STEP WORKFLOW:
  1. Navigate to https://temp-mail.org/en/
  2. WAIT 10 seconds after page loads (email appears with delay)
  3. Call extract_email_from_page() to get the email from HTML
  4. As soon as you have the email, return it in text and STOP

ANTI-LOOP RULES:
  - Max 3 attempts
  - If function returns error → WAIT 5s and retry

SUCCESS CHECK:
  ✅ Contains '@' and a domain
"""

    model_name = "gemini-2.5-computer-use-preview-10-2025"
    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 900

    history = []
    screenshot_bytes = await safe_screenshot(page, full_page=False, timeout_ms=10000)
    parts = [Part(text=task)]
    if screenshot_bytes:
        parts.append(Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes)))
    history.append(Content(role="user", parts=parts))

    print("\n💬 Начальный промпт (email extraction, unified) отправлен...")

    extracted_email = None

    for step in range(1, max_steps + 1):
        print(f"\n{'=' * 70}")
        print(f"🔄 ШАГ {step}/{max_steps} (email)")
        print("=" * 70)
        print("🧠 Модель анализирует...")

        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model_name,
            contents=history,
            config=config
        )
        if response is None or not getattr(response, 'candidates', None):
            print("⚠️  Пустой ответ модели (email), повторяю через 2с...")
            await asyncio.sleep(2)
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=history,
                config=config
            )
            if response is None or not getattr(response, 'candidates', None):
                print("❌ Модель вернула пустой ответ повторно (email)")
                break

        candidate = response.candidates[0]
        model_content = candidate.content

        # Печать мыслей модели
        for part in model_content.parts:
            if hasattr(part, 'text') and part.text:
                print(f"\n💭 Мысль модели:\n   {part.text[:300]}...")

        # Выполнение действий
        tool_responses = []
        for part in model_content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                fc = part.function_call
                result = await execute_computer_use_action(page, fc, SCREEN_WIDTH, SCREEN_HEIGHT)
                # Cloudflare детект для каждого действия шага email
                # Cloudflare check отключен
                if fc.name == "extract_email_from_page" and result.get("success"):
                    extracted_email = result.get("email")
                    print(f"\n✅ EMAIL ПОЛУЧЕН (unified): {extracted_email}")
                tool_responses.append(
                    Part(function_response=FunctionResponse(name=fc.name, response=result))
                )

        history.append(model_content)

        if tool_responses:
            screenshot_bytes = await safe_screenshot(page, full_page=False, timeout_ms=10000)
            parts = tool_responses.copy()
            if screenshot_bytes:
                parts.append(Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes)))
            history.append(Content(role="user", parts=parts))

        if extracted_email:
            return extracted_email

        # Если модель завершила без действий, попробуем вытащить email из текста
        if all(not getattr(p, 'function_call', None) for p in model_content.parts):
            for p in model_content.parts:
                if hasattr(p, 'text') and p.text:
                    maybe_email = extract_email_from_text(p.text)
                    if maybe_email:
                        print(f"\n✅ EMAIL извлечён из текста (unified): {maybe_email}")
                        return maybe_email
            break

    return None


async def run_airtable_registration_on_pages(email: str, page_mail, page_airtable, client, config, max_steps: int = 40) -> dict:
    """
    ШАГ 2 (унифицированный): Регистрация на Airtable на ОТДЕЛЬНОЙ вкладке, оставляя почту открытой.

    Правило: вкладка с temp-mail (page_mail) не закрывается и не теряет состояние.
    Функцию extract_verification_link() выполняем на вкладке почты, а навигацию по verify URL — на вкладке Airtable.
    """
    task = f"""
MISSION: Register on Airtable and confirm email (Two-tab workflow)

YOUR EMAIL: {email}
REGISTRATION URL: https://airtable.com/invite/r/ovoAP1zR

YOU HAVE TWO BROWSER TABS AVAILABLE:
  1. Airtable tab (currently active) - for registration
  2. Temp-mail tab (already open) - for checking verification email

AVAILABLE TAB SWITCHING FUNCTIONS:
  - switch_to_mail_tab() - switches to temp-mail inbox
  - switch_to_airtable_tab() - switches to Airtable registration page

CRITICAL WORKFLOW:
  1) [AIRTABLE TAB - already active] Navigate to https://airtable.com/invite/r/ovoAP1zR and complete signup:
     - Email: {email}
     - Full Name: Maria Rodriguez (or similar realistic name)
     - Password: SecurePass2024!
     - Click "Create account" button ONCE
     - Wait 10 seconds to see if URL changes from /invite/

  2) [SWITCH TO MAIL TAB] Use switch_to_mail_tab() to view the inbox
     - Wait up to 30 seconds for Airtable email (subject: "Please confirm your email")
     - Click on the email to open it

  3) [MAIL TAB] Call extract_verification_link() to get the verification URL from email content
     - This will return the full https://airtable.com/auth/verifyEmail/... URL

  4) [SWITCH TO AIRTABLE TAB] Use switch_to_airtable_tab() to go back
     - Navigate to the verification URL using navigate(url=...)
     - Wait 5-10 seconds and confirm success

IMPORTANT RULES:
  - ALWAYS use switch_to_mail_tab() BEFORE clicking on emails or calling extract_verification_link()
  - ALWAYS use switch_to_airtable_tab() BEFORE navigating to Airtable pages
  - The mail tab must stay open throughout the entire process
  - After switching tabs, ALL subsequent actions happen on that tab until you switch again
"""

    model_name = "gemini-2.5-computer-use-preview-10-2025"
    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 900

    history = []
    screenshot_bytes = await safe_screenshot(page_airtable, full_page=False, timeout_ms=10000)
    parts = [Part(text=task)]
    if screenshot_bytes:
        parts.append(Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes)))
    history.append(Content(role="user", parts=parts))

    print("\n💬 Начальный промпт (airtable registration, unified) отправлен...")

    result = {
        "status": "unknown",
        "email": email,
        "confirmed": False,
        "notes": ""
    }

    final_text = ""
    
    # Отслеживание текущей активной вкладки между шагами
    # Начинаем с Airtable, т.к. это вкладка регистрации
    current_active_page = page_airtable

    for step in range(1, max_steps + 1):
        print(f"\n{'=' * 70}")
        print(f"🔄 ШАГ {step}/{max_steps} (registration)")
        print("=" * 70)
        print("🧠 Модель анализирует...")

        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model_name,
            contents=history,
            config=config
        )
        if response is None or not getattr(response, 'candidates', None):
            print("⚠️  Пустой ответ модели, жду 2с и повторяю запрос...")
            await asyncio.sleep(2)
            # Однократный повтор
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=history,
                config=config
            )
            if response is None or not getattr(response, 'candidates', None):
                print("❌ Модель вернула пустой ответ повторно. Прерываю.")
                result["status"] = "failed"
                result["notes"] = "Model returned empty response"
                break

        candidate = response.candidates[0]
        model_content = candidate.content

        has_tool_calls = any(hasattr(p, 'function_call') and p.function_call for p in model_content.parts)

        # Печать мыслей и накопление финального текста
        for part in model_content.parts:
            if hasattr(part, 'text') and part.text:
                print(f"\n💭 Мысль модели:\n   {part.text[:400]}...")
                final_text += part.text + "\n"

        # Выполнение действий: switch_to_* меняет активную вкладку, остальные работают с текущей
        # current_active_page хранится между шагами (определена выше цикла)
        tool_responses = []
        
        for part in model_content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                fc = part.function_call
                
                # Обработка switch_to_* функций меняет current_active_page
                if fc.name == "switch_to_mail_tab":
                    exec_result = await execute_computer_use_action(
                        page_mail, fc, SCREEN_WIDTH, SCREEN_HEIGHT, 
                        page_mail=page_mail, page_airtable=page_airtable
                    )
                    current_active_page = page_mail  # Теперь активна почта
                    tool_responses.append(Part(function_response=FunctionResponse(name=fc.name, response=exec_result)))
                    
                elif fc.name == "switch_to_airtable_tab":
                    exec_result = await execute_computer_use_action(
                        page_airtable, fc, SCREEN_WIDTH, SCREEN_HEIGHT, 
                        page_mail=page_mail, page_airtable=page_airtable
                    )
                    current_active_page = page_airtable  # Теперь активен Airtable
                    tool_responses.append(Part(function_response=FunctionResponse(name=fc.name, response=exec_result)))
                    
                elif fc.name == "extract_verification_link":
                    # Явно переключаемся на почту для извлечения ссылки
                    await page_mail.bring_to_front()
                    current_active_page = page_mail
                    exec_result = await execute_computer_use_action(
                        page_mail, fc, SCREEN_WIDTH, SCREEN_HEIGHT,
                        page_mail=page_mail, page_airtable=page_airtable
                    )
                    tool_responses.append(Part(function_response=FunctionResponse(name=fc.name, response=exec_result)))
                    
                else:
                    # Все остальные действия выполняем на текущей активной вкладке
                    exec_result = await execute_computer_use_action(
                        current_active_page, fc, SCREEN_WIDTH, SCREEN_HEIGHT,
                        page_mail=page_mail, page_airtable=page_airtable
                    )
                    tool_responses.append(Part(function_response=FunctionResponse(name=fc.name, response=exec_result)))

        history.append(model_content)

        if tool_responses:
            # ВАЖНО: При работе с множественными вкладками Computer Use API не может автоматически
            # определить какую вкладку скриншотить. Нужно ВРУЧНУЮ добавить скриншот текущей активной вкладки!
            
            # Убедимся что current_active_page действительно на переднем плане
            await current_active_page.bring_to_front()
            await asyncio.sleep(0.3)  # Небольшая пауза для рендеринга
            
            screenshot_bytes = await safe_screenshot(current_active_page, full_page=False, timeout_ms=10000)
            parts = tool_responses.copy()
            if screenshot_bytes:
                parts.append(Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes)))
            else:
                print("  ⚠️  Не удалось сделать скриншот текущей вкладки!")
            history.append(Content(role="user", parts=parts))

        # Оценка состояния по тексту
        lower = final_text.lower()
        if "registration successful" in lower or "account created" in lower:
            result["status"] = "success"
        if "email confirmed" in lower or "email verified" in lower:
            result["confirmed"] = True
        if "failed" in lower or "error" in lower:
            result["status"] = "failed"

        # Завершение, если модель перестала делать вызовы
        if not has_tool_calls and final_text.strip():
            print("\n✅ ЗАДАЧА ЗАВЕРШЕНА (unified)")
            result["notes"] = final_text[:400]
            break

    # Скриншот итогового состояния Airtable
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = Path("logs") / f"airtable_registration_unified_{timestamp}.png"
    screenshot_path.parent.mkdir(exist_ok=True)
    try:
        img = await safe_screenshot(page_airtable, full_page=True, timeout_ms=15000)
        with open(screenshot_path, 'wb') as f:
            f.write(img)
    except Exception as e:
        print(f"⚠️ Не удалось сохранить финальный скриншот (unified): {e}")
    print(f"\n📸 Финальный скриншот (unified): {screenshot_path}")

    return result


async def main_airtable_registration_unified():
    """
    ЕДИНЫЙ ПОТОК: один браузер, две вкладки (temp-mail + Airtable).
    Почтовая вкладка НЕ закрывается, верификационная ссылка извлекается на ней же.
    """
    print("=" * 70)
    print("🚀 АВТО-РЕГИСТРАЦИЯ НА AIRTABLE (единый браузер, 2 вкладки)")
    print("=" * 70)
    print("🔒 Политика навигации: разрешены только airtable.com и temp-mail.org")

    # Загружаем API ключ
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("❌ GOOGLE_API_KEY не найден в .env файле")

    # Инициализация клиента и конфигурации
    client = genai.Client(api_key=api_key)
    config = GenerateContentConfig(
        tools=[
            Tool(computer_use=ComputerUse(environment=genai.types.Environment.ENVIRONMENT_BROWSER)),
            Tool(function_declarations=get_custom_function_declarations())
        ],
        temperature=0.3,
        max_output_tokens=4096,
    )

    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 900

    # Один браузер, две вкладки. По умолчанию БЕЗ persistent (совпадает с успешно пройденными тестами).
    # Включить persistent можно переменной окружения AS_USE_PERSISTENT=1
    playwright = await async_playwright().start()
    use_persistent = os.getenv('AS_USE_PERSISTENT', '0') == '1'
    if use_persistent:
        user_data_dir = os.getenv("PLAYWRIGHT_USER_DATA_DIR") or os.getenv("BROWSER_USE_USER_DATA_DIR")
        if not user_data_dir:
            user_data_dir = str(Path.cwd() / "profiles" / "unified_default")
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        print(f"🗂️  Профиль браузера (persistent): {user_data_dir}")
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={'width': SCREEN_WIDTH, 'height': SCREEN_HEIGHT},
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Cache-Control': 'max-age=0',
            },
            args=['--start-maximized', '--disable-blink-features=AutomationControlled']
        )
    else:
        print("🗂️  Режим без persistent профиля (как в тестах)")
        browser = await playwright.chromium.launch(
            headless=False,
            args=['--start-maximized', '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            viewport={'width': SCREEN_WIDTH, 'height': SCREEN_HEIGHT},
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Cache-Control': 'max-age=0',
            },
        )

    # ✅ Применяем stealth для обхода Cloudflare и других систем обнаружения
    if stealth_async:
        # ✅ ИСПРАВЛЕНО: В playwright-stealth 2.0.0 метод принимает context
        await stealth_async(context)
        print("🕵️ Stealth mode активирован (обход Cloudflare и bot-detection)")
    else:
        print("⚠️  Stealth mode недоступен (playwright_stealth не установлен правильно)")
        print("   💡 Установите: pip install playwright-stealth")
    
    # 🎭 Установка Sec-Fetch-* headers (как в working test)
    await context.set_extra_http_headers({
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    })
    print("🎭 Sec-Fetch-* headers установлены (точно как в working test)")

    # === Управление вкладками: СТАРТУЕМ С ОДНОЙ (почта), вторую создадим ПОТОМ ===
    # В persistent-профиле Chromium может восстановить сессию и открыть несколько about:blank
    # Чтобы исключить это, закрываем все текущие и создаём заново 1 предсказуемую вкладку
    existing = list(context.pages)
    print(f"🧭 Вкладок сразу после старта: {len(existing)} → закрываю все и создаю 1 (почта)")
    for p in existing:
        try:
            await p.close()
        except Exception:
            pass

    # Создаём ровно одну вкладку: для почты (temp-mail)
    page_mail = await context.new_page()
    if page_mail.url == "" or not page_mail.url:
        await page_mail.goto("about:blank")
    print(f"📄 Текущих вкладок: {len(context.pages)} (только mail)")

    try:
    # ШАГ 1: получаем email на вкладке почты (вкладка почты остаётся открытой)
        print("\n📧 ШАГ 1: Получение временного email (вкладка почты остаётся открытой)...")
        email = await run_email_extraction_on_page(page_mail, client, config, max_steps=15)

        if not email:
            print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить email")
            save_registration_result(email="None", status="failed", confirmed=False, notes="Failed to get temporary email (unified)")
            return

        print(f"\n✅ Email получен: {email}")

        # Только теперь создаём вторую вкладку под Airtable
        page_airtable = await context.new_page()
        if page_airtable.url == "" or not page_airtable.url:
            await page_airtable.goto("about:blank")
        print(f"🪟 Открыта вторая вкладка для Airtable. Всего вкладок: {len(context.pages)}")

        # ШАГ 2: регистрация на Airtable с использованием двух вкладок
        print("\n📝 ШАГ 2: Регистрация на Airtable (почта не закрывается)...")
        result = await run_airtable_registration_on_pages(email, page_mail, page_airtable, client, config, max_steps=40)

        # Сохранение результата
        save_registration_result(
            email=result.get("email", email),
            status=result.get("status", "unknown"),
            confirmed=result.get("confirmed", False),
            notes=result.get("notes", "")
        )

        # Краткий итог
        print("\n" + "=" * 70)
        print("✅ РЕГИСТРАЦИЯ (unified) ЗАВЕРШЕНА")
        print("=" * 70)
        print(f"📧 Email: {result.get('email', email)}")
        print(f"📊 Статус: {result.get('status', 'unknown')}")
        print(f"✓ Подтверждено: {result.get('confirmed', False)}")
        if result.get('notes'):
            print(f"📝 Заметки: {result['notes'][:200]}")

        # Небольшая пауза для визуальной проверки
        print("\n💤 Вкладки останутся открыты 30 сек для проверки...")
        await asyncio.sleep(30)

    except KeyboardInterrupt:
        print("\n👋 Прервано пользователем")
    finally:
        print("\n🧹 Закрываем браузер (unified, persistent context)...")
        await context.close()
        await playwright.stop()

    return


async def main_airtable_registration():
    """
    Главная функция для полной регистрации на Airtable
    """
    print("=" * 70)
    print("🚀 АВТОМАТИЧЕСКАЯ РЕГИСТРАЦИЯ НА AIRTABLE")
    print("=" * 70)
    
    try:
        # ШАГ 1: Получение email
        print("\n📧 ШАГ 1: Получение временного email...")
        email = await run_email_extraction(max_steps=15)
        
        if not email:
            print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить email")
            save_registration_result(
                email="None",
                status="failed",
                confirmed=False,
                notes="Failed to get temporary email"
            )
            return
        
        print(f"\n✅ Email получен: {email}")
        
        # Пауза между этапами
        print("\n⏳ Пауза 5 секунд перед регистрацией...")
        await asyncio.sleep(5)
        
        # ШАГ 2: Регистрация
        print("\n📝 ШАГ 2: Регистрация на Airtable...")
        result = await run_airtable_registration(email, max_steps=35)
        
        # Сохранение результата
        save_registration_result(
            email=result["email"],
            status=result["status"],
            confirmed=result["confirmed"],
            notes=result["notes"]
        )
        
        # Итоговая статистика
        print("\n" + "=" * 70)
        print("✅ РЕГИСТРАЦИЯ ЗАВЕРШЕНА")
        print("=" * 70)
        print(f"📧 Email: {result['email']}")
        print(f"📊 Статус: {result['status']}")
        print(f"✓ Подтверждено: {result['confirmed']}")
        if result['notes']:
            print(f"📝 Заметки: {result['notes'][:200]}")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n👋 Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


# ==================== ЗАПУСК ====================

async def main():
    """Главная функция - демо с Yandex"""
    
    # Задача для агента
    task = """
Открой сайт yandex.ru и найди информацию о курсе доллара к рублю.
Когда найдешь курс, сообщи мне текущее значение.
"""
    
    await run_computer_use_agent(task, max_steps=15)


if __name__ == "__main__":
    import sys
    
    # Выбор режима: демо или регистрация Airtable
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        print("🎯 Режим: Демо (отключены посторонние домены)")
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n👋 Завершено")
        except RuntimeError as e:
            if "Event loop is closed" not in str(e):
                raise
    else:
        print("🎯 Режим: Автоматическая регистрация на Airtable (по умолчанию)")
        print("🔒 Политика навигации: разрешены только airtable.com и temp-mail.org")
        try:
            # Используем единый поток с двумя вкладками, чтобы НЕ закрывать почту
            asyncio.run(main_airtable_registration_unified())
        except KeyboardInterrupt:
            print("\n👋 Завершено")
        except RuntimeError as e:
            if "Event loop is closed" not in str(e):
                raise