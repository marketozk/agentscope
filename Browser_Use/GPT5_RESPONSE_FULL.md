# 🧠 ПОЛНЫЙ ОТВЕТ GPT-5 PRO: СИСТЕМА САМООБУЧЕНИЯ

**Дата:** 2025-10-19 02:10:17  
**Модель:** gpt-5-pro  
**Всего токенов:** 41,044

---

Ниже — полностью совместимая «надстройка» для самообучения, которую можно «вставить» в ваш существующий test_agent3_air.py, не переписывая архитектуру и не меняя интерфейсов (включая register_airtable_account, если вы её вызываете снаружи). Она:

- Сохраняет телеметрию шагов (время, успех/ошибку, домен, стратегию);
- Хранит и агрегирует опыт между запусками (SQLite, без внешних зависимостей);
- Автоматически подбирает параметры (стратегии navigate, таймауты, порядок извлечения ссылок/почты);
- Балансирует exploitation/exploration через epsilon-greedy;
- Встроена минимальными правками в конкретные точки (navigate, switch tabs, извлечение email и verification link, safe_screenshot, финальный результат).

## Часть 1. Архитектура самообучения

### Хранилище опыта (SQLite, файл selflearn_airtable.sqlite3):

- **runs**: один запуск/регистрация (phase: unified/email/registration/onboarding, статус, confirmed, время).
- **actions**: пошаговая телеметрия (navigate/click/.../custom), домен, URL, параметры, время, успех/ошибка.
- **params**: статистика параметров/стратегий (nav_strategy, timeouts, order методов извлечения и т.д.) с учетами n, success, tot_ms; на основе этого выбираются значения на следующих запусках.

### Политика выбора параметров:

- Epsilon-greedy для дискретных стратегий (пример: nav_strategy ∈ {domcontentloaded, load, minimal}).
- Ранжирование порядка методов (rank_methods) по успешности/скорости.
- Авто-подбор численных параметров (timeouts), также через epsilon-greedy (choose_numeric).

### Точки логирования:

- execute_computer_use_action: navigate (стратегия + ожидания), switch_to_* (ожидание после bring_to_front).
- safe_screenshot (таймаут).
- extract_email_from_tempmail_page (сколько ждать до появления email, порядок методов).
- extract_verification_link_from_page (порядок методов).
- save_registration_result (финал).

### Баланс exploitation/exploration:

- Стратегии и таймауты выбираются через LEARN.choose_*: чаще используется лучшее наработанное, но с вероятностью epsilon берётся альтернативный вариант.
- Epsilon можно регулировать через переменную окружения AUTOLEARN_EPS (по умолчанию 0.12).

---

## Часть 2. Код: ядро самообучения и точечные вставки

### Шаг 2.1. Добавьте блок «SELF-LEARNING CORE» сразу после импортов

(после всех import …, до остального кода):

```python
# ==================== SELF-LEARNING CORE (drop-in) ====================
import sqlite3
import random
import atexit
from time import perf_counter
from contextlib import contextmanager

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
```

### Шаг 2.2. Инструментируем safe_screenshot

(минимальная правка: динамический таймаут + лог):

Найдите функцию safe_screenshot и замените её тело на:

```python
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
```

### Шаг 2.3. Инструментируем и «обучаем» navigate и switch_to_* в execute_computer_use_action

Внутри execute_computer_use_action:
- В ветке action == "switch_to_mail_tab" и "switch_to_airtable_tab" замените стабильную паузу 1.0 сек на адаптивную.
- В ветке action == "navigate" используйте auto-выбор стратегии и таймаутов.

Фрагменты для вставки:

**1) В блоке "switch_to_mail_tab" (перед return):**

```python
# вместо: await asyncio.sleep(1.0)
tab_wait_ms = LEARN.choose_numeric("tab_switch_wait_ms", "tabs", [300, 600, 800, 1000, 1200, 1500], default=1000)
t0 = perf_counter()
await asyncio.sleep(tab_wait_ms / 1000)
LEARN.log_action("switch_tab", _domain_from_url(page_mail.url), page_mail.url, {"target": "mail", "wait_ms": tab_wait_ms}, True, int((perf_counter()-t0)*1000))
LEARN.record_param_outcome("tab_switch_wait_ms", "tabs", tab_wait_ms, True, tab_wait_ms)
```

**2) Аналогично в "switch_to_airtable_tab":**

```python
tab_wait_ms = LEARN.choose_numeric("tab_switch_wait_ms", "tabs", [300, 600, 800, 1000, 1200, 1500], default=1000)
t0 = perf_counter()
await asyncio.sleep(tab_wait_ms / 1000)
LEARN.log_action("switch_tab", _domain_from_url(page_airtable.url), page_airtable.url, {"target": "airtable", "wait_ms": tab_wait_ms}, True, int((perf_counter()-t0)*1000))
LEARN.record_param_outcome("tab_switch_wait_ms", "tabs", tab_wait_ms, True, tab_wait_ms)
```

**3) В ветке action == "navigate" замените «жёсткий» порядок стратегий на обучаемый:**

Найдите место, где сейчас:
- ждём 1000 мс,
- пытаемся domcontentloaded → load → minimal,
- затем ждём доп. время и ждём селекторы.

Замените этот кусок на:

```python
elif action == "navigate":
    url = args.get("url", "")
    if not is_allowed_url(url):
        return {"success": False, "message": f"Navigation blocked by policy: {url}", "url": page.url}
    domain = _domain_from_url(url)
    # Выбор стартовой стратегии на основе опыта
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
```

### Шаг 2.4. Извлечение email: адаптивное ожидание + логика порядка методов

В функции extract_email_from_tempmail_page сделаем:
- Обучаемое время «активного ожидания» появления email;
- Логирование успешности каждого метода;
- Возможность переставлять приоритет методов (по факту здесь основное — JS поиск, потом regex/селекторы).

Замените тело функции на:

```python
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
```

### Шаг 2.5. Извлечение verification link: обучаемый порядок методов + логирование

Замените тело extract_verification_link_from_page на:

```python
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
```

### Шаг 2.6. Регистрация финального результата

Внутри save_registration_result добавьте запись результата в «runs» (это завершение текущего запуска):

В конец функции save_registration_result (перед print сохранения файла или сразу после) добавьте:

```python
# Сообщаем LEARN об итогах этого запуска
try:
    LEARN.finish_run(status=status, confirmed=bool(confirmed), notes=notes or "")
except Exception:
    pass
```

### Шаг 2.7. Старт запуска (run start)

В начале объединённой функции main_airtable_registration_unified (после заголовочных принтов и перед загрузкой ключа/инициализацией клиента) добавьте:

```python
# Старт самообучающегося «забега» (run)
try:
    LEARN.start_run(phase="unified", email=None, extra={"script": "test_agent3_air"})
except Exception:
    pass
```

Аналогично можно добавить start_run в main_airtable_registration (классическая двухэтапная версия), если вы её используете.

### Шаг 2.8. (Опционально) мелкая оптимизация ввода текста

В type_text_at внутри execute_computer_use_action замените фиксированную задержку 50 мс на обучаемую:

```python
delay_ms = LEARN.choose_numeric("type_text_delay_ms", "typing", [20, 35, 50, 75], default=50)
await page.keyboard.type(text, delay=delay_ms)
LEARN.record_param_outcome("type_text_delay_ms", "typing", delay_ms, True, len(text) * delay_ms)
```

---

## Часть 3. Где и как внедрить изменения в test_agent3_air.py

- После импортов вставьте блок SELF-LEARNING CORE (Шаг 2.1).
- Замените реализацию safe_screenshot (Шаг 2.2).
- Патчите execute_computer_use_action:
  - В блоках switch_to_mail_tab и switch_to_airtable_tab — вставьте адаптивный tab_wait (Шаг 2.3, пункты 1 и 2).
  - В блоке navigate — замените логику выбора стратегии на обучаемую (Шаг 2.3, пункт 3).
  - (Опционально) в type_text_at — обучаемый delay (Шаг 2.8).
- Замените тело extract_email_from_tempmail_page на обучаемую версию (Шаг 2.4).
- Замените тело extract_verification_link_from_page на обучаемую версию (Шаг 2.5).
- В save_registration_result добавьте LEARN.finish_run (Шаг 2.6).
- В main_airtable_registration_unified добавьте LEARN.start_run в самом начале (Шаг 2.7).
- Больше ничего менять не нужно. Интерфейсы функций не меняются, внешние вызовы остаются прежними.

---

## Часть 4. Как агент будет адаптироваться и улучшаться с каждым запуском

- Первые 1–2 запуска выполняют «разведку» (epsilon-greedy пробует разные стратегии).
- После каждого действия (navigate, selector_wait, screenshot, extract_email, extract_verification_link, switch tabs, typing) логируются:
  - success/fail;
  - длительность;
  - домен/URL;
  - выбранные параметры (стратегия/таймаут/метод).
- На следующем запуске:
  - Для каждого домена и операции выбирается «лучшее» наработанное значение с вероятностью 1-epsilon;
  - С вероятностью epsilon пробуется альтернатива (чтобы не «застыть» и адаптироваться к изменениям сайтов).
- Примеры эффекта:
  - Если для temp-mail чаще всего email появляется за 12–15 сек — параметр email_initial_wait_ms сойдётся к 12000–15000.
  - Если navigate(domcontentloaded) для airtable часто падает — будет чаще выбираться load или minimal, и порядок стратегий изменится.
  - Если извлечение verification link чаще удаётся через JS ссылки, этот метод станет приоритетным.
  - Время ожидания после переключения вкладок «пристреляется» (без излишней задержки, но достаточно для рендеринга).

---

## Часть 5. Рекомендации для масштабирования и улучшений

### Безопасность/валидация данных:

- Хранить DB в отдельной папке (например, ./.selflearn/).
- Добавить бэкап JSON со сводными метриками в конце каждого run (необязательно).

### Визуализация:

- Простая диагностика: запросы к SQLite (sqlite3 selflearn_airtable.sqlite3), чтобы смотреть лучшие параметры и истории.

### Дополнительные параметры для обучения (при желании):

- Время ожидания после navigate перед попыткой submit.
- Время ожидания email от Airtable (15–30 сек).
- Политика повторов при неуспешном клике (кол-во попыток 1–3).

### Регулировка epsilon:

- Переменная окружения AUTOLEARN_EPS (например, 0.12 → 0.05 после нескольких стабильных прогонов).

### Адаптация под другие сервисы:

- Контекстом для ключей параметров служит домен. Добавить новые домены — просто.

---

## Итог

- Все изменения добавляют «тонкий слой» самообучения и телеметрии в точках, где это реально влияет на стабильность: стратегия навигации, таймауты, порядок методов извлечения, ожидание после переключения вкладок и ввод.
- Архитектура и внешний интерфейс функций не изменяются.
- Система начнет накапливать знания с первого запуска и будет всё лучше выбирать параметры для temp-mail и Airtable, повышая надёжность и скорость.
