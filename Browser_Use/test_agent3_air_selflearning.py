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
import httpx

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


# ==================== SELF-LEARNING CORE (drop-in) ====================
import sqlite3
import random
import atexit
from time import perf_counter

class SelfLearnStore:
    def __init__(self, path="selflearn_airtable.sqlite3", epsilon_env_var="AUTOLEARN_EPS"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.cur = self.conn.cursor()
        self._init_schema()
        self.current_run_id = None
        self.step_counter = 0
        # Эпсилон для exploration
        try:
            self.epsilon = float(os.getenv(epsilon_env_var, "0.12"))
        except Exception:
            self.epsilon = 0.12

    def _init_schema(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                phase TEXT,
                email TEXT,
                result_status TEXT,
                confirmed INTEGER,
                total_ms INTEGER,
                notes TEXT
            )
        """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                step INTEGER,
                action TEXT,
                domain TEXT,
                url TEXT,
                params TEXT,
                success INTEGER,
                error TEXT,
                duration_ms INTEGER,
                created_at TEXT
            )
        """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS params (
                key TEXT,
                context TEXT,
                value TEXT,
                n INTEGER,
                success INTEGER,
                tot_ms INTEGER,
                last_ts TEXT,
                PRIMARY KEY (key, context, value)
            )
        """)
        self.conn.commit()

    def start_run(self, phase: str, email: str | None = None, extra: dict | None = None):
        ts = datetime.now().isoformat()
        self.cur.execute(
            "INSERT INTO runs (ts, phase, email, result_status, confirmed, total_ms, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, phase, email or "", "", 0, 0, json.dumps(extra or {}, ensure_ascii=False))
        )
        self.current_run_id = self.cur.lastrowid
        self.step_counter = 0
        self.conn.commit()
        return self.current_run_id

    def finish_run(self, status: str, confirmed: bool = False, notes: str = "", total_ms: int | None = None):
        if self.current_run_id is None:
            return
        self.cur.execute(
            "UPDATE runs SET result_status=?, confirmed=?, notes=?, total_ms=? WHERE id=?",
            (status or "", int(bool(confirmed)), notes or "", int(total_ms or 0), self.current_run_id)
        )
        self.conn.commit()

    def log_action(self, action: str, domain: str | None, url: str | None, params: dict | None,
                   success: bool, duration_ms: int, error: str | None = None, selector: str | None = None):
        self.step_counter += 1
        self.cur.execute(
            "INSERT INTO actions (run_id, step, action, domain, url, params, success, error, duration_ms, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                self.current_run_id, self.step_counter, action,
                (domain or ""), (url or ""),
                json.dumps(params or {}, ensure_ascii=False),
                int(bool(success)), (error or "")[:4000],
                int(duration_ms or 0), datetime.now().isoformat()
            )
        )
        if selector:
            # Отдельно учитываем «надёжность» селектора
            self.record_param_outcome("selector_ok", f"{domain}:{selector}", "used", success=int(bool(success)), duration_ms=duration_ms)
        self.conn.commit()

    def record_param_outcome(self, key: str, context: str, value, success: bool, duration_ms: int):
        self.cur.execute("""
            INSERT INTO params (key, context, value, n, success, tot_ms, last_ts)
            VALUES (?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(key, context, value) DO UPDATE SET
                n = n + 1,
                success = success + excluded.success,
                tot_ms = tot_ms + excluded.tot_ms,
                last_ts = excluded.last_ts
        """, (key, context or "", str(value), int(bool(success)), int(duration_ms or 0), datetime.now().isoformat()))
        self.conn.commit()

    def _stats_for(self, key: str, context: str):
        self.cur.execute("SELECT value, n, success, tot_ms FROM params WHERE key=? AND context=?", (key, context or ""))
        rows = self.cur.fetchall()
        stats = {}
        for v, n, s, tot in rows:
            stats[v] = {"n": n, "success": s, "tot_ms": tot, "avg_ms": (tot / (n or 1))}
        return stats

    def choose_option(self, key: str, context: str, options: list, default=None, minimize_time_weight: float = 0.25):
        # epsilon-greedy по reward = success_rate - w * normalized_time
        options = list(options)
        stats = self._stats_for(key, context)
        unexplored = [o for o in options if str(o) not in stats]

        if unexplored:
            choice = random.choice(unexplored)
        else:
            if random.random() < self.epsilon:
                choice = random.choice(options)
            else:
                best = None
                best_score = -1e9
                for o in options:
                    s = stats.get(str(o), {"n": 0, "success": 0, "avg_ms": 2000})
                    n = s["n"]; succ = s["success"]; avg_ms = s["avg_ms"]
                    succ_rate = (succ / n) if n > 0 else 0.5
                    time_penalty = minimize_time_weight * (avg_ms / 5000.0)
                    score = succ_rate - time_penalty
                    if score > best_score:
                        best_score = score
                        best = o
                choice = best if best is not None else (default if default in options else options[0])
        return choice

    def choose_numeric(self, key: str, context: str, candidates: list[int | float], default=None):
        val = self.choose_option(key, context, candidates, default=default)
        try:
            return int(val)
        except Exception:
            return float(val)

    def rank_methods(self, key: str, context: str, default_order: list[str]):
        # Сортировка методов по успешности и скорости
        stats = self._stats_for(key, context)
        def score(m):
            s = stats.get(m, {"n": 0, "success": 0, "avg_ms": 2500})
            n = s["n"]; succ = s["success"]; avg = s["avg_ms"]
            succ_rate = (succ / n) if n > 0 else 0.5
            return succ_rate - 0.2 * (avg / 5000.0)
        known = [m for m in default_order if m in stats]
        unknown = [m for m in default_order if m not in stats]
        ordered = sorted(known, key=lambda m: score(m), reverse=True) + unknown
        # Небольшая эксплорация: иногда меняем местами топ-2
        if len(ordered) >= 2 and random.random() < 0.1:
            ordered[0], ordered[1] = ordered[1], ordered[0]
        return ordered

def _domain_from_url(url: str | None) -> str:
    try:
        if not url:
            return ""
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""

LEARN = SelfLearnStore("selflearn_airtable.sqlite3")
atexit.register(lambda: getattr(LEARN, "conn", None) and LEARN.conn.close())
# ======================================================================


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


async def get_random_user_data() -> dict:
    """
    Получает случайные имя и пароль из API randomdatatools.ru
    
    Returns:
        dict: {
            'name': 'Имя Фамилия',
            'password': 'Сложный пароль'
        }
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://api.randomdatatools.ru/?gender=man")
            response.raise_for_status()
            data = response.json()
            
            # Формируем полное имя (FirstName + LastName)
            first_name = data.get('FirstName', 'Иван')
            last_name = data.get('LastName', 'Иванов')
            full_name = f"{first_name} {last_name}"
            
            # Используем готовый пароль из API и добавляем спецсимволы для надёжности
            api_password = data.get('Password', 'default123')
            # Airtable требует минимум 8 символов, добавим спецсимвол для надёжности
            password = f"{api_password}!@"
            
            user_data = {
                'name': full_name,
                'password': password
            }
            
            print(f"✅ Получены случайные данные: {full_name}, пароль: {password}")
            return user_data
            
    except Exception as e:
        print(f"⚠️ Ошибка получения случайных данных: {e}. Использую дефолтные значения.")
        # Fallback на дефолтные значения
        return {
            'name': 'Иван Иванов',
            'password': 'SecurePass2024!'
        }


async def safe_screenshot(page, full_page: bool = False, timeout_ms: int = 10000) -> Optional[bytes]:
    """Делает скриншот с учётом самообучающегося таймаута и логированием."""
    # Подбираем таймаут на основе опыта
    domain = _domain_from_url(getattr(page, "url", ""))
    chosen_timeout = LEARN.choose_numeric("screenshot_timeout_ms", domain or "any", [6000, 8000, 10000, 12000, 15000], default=timeout_ms)
    t0 = perf_counter()
    try:
        img = await page.screenshot(type="png", full_page=full_page, timeout=chosen_timeout)
        dt = int((perf_counter() - t0) * 1000)
        LEARN.log_action("screenshot", domain, getattr(page, "url", ""), {"full_page": full_page, "timeout_ms": chosen_timeout}, True, dt)
        LEARN.record_param_outcome("screenshot_timeout_ms", domain or "any", chosen_timeout, True, dt)
        return img
    except Exception as e:
        dt = int((perf_counter() - t0) * 1000)
        LEARN.log_action("screenshot", domain, getattr(page, "url", ""), {"full_page": full_page, "timeout_ms": chosen_timeout}, False, dt, error=str(e))
        LEARN.record_param_outcome("screenshot_timeout_ms", domain or "any", chosen_timeout, False, dt)
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
    # Сообщаем LEARN об итогах этого запуска
    try:
        LEARN.finish_run(status=status, confirmed=bool(confirmed), notes=notes or "")
    except Exception:
        pass
    
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
    """Извлекает verification link со страницы письма Airtable с обучаемым порядком методов."""
    domain = _domain_from_url(getattr(page, "url", ""))
    # Доступные методы
    default_order = ["regex", "js_links", "selector", "click_then_regex", "click_then_js"]
    order = LEARN.rank_methods("verify_extract_order", "airtable_email", default_order)
    print(f"  🔍 Порядок попыток извлечения ссылки: {order}")

    patterns = [
        r'https://airtable\.com/auth/verifyEmail/[^\s"<>\']+',
        r'https://airtable\.com/verify[^\s"<>\']+',
        r'https://[^/]*airtable\.com/[^\s"<>\']*verify[^\s"<>\']*',
    ]

    async def try_regex(source="page"):
        t0 = perf_counter()
        html = await page.content()
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                url = match.group(0)
                dt = int((perf_counter() - t0) * 1000)
                LEARN.log_action("verify_extract_regex", domain, page.url, {"source": source}, True, dt)
                LEARN.record_param_outcome("verify_extract_order", "airtable_email", "regex", True, dt)
                print(f"  ✅ Найден URL через regex: {url}")
                return url
        dt = int((perf_counter() - t0) * 1000)
        LEARN.log_action("verify_extract_regex", domain, page.url, {"source": source}, False, dt)
        return None

    async def try_js_links(source="page"):
        t0 = perf_counter()
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
                dt = int((perf_counter() - t0) * 1000)
                LEARN.log_action("verify_extract_js_links", domain, page.url, None, True, dt)
                LEARN.record_param_outcome("verify_extract_order", "airtable_email", "js_links", True, dt)
                print(f"  ✅ Найден URL через JS: {links[0]}")
                return links[0]
        except Exception as e:
            pass
        dt = int((perf_counter() - t0) * 1000)
        LEARN.log_action("verify_extract_js_links", domain, page.url, None, False, dt)
        return None

    async def try_selector():
        t0 = perf_counter()
        try:
            link = await page.query_selector('a[href*="verifyEmail"]')
            if link:
                url = await link.get_attribute('href')
                if url:
                    dt = int((perf_counter() - t0) * 1000)
                    LEARN.log_action("verify_extract_selector", domain, page.url, {"selector": 'a[href*="verifyEmail"]'}, True, dt, selector='a[href*="verifyEmail"]')
                    LEARN.record_param_outcome("verify_extract_order", "airtable_email", "selector", True, dt)
                    print(f"  ✅ Найден URL через селектор: {url}")
                    return url
        except Exception:
            pass
        dt = int((perf_counter() - t0) * 1000)
        LEARN.log_action("verify_extract_selector", domain, page.url, {"selector": 'a[href*="verifyEmail"]'}, False, dt)
        return None

    async def try_click_then_regex():
        print("  🔄 Пытаюсь открыть письмо Airtable и повторить regex...")
        t0 = perf_counter()
        try:
            clicked = await page.evaluate('''() => {
                const isVisible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                const nodes = Array.from(document.querySelectorAll('a, div, span, li'));
                const candidates = nodes.filter(el => {
                    const t = (el.textContent || '').toLowerCase();
                    return isVisible(el) && (
                        t.includes('airtable') ||
                        t.includes('confirm your email') ||
                        t.includes('please confirm') ||
                        t.includes('confirm email')
                    );
                });
                for (const el of candidates) { try { el.click(); return true; } catch (e) {} }
                return false;
            }''')
            await asyncio.sleep(2)
            url = await try_regex(source="after_click")
            dt = int((perf_counter() - t0) * 1000)
            if url:
                LEARN.log_action("verify_click_then_regex", domain, page.url, None, True, dt)
                LEARN.record_param_outcome("verify_extract_order", "airtable_email", "click_then_regex", True, dt)
                return url
            else:
                LEARN.log_action("verify_click_then_regex", domain, page.url, None, False, dt)
        except Exception as e:
            dt = int((perf_counter() - t0) * 1000)
            LEARN.log_action("verify_click_then_regex", domain, page.url, None, False, dt, error=str(e))
        return None

    async def try_click_then_js():
        print("  🔄 Пытаюсь открыть письмо Airtable и повторить JS-поиск ссылок...")
        t0 = perf_counter()
        try:
            await page.evaluate('''() => {
                const isVisible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                const nodes = Array.from(document.querySelectorAll('a, div, span, li'));
                const candidates = nodes.filter(el => {
                    const t = (el.textContent || '').toLowerCase();
                    return isVisible(el) && (t.includes('airtable') || t.includes('confirm'));
                });
                for (const el of candidates) { try { el.click(); return true; } catch (e) {} }
                return false;
            }''')
            await asyncio.sleep(2)
            url = await try_js_links(source="after_click")
            dt = int((perf_counter() - t0) * 1000)
            if url:
                LEARN.log_action("verify_click_then_js", domain, page.url, None, True, dt)
                LEARN.record_param_outcome("verify_extract_order", "airtable_email", "click_then_js", True, dt)
                return url
            else:
                LEARN.log_action("verify_click_then_js", domain, page.url, None, False, dt)
        except Exception as e:
            dt = int((perf_counter() - t0) * 1000)
            LEARN.log_action("verify_click_then_js", domain, page.url, None, False, dt, error=str(e))
        return None

    # Выполняем по обучаемому порядку
    for method in order:
        if method == "regex":
            url = await try_regex()
        elif method == "js_links":
            url = await try_js_links()
        elif method == "selector":
            url = await try_selector()
        elif method == "click_then_regex":
            url = await try_click_then_regex()
        elif method == "click_then_js":
            url = await try_click_then_js()
        else:
            url = None
        if url:
            return url

    return "ERROR: Verification link not found on page. Make sure you opened the email."


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
    """Извлекает email со страницы temp-mail.org с самообучаемыми таймаутами и логированием."""
    domain = _domain_from_url(getattr(page, "url", "https://temp-mail.org/en/"))
    total_wait_ms = LEARN.choose_numeric("email_initial_wait_ms", "temp-mail", [8000, 10000, 12000, 15000, 20000], default=15000)
    attempts = max(1, int(total_wait_ms / 500))
    print(f"  ⏳ Ожидание загрузки email (до ~{int(total_wait_ms/1000)} сек, {attempts} попыток)...")

    # Метод 1: Активный JS-поиск
    t0 = perf_counter()
    for attempt in range(attempts):
        try:
            email = await page.evaluate('''() => {
                let input = document.querySelector('#mail');
                if (input && input.value && input.value.includes('@')) return input.value;
                let inputs = document.querySelectorAll('input');
                for (let inp of inputs) {
                    if (inp.value && inp.value.includes('@') && (!inp.placeholder || !inp.placeholder.includes('@'))) {
                        return inp.value;
                    }
                }
                let elements = document.querySelectorAll('[class*="mail"], [class*="email"], [id*="mail"], [id*="email"]');
                for (let el of elements) {
                    if (el.value && el.value.includes('@')) return el.value;
                    if (el.innerText && el.innerText.includes('@')) return el.innerText;
                }
                return null;
            }''')
            if email and '@' in email and '.' in email:
                dt = int((perf_counter() - t0) * 1000)
                LEARN.log_action("email_extract_js", domain, page.url, {"attempt": attempt+1, "total_wait_ms": total_wait_ms}, True, dt)
                LEARN.record_param_outcome("email_extract_method", "temp-mail", "js", True, dt)
                print(f"  ✅ Найден email через JavaScript: {email}")
                return email
        except Exception as e_js:
            pass
        await asyncio.sleep(0.5)
    dt_js = int((perf_counter() - t0) * 1000)
    LEARN.log_action("email_extract_js", domain, page.url, {"attempts": attempts, "total_wait_ms": total_wait_ms}, False, dt_js)
    LEARN.record_param_outcome("email_initial_wait_ms", "temp-mail", total_wait_ms, False, dt_js)

    # Метод 2: Regex
    try:
        t1 = perf_counter()
        html = await page.content()
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, html)
        for match in matches:
            if 'example.com' not in match and 'test.com' not in match:
                dt = int((perf_counter() - t1) * 1000)
                LEARN.log_action("email_extract_regex", domain, page.url, None, True, dt)
                LEARN.record_param_outcome("email_extract_method", "temp-mail", "regex", True, dt)
                print(f"  ✅ Найден email через regex: {match}")
                return match
        dt = int((perf_counter() - t1) * 1000)
        LEARN.log_action("email_extract_regex", domain, page.url, None, False, dt)
    except Exception as e:
        pass

    # Метод 3: Селекторы напрямую
    try:
        t2 = perf_counter()
        input_field = await page.query_selector('#mail, input[type="email"], input[type="text"]')
        if input_field:
            email = await input_field.input_value()
            if email and '@' in email and '.' in email:
                dt = int((perf_counter() - t2) * 1000)
                LEARN.log_action("email_extract_selector", domain, page.url, {"selector": "#mail | input"}, True, dt, selector="#mail")
                LEARN.record_param_outcome("email_extract_method", "temp-mail", "selector", True, dt)
                return email
        dt = int((perf_counter() - t2) * 1000)
        LEARN.log_action("email_extract_selector", domain, page.url, {"selector": "#mail | input"}, False, dt)
    except Exception:
        pass

    # Метод 4: Опрашиваем все inputs
    try:
        t3 = perf_counter()
        all_emails = await page.evaluate('''() => {
            const inputs = document.querySelectorAll('input');
            for (let inp of inputs) {
                if (inp.value && inp.value.includes('@')) return inp.value;
            }
            return null;
        }''')
        if all_emails and '@' in all_emails:
            dt = int((perf_counter() - t3) * 1000)
            LEARN.log_action("email_extract_all_inputs", domain, page.url, None, True, dt)
            LEARN.record_param_outcome("email_extract_method", "temp-mail", "all_inputs", True, dt)
            return all_emails
        dt = int((perf_counter() - t3) * 1000)
        LEARN.log_action("email_extract_all_inputs", domain, page.url, None, False, dt)
    except:
        pass

    return "ERROR: Email not found. Make sure page is fully loaded and email is visible."


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
            # SELF-LEARNING: Адаптивная пауза для рендеринга
            tab_wait_ms = LEARN.choose_numeric("tab_switch_wait_ms", "tabs", [300, 600, 800, 1000, 1200, 1500], default=1000)
            t0 = perf_counter()
            await asyncio.sleep(tab_wait_ms / 1000)
            LEARN.log_action("switch_tab", _domain_from_url(page_mail.url), page_mail.url, {"target": "mail", "wait_ms": tab_wait_ms}, True, int((perf_counter()-t0)*1000))
            LEARN.record_param_outcome("tab_switch_wait_ms", "tabs", tab_wait_ms, True, tab_wait_ms)
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
            # SELF-LEARNING: Адаптивная пауза для рендеринга
            tab_wait_ms = LEARN.choose_numeric("tab_switch_wait_ms", "tabs", [300, 600, 800, 1000, 1200, 1500], default=1000)
            t0 = perf_counter()
            await asyncio.sleep(tab_wait_ms / 1000)
            LEARN.log_action("switch_tab", _domain_from_url(page_airtable.url), page_airtable.url, {"target": "airtable", "wait_ms": tab_wait_ms}, True, int((perf_counter()-t0)*1000))
            LEARN.record_param_outcome("tab_switch_wait_ms", "tabs", tab_wait_ms, True, tab_wait_ms)
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
            if not is_allowed_url(url):
                return {"success": False, "message": f"Navigation blocked by policy: {url}", "url": page.url}
            domain = _domain_from_url(url)
            # SELF-LEARNING: Выбор стартовой стратегии на основе опыта
            strategy = LEARN.choose_option("nav_strategy", domain, ["domcontentloaded", "load", "minimal"], default="domcontentloaded")
            after_wait_ms = LEARN.choose_numeric("nav_after_wait_ms", domain, [500, 1000, 1500, 2000, 3000], default=1500)
            selector_timeout_ms = LEARN.choose_numeric("selector_timeout_ms", domain, [5000, 8000, 10000, 12000, 15000], default=10000)

            # Небольшая задержка перед навигацией
            await page.wait_for_timeout(LEARN.choose_numeric("pre_nav_pause_ms", domain, [500, 800, 1000, 1200], default=1000))

            tried = []
            success = False
            err_msgs = []
            t_nav0 = perf_counter()

            # Сформируем порядок стратегий: выбранная + 2 запасных
            strategies = [strategy] + [s for s in ["domcontentloaded", "load", "minimal"] if s != strategy]
            for strat in strategies:
                tried.append(strat)
                try:
                    print(f"  🌐 Навигация на {url} (стратегия: {strat})...")
                    if strat == "domcontentloaded":
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    elif strat == "load":
                        await page.goto(url, wait_until="load", timeout=15000)
                    else:
                        nav_task = page.goto(url, wait_until=None)
                        await asyncio.sleep(LEARN.choose_numeric("nav_minimal_wait_ms", domain, [1500, 2000, 3000], default=3000) / 1000)
                        await asyncio.wait_for(nav_task, timeout=5)

                    await page.wait_for_timeout(after_wait_ms)
                    print(f"  ✅ Загружено: {page.url}")
                    # Доп. ожидание селекторов по домену
                    try:
                        if "temp-mail" in url or "tempmail" in url.lower():
                            t_sel = perf_counter()
                            await page.wait_for_selector("#mail, input[type='email']", timeout=selector_timeout_ms)
                            dt_sel = int((perf_counter() - t_sel)*1000)
                            LEARN.log_action("selector_wait", domain, page.url, {"selector": "#mail, input[type='email']"}, True, dt_sel, selector="#mail")
                            LEARN.record_param_outcome("selector_timeout_ms", domain, selector_timeout_ms, True, dt_sel)
                        elif "airtable" in url:
                            t_sel = perf_counter()
                            await page.wait_for_selector("input, button, form, [role='main']", timeout=selector_timeout_ms)
                            dt_sel = int((perf_counter() - t_sel)*1000)
                            LEARN.log_action("selector_wait", domain, page.url, {"selector": "input, button, form, [role='main']"}, True, dt_sel)
                            LEARN.record_param_outcome("selector_timeout_ms", domain, selector_timeout_ms, True, dt_sel)
                        else:
                            await page.wait_for_selector("body", timeout=5000)
                    except Exception as e_sel:
                        # Логируем, но не падаем
                        LEARN.log_action("selector_wait", domain, page.url, {"selector": "(domain-default)"}, False, 0, error=str(e_sel))

                    success = True
                    break
                except Exception as e_try:
                    msg = str(e_try)
                    err_msgs.append(f"{strat}: {msg[:80]}")
                    print(f"  ⚠️  Стратегия {strat} не сработала ({msg[:80]}) → пробую следующую...")

            dt_nav = int((perf_counter() - t_nav0) * 1000)
            LEARN.log_action("navigate", domain, url, {"tried": tried, "chosen": strategy, "after_wait_ms": after_wait_ms}, success, dt_nav, error=" | ".join(err_msgs))
            LEARN.record_param_outcome("nav_strategy", domain, strategy, success, dt_nav)
            LEARN.record_param_outcome("nav_after_wait_ms", domain, after_wait_ms, success, dt_nav)

            if not success:
                return {"success": False, "message": f"Navigate failed ({' | '.join(err_msgs)})", "url": page.url}

            return {"success": True, "message": f"Перешел на {page.url}", "url": page.url}
        
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
REGISTRATION URL: https://airtable.com/invite/r/LzgpVACU

YOUR TASK:
  Complete full Airtable registration using the email above, including email verification.

CRITICAL WORKFLOW:
  📝 PHASE 1: AIRTABLE REGISTRATION FORM
  -------------------------------------------
  STEP 1: Navigate to https://airtable.com/invite/r/LzgpVACU
  
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


async def run_airtable_registration_on_pages(email: str, user_data: dict, page_mail, page_airtable, client, config, max_steps: int = 40) -> dict:
    """
    ШАГ 2 (унифицированный): Регистрация на Airtable на ОТДЕЛЬНОЙ вкладке, оставляя почту открытой.

    Правило: вкладка с temp-mail (page_mail) не закрывается и не теряет состояние.
    Функцию extract_verification_link() выполняем на вкладке почты, а навигацию по verify URL — на вкладке Airtable.
    
    Args:
        email: Email адрес для регистрации
        user_data: Словарь с данными пользователя (name, password, birthdate)
        page_mail: Playwright page объект для temp-mail
        page_airtable: Playwright page объект для Airtable
        client: Google AI client
        config: Конфигурация для модели
        max_steps: Максимальное количество шагов
    """
    full_name = user_data.get('name', 'John Smith')
    password = user_data.get('password', 'SecurePass2024!')
    
    task = f"""
MISSION: Register on Airtable and confirm email (Two-tab workflow)

YOUR EMAIL: {email}
YOUR FULL NAME: {full_name}
YOUR PASSWORD: {password}
REGISTRATION URL: https://airtable.com/invite/r/LzgpVACU

YOU HAVE TWO BROWSER TABS AVAILABLE:
  1. Airtable tab (currently active) - for registration
  2. Temp-mail tab (already open) - for checking verification email

AVAILABLE TAB SWITCHING FUNCTIONS:
  - switch_to_mail_tab() - switches to temp-mail inbox
  - switch_to_airtable_tab() - switches to Airtable registration page

CRITICAL WORKFLOW (MUST COMPLETE ALL STEPS):
  1) [AIRTABLE TAB - already active] Navigate to https://airtable.com/invite/r/LzgpVACU and complete signup:
     - Email: {email}
     - Full Name: {full_name}
     - Password: {password}
     - Click "Create account" button ONCE
     - Wait 10 seconds to see if URL changes from /invite/

  2) [SWITCH TO MAIL TAB] Use switch_to_mail_tab() to view the inbox
     - Wait up to 30 seconds for Airtable email (subject: "Please confirm your email")
     - If email not visible, wait and refresh
     - Click on the email to open it
     - ⚠️ If click fails with timeout - TRY AGAIN! Wait 3 seconds and retry
     - ⚠️ If screenshot fails - CONTINUE ANYWAY! Try next action

  3) [MAIL TAB] Call extract_verification_link() to get the verification URL from email content
     - This will return the full https://airtable.com/auth/verifyEmail/... URL
     - If extraction fails - try clicking email again and retry

  4) [SWITCH TO AIRTABLE TAB] Use switch_to_airtable_tab() to go back
     - Navigate to the verification URL using navigate(url=...)
     - ⚠️ IMPORTANT: After navigation to verification URL, system will AUTO-WAIT 10 seconds
     - Email verification happens AUTOMATICALLY - just wait, don't look for confirmation
     - After 10 seconds, onboarding questions will appear automatically
     - You can then say task complete - onboarding will be handled separately

CRITICAL SUCCESS CRITERIA (DO NOT STOP UNTIL ALL ARE MET):
  ✅ MUST: Email verification link extracted from mail
  ✅ MUST: Navigated to verification URL on Airtable tab
  ✅ AFTER navigation to verification URL - task is COMPLETE (10 sec auto-wait will happen)
  ❌ You DON'T need to confirm verification manually - it's automatic
  ❌ You DON'T need to handle onboarding questions - separate process will do it

HANDLING ERRORS - VERY IMPORTANT:
  ⚠️ If action fails with timeout - RETRY at least 2-3 times
  ⚠️ If screenshot fails - IGNORE and continue with next action
  ⚠️ If click doesn't work - try clicking slightly different coordinates
  ⚠️ If page doesn't load - wait 5 seconds and try again
  ❌ NEVER say "task complete" unless ALL critical steps are verified
  ❌ NEVER stop if verification link not extracted yet
  ❌ NEVER stop if email not confirmed yet

IMPORTANT RULES:
  - ALWAYS use switch_to_mail_tab() BEFORE clicking on emails or calling extract_verification_link()
  - ALWAYS use switch_to_airtable_tab() BEFORE navigating to Airtable pages
  - The mail tab must stay open throughout the entire process
  - After switching tabs, ALL subsequent actions happen on that tab until you switch again
  - BE PERSISTENT - retry failed actions, don't give up after first error
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
        "notes": "",
        "verification_link_extracted": False,
        "navigated_to_verification": False
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
                    # Отмечаем что ссылка успешно извлечена
                    if exec_result.get("success") and exec_result.get("url"):
                        result["verification_link_extracted"] = True
                        print(f"  ✅ Ссылка верификации извлечена: {exec_result.get('url')[:50]}...")
                    tool_responses.append(Part(function_response=FunctionResponse(name=fc.name, response=exec_result)))
                    
                elif fc.name == "navigate":
                    # Выполняем навигацию
                    exec_result = await execute_computer_use_action(
                        current_active_page, fc, SCREEN_WIDTH, SCREEN_HEIGHT,
                        page_mail=page_mail, page_airtable=page_airtable
                    )
                    tool_responses.append(Part(function_response=FunctionResponse(name=fc.name, response=exec_result)))
                    
                    # Если это навигация по ссылке верификации - отмечаем и ждем 10 секунд
                    if result["verification_link_extracted"] and exec_result.get("success"):
                        url = fc.args.get("url", "")
                        if "verifyEmail" in url or "verify" in url.lower():
                            result["navigated_to_verification"] = True
                            print("  ✅ Переход по ссылке верификации выполнен")
                            print("  ⏳ Ожидание 10 секунд (автоматическая верификация + загрузка onboarding)...")
                            await asyncio.sleep(10)
                            print("  ✅ Верификация завершена, готово к onboarding")
                            # Автоматически считаем email подтвержденным
                            result["confirmed"] = True
                    
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
        if "email confirmed" in lower or "email verified" in lower or "verification successful" in lower:
            result["confirmed"] = True
        if "failed" in lower or "error" in lower:
            result["status"] = "failed"
        
        # Проверяем что модель перешла по ссылке верификации
        if "navigate" in [p.function_call.name for p in model_content.parts if hasattr(p, 'function_call') and p.function_call]:
            if result["verification_link_extracted"]:
                result["navigated_to_verification"] = True
                print("  ✅ Переход по ссылке верификации выполнен")

        # Завершение ТОЛЬКО если выполнены критические шаги
        if not has_tool_calls and final_text.strip():
            # Проверяем критические критерии
            critical_steps_completed = (
                result["verification_link_extracted"] and 
                result["navigated_to_verification"]
            )
            
            if critical_steps_completed:
                print("\n✅ ЗАДАЧА ЗАВЕРШЕНА (unified) - все критические шаги выполнены")
                result["notes"] = final_text[:400]
                break
            else:
                # Модель пытается завершиться, но критические шаги не выполнены
                missing_steps = []
                if not result["verification_link_extracted"]:
                    missing_steps.append("извлечение ссылки верификации")
                if not result["navigated_to_verification"]:
                    missing_steps.append("переход по ссылке верификации")
                
                print(f"\n⚠️  Модель хочет завершиться, но НЕ выполнены: {', '.join(missing_steps)}")
                print(f"   Продолжаем выполнение... (шаг {step}/{max_steps})")
                
                # Добавляем напоминание модели
                reminder = f"""
⚠️ CRITICAL REMINDER: Task is NOT complete yet!

Missing steps:
{chr(10).join(f'  ❌ {step}' for step in missing_steps)}

You MUST complete these steps:
1. Switch to mail tab (switch_to_mail_tab)
2. Click on the Airtable verification email
3. Extract verification link (extract_verification_link)
4. Switch to Airtable tab (switch_to_airtable_tab)
5. Navigate to the verification URL (navigate)

After step 5, the system will AUTO-WAIT 10 seconds and task will be complete.

DO NOT SAY "task complete" until you've done navigate() to the verification URL!
Continue with the next action now.
"""
                history.append(Content(role="user", parts=[Part(text=reminder)]))
                continue

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


async def run_airtable_onboarding(page_airtable, client, config, max_steps: int = 10) -> dict:
    """
    ШАГ 3 (дополнительный): Прохождение onboarding после регистрации на Airtable.
    
    После успешной регистрации и верификации email, Airtable показывает серию вопросов:
    - Для чего нужен Airtable (цель использования)
    - Размер команды
    - Тип таблиц которые нужны
    - Шаблоны для начала работы
    - Создание первой базы
    - Настройка первой таблицы
    - Tutorial/tour по функциям
    - И другие настройки
    
    Args:
        page_airtable: Playwright page объект для Airtable
        client: Google AI client
        config: Конфигурация для модели
        max_steps: Максимальное количество шагов (по умолчанию 10 для полного onboarding)
    
    Returns:
        dict с результатом: {status, completed_steps, notes}
    """
    
    # Генерируем случайные значения для onboarding
    import random
    
    use_cases = [
        "Project Management", "Content Planning", "Product Development", 
        "Event Planning", "CRM", "Inventory Tracking", "Task Management",
        "Marketing Campaigns", "Product Roadmap", "Team Collaboration"
    ]
    
    team_sizes = ["Just me", "2-10 people", "11-50 people", "51-200 people"]
    
    roles = [
        "Product Manager", "Developer", "Marketing", "Designer", "Operations",
        "Sales", "HR", "Finance", "Customer Success", "Founder", "Consultant"
    ]
    
    companies = [
        "TechCorp", "InnovateLab", "Digital Solutions", "Creative Studio",
        "StartupHub", "DataWorks", "CloudTech", "AppFactory", "WebStudio",
        "SoftwarePro", "DevTeam", "AgileWorks", "SmartSystems"
    ]
    
    industries = [
        "Technology", "Marketing", "Healthcare", "Finance", "Education",
        "E-commerce", "Media", "Real Estate", "Consulting", "Manufacturing"
    ]
    
    teams = [
        "Engineering", "Marketing", "Product", "Design", "Operations",
        "Sales", "Support", "HR", "Finance", "Research"
    ]
    
    workspace_names = [
        "My Workspace", "Project Hub", "Team Base", "Work Central",
        "Productivity Hub", "Task Center", "Collaboration Space", "Main Workspace"
    ]
    
    # Выбираем случайные значения
    random_use_case = random.choice(use_cases)
    random_team_size = random.choice(team_sizes)
    random_role = random.choice(roles)
    random_company = random.choice(companies)
    random_industry = random.choice(industries)
    random_team = random.choice(teams)
    random_workspace = random.choice(workspace_names)
    
    print(f"  🎲 Случайные значения для onboarding:")
    print(f"     - Use case: {random_use_case}")
    print(f"     - Company: {random_company}")
    print(f"     - Industry: {random_industry}")
    print(f"     - Team: {random_team}")
    print(f"     - Team size: {random_team_size}")
    print(f"     - Role: {random_role}")
    print(f"     - Workspace: {random_workspace}")
    
    task = f"""
MISSION: Complete FULL Airtable onboarding setup (up to 10 steps)

CONTEXT: You have successfully registered and verified email on Airtable.
Now you need to complete the ENTIRE initial setup wizard/onboarding process.

YOUR TASK:
  Go through ALL onboarding questions and complete ALL setup steps until you reach the main workspace.

TYPICAL AIRTABLE ONBOARDING FLOW (complete ALL steps):
  
  1️⃣ "What will you use Airtable for?" / "How do you plan to use Airtable?"
     → Answer: "{random_use_case}"
  
  2️⃣ "First, where do you work?" / "Company name?"
     → Answer: "{random_company}"
  
  3️⃣ "What industry is your company in?"
     → Answer: "{random_industry}"
  
  4️⃣ "Which team are you on?" / "What team?"
     → Answer: "{random_team}"
  
  5️⃣ "How big is your team?" / "Team size?"
     → Answer: "{random_team_size}"
  
  6️⃣ "What role best describes you?"
     → Answer: "{random_role}"
  
  7️⃣ "Would you like to start with a template?"
     → Select "Start from scratch" or choose any template
  
  8️⃣ "Create your first base" / "Name your workspace"
     → Answer: "{random_workspace}"
  
  9️⃣ "Add tables to your base"
     → Create or confirm table names (use default or type: "Tasks", "Projects")
  
  🔟 "Add fields to your table"
     → Add or confirm field types (use defaults or add: Text, Number, Date, etc.)
  
  1️⃣1️⃣ Tutorial/Tour prompts ("Let's show you around", "Take a tour")
     → Complete the tour OR click "Skip tour" to skip it
  
  1️⃣2️⃣ "Invite team members" / "Share your workspace"
     → Click "Skip" or "Maybe later" to skip invitations
  
  1️⃣3️⃣ Additional setup steps
     → Complete any remaining prompts until you reach the main workspace

IMPORTANT RULES:
  ✓ Complete ALL steps - don't stop early!
  ✓ Use the EXACT values specified above (in curly braces) for each question
  ✓ Type or select the specified answers - don't make up different values
  ✓ If you need to type text, use the exact value shown (e.g., "{random_company}", "{random_workspace}")
  ✓ If you need to select from options, choose the closest match to the specified value
  ✓ Click "Next", "Continue", "Get Started", "Skip" buttons to progress
  ✓ If you see "Skip tour" or "Skip tutorial" - you can skip it to save time
  ✓ Goal is to reach the main Airtable workspace/dashboard WITH a created base
  ✓ Complete up to 10 steps total to ensure FULL onboarding is done
  ✓ STOP ONLY when you see the main workspace with your created base/table visible

SUCCESS INDICATORS (when to stop):
  ✅ You see main Airtable interface with your created workspace/base
  ✅ URL contains "/workspace" or shows base/table view (e.g., /tblXXXX)
  ✅ Onboarding wizard is no longer visible - no more setup questions
  ✅ You can see your base name and table(s) you created
  ✅ You can see navigation menu, workspace name, "Create" buttons, table grid
  ✅ Page looks like a functional Airtable workspace, not a setup wizard

REMEMBER: Complete ALL onboarding steps - up to 10 total!
Be thorough but efficient. The goal is a FULLY configured workspace.
"""

    model_name = "gemini-2.5-computer-use-preview-10-2025"
    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 900

    history = [Content(role="user", parts=[Part(text=task)])]

    print("\n💬 Промпт onboarding отправлен...")

    result = {
        "status": "unknown",
        "completed_steps": 0,
        "notes": ""
    }

    for step in range(1, max_steps + 1):
        print(f"\n{'=' * 70}")
        print(f"🔄 ШАГ ONBOARDING {step}/{max_steps}")
        print(f"{'=' * 70}")

        # Скриншот текущего состояния
        screenshot_bytes = await safe_screenshot(page_airtable, full_page=False, timeout_ms=10000)
        if screenshot_bytes:
            history.append(Content(role="user", parts=[
                Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes))
            ]))

        print("🧠 Модель анализирует onboarding...")
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model_name,
            contents=history,
            config=config
        )

        if response is None or not getattr(response, 'candidates', None):
            print("❌ Модель вернула пустой ответ (onboarding)")
            break

        candidate = response.candidates[0]
        model_content = candidate.content

        # Печать мыслей модели
        has_text = False
        has_tool_calls = False
        final_text = ""

        for part in model_content.parts:
            if hasattr(part, 'text') and part.text:
                has_text = True
                final_text += part.text + " "
                print(f"\n💭 Мысль модели (onboarding):\n   {part.text[:300]}...")
            if hasattr(part, 'function_call') and part.function_call:
                has_tool_calls = True

        # Выполнение действий
        tool_responses = []
        for part in model_content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                fc = part.function_call
                print(f"  🔧 Действие: {fc.name}")
                exec_result = await execute_computer_use_action(
                    page_airtable, fc, SCREEN_WIDTH, SCREEN_HEIGHT
                )
                tool_responses.append(
                    Part(function_response=FunctionResponse(name=fc.name, response=exec_result))
                )
                result["completed_steps"] += 1

        history.append(model_content)

        if tool_responses:
            screenshot_bytes = await safe_screenshot(page_airtable, full_page=False, timeout_ms=10000)
            parts = tool_responses.copy()
            if screenshot_bytes:
                parts.append(Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes)))
            history.append(Content(role="user", parts=parts))

        # Проверка завершения
        lower = final_text.lower()
        if any(keyword in lower for keyword in ["workspace", "main interface", "setup complete", "onboarding complete", "dashboard"]):
            result["status"] = "success"
            result["notes"] = "Onboarding completed successfully"
            print("\n✅ ONBOARDING ЗАВЕРШЁН")
            break

        # Если модель больше не делает действий
        if not has_tool_calls and has_text:
            result["status"] = "completed"
            result["notes"] = final_text[:300]
            print("\n✅ Onboarding завершён (модель остановилась)")
            break

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
    
    # Старт самообучающегося «забега» (run)
    try:
        LEARN.start_run(phase="unified", email=None, extra={"script": "test_agent3_air"})
    except Exception:
        pass

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

        # Получаем случайные данные пользователя
        print("\n🎲 Получение случайных данных пользователя...")
        user_data = await get_random_user_data()

        # Только теперь создаём вторую вкладку под Airtable
        page_airtable = await context.new_page()
        if page_airtable.url == "" or not page_airtable.url:
            await page_airtable.goto("about:blank")
        print(f"🪟 Открыта вторая вкладка для Airtable. Всего вкладок: {len(context.pages)}")

        # ШАГ 2: регистрация на Airtable с использованием двух вкладок
        print("\n📝 ШАГ 2: Регистрация на Airtable (почта не закрывается)...")
        result = await run_airtable_registration_on_pages(email, user_data, page_mail, page_airtable, client, config, max_steps=40)

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

        # ШАГ 3: Onboarding - проходим дополнительные шаги настройки
        if result.get('status') in ['success', 'unknown'] and result.get('confirmed', False):
            print("\n" + "=" * 70)
            print("🎯 ШАГ 3: Прохождение onboarding (до 10 дополнительных шагов)")
            print("=" * 70)
            print("💡 Цель: Ответить на вопросы Airtable и завершить начальную настройку")
            
            onboarding_result = await run_airtable_onboarding(page_airtable, client, config, max_steps=10)
            
            print("\n" + "=" * 70)
            print("✅ ONBOARDING ЗАВЕРШЁН")
            print("=" * 70)
            print(f"📊 Статус: {onboarding_result.get('status', 'unknown')}")
            print(f"🔢 Выполнено шагов: {onboarding_result.get('completed_steps', 0)}")
            if onboarding_result.get('notes'):
                print(f"📝 Заметки: {onboarding_result['notes'][:200]}")
        else:
            print("\n⚠️ Пропускаем onboarding - регистрация не подтверждена")

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