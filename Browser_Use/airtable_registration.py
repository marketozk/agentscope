"""
🧠 Автономная регистрация в Airtable (реферальная ссылка)
с использованием временной почты temp-mail.org — один Agent сам планирует и выполняет все шаги.

Что изменилось:
- ЕДИНЫЙ «Master Mission» промпт: агент сам решает, какие действия делать и когда, в каком порядке.
- Четкие цели/критерии успеха + подсказки по инструментам (селекторы, ожидания, проверки, ретраи).
- На выходе агент возвращает JSON-результат: статус, email, флаги подтверждения, заметки.

Основные фазы (внутри одной миссии):
  A) Открыть реферал Airtable → убедиться, что страница загрузилась.
  B) Получить временную почту на temp-mail.org (id="mail", дождаться, пока не исчезнет "Loading").
  C) Регистрация: заполнить форму (точный email, реалистичное имя, сложный пароль, чекбоксы); обработать ошибки.
  D) Если регистрация успешна → перейти в почту, найти письмо Airtable и нажать кнопку подтверждения.
  E) Финальная проверка на airtable.com (dashboard/меню) и возврат JSON.
"""
import asyncio
import os
import re
from pathlib import Path
from browser_use import Agent
from browser_use.browser.profile import BrowserProfile
from dotenv import load_dotenv
from datetime import datetime
from typing import Any, Optional, Tuple

# Импорт конфигурации с rate limiting
from config import (
    get_app_config,
    get_llm,
    get_profile_path,
    wait_for_rate_limit,
    register_api_request,
    print_api_stats
)

# Импорт вспомогательных функций
from browser_use_helpers import extract_email_from_result

# Загружаем переменные окружения
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Константы таймаутов и повторов
STEP_TIMEOUT = 240  # Таймаут одного запуска Agent.run(), сек (чуть больше для сетевых лагов)
RETRY_DELAY_SHORT = 3
RETRY_DELAY_MEDIUM = 5
RETRY_DELAY_LONG = 10
BROWSER_KEEP_ALIVE = 86400  # Держать браузер открытым (24 часа)


# ==================== ОБЕРТКА ДЛЯ LLM С RATE LIMIT ====================

class RateLimitedLLM:
    """Обертка вокруг LLM для контроля rate limit на каждый вызов"""
    
    def __init__(self, llm):
        self.llm = llm
        self._call_count = 0
    
    async def ainvoke(self, input: Any, config: Any = None, **kwargs) -> Any:
        """Обертка вокруг ainvoke с rate limit контролем"""
        # Ждем если нужно
        if not await wait_for_rate_limit():
            raise Exception("Достигнут дневной лимит API")
        
        # Регистрируем запрос
        register_api_request()
        self._call_count += 1
        
        print(f"   🔷 LLM вызов #{self._call_count}")
        
        # Делаем реальный вызов с правильными аргументами
        if config is not None:
            return await self.llm.ainvoke(input, config, **kwargs)
        else:
            return await self.llm.ainvoke(input, **kwargs)
    
    def __getattr__(self, name):
        """Проксируем все остальные атрибуты к оригинальному LLM"""
        return getattr(self.llm, name)


# ==================== УТИЛИТЫ ПАРСИНГА РЕЗУЛЬТАТОВ AGENT ====================

def _extract_text_from_action(action: Any) -> Optional[str]:
    """Попробовать извлечь основной текст из ActionResult.
    Приоритет: text -> extracted_content -> output -> None
    """
    for attr in ("text", "extracted_content", "output"):
        try:
            val = getattr(action, attr, None)
            if isinstance(val, str) and val.strip():
                return val
        except Exception:
            pass
    # Иногда текст может быть внутри dict-поля
    try:
        if isinstance(action, dict):
            for key in ("text", "extracted_content", "output"):
                val = action.get(key)
                if isinstance(val, str) and val.strip():
                    return val
    except Exception:
        pass
    return None


def parse_agent_result(result: Any) -> dict:
    """Структурированный парсер результата Agent с безопасным фолбэком.
    Возвращает словарь:
    {
      'is_done': bool|None,
      'success': bool|None,
      'error': str|None,
      'done_text': str|None,  # короткий итоговый текст
      'raw_text': str         # полный текст (fallback)
    }
    """
    parsed = {
        "is_done": None,
        "success": None,
        "error": None,
        "done_text": None,
        "raw_text": str(result) if result is not None else ""
    }

    try:
        all_results = getattr(result, "all_results", None)
        # Если есть список шагов
        if isinstance(all_results, (list, tuple)) and all_results:
            # Ищем финализирующее действие
            final = None
            for item in reversed(all_results):
                try:
                    if getattr(item, "is_done", False):
                        final = item
                        break
                except Exception:
                    continue
            if final is None:
                final = all_results[-1]

            # Заполняем поля
            try:
                parsed["is_done"] = getattr(final, "is_done", None)
            except Exception:
                pass
            try:
                parsed["success"] = getattr(final, "success", None)
            except Exception:
                pass
            try:
                err = getattr(final, "error", None)
                parsed["error"] = str(err) if err else None
            except Exception:
                pass
            # основной краткий текст
            parsed["done_text"] = _extract_text_from_action(final)
            # если не нашли короткий текст — можно попробовать ещё и из всего результата
            if not parsed["done_text"]:
                parsed["done_text"] = _extract_text_from_action(result) or None

    except Exception:
        # Любая ошибка парсинга — просто используем raw_text
        pass

    return parsed


class AirtableRegistration:
    """
    Полностью автономная регистрация в Airtable: один Agent получает почту (temp-mail.org),
    регистрируется, подтверждает email и возвращает структурированный результат.
    """

    def __init__(self, llm, referral_url: str = "https://airtable.com/invite/r/ovoAP1zR", max_retries: int = 5):
        self.llm = llm
        self.referral_url = referral_url
        self.max_retries = max_retries
        self.state = "INIT"
        self.temp_email: Optional[str] = None
        self.status: str = "unknown"
        self.confirmed: bool = False
        self.notes: str = ""
        self.agent: Optional[Agent] = None
        self.browser_profile = BrowserProfile(keep_alive=True)
        self.rate_limited_llm: Optional[RateLimitedLLM] = None

    def build_master_mission(self) -> str:
        """Единый промпт миссии: агент сам планирует и выполняет шаги."""
        return f"""
    ROLE: You are an autonomous web agent. Plan your own steps and act to complete the mission.
    BROWSER: You can open tabs, switch tabs, click, type, wait, run small JS, and use vision.

        MISSION GOAL:
          Create a new Airtable account using a reliable temporary email from temp-mail.org,
          then confirm the account via the confirmation email. Finish on Airtable with a verified/logged-in state.

        START HERE:
          1) Open the referral link in the FIRST tab and wait until fully loaded:
             {self.referral_url}

       EMAIL ACQUISITION (temp-mail.org):
        - Open a NEW TAB and navigate to https://temp-mail.org/en/
        - BEFORE reading email: verify page is fully loaded via JS: document.readyState === 'complete'. If not, wait 3s and check again (max 3 attempts).
        - Once readyState is 'complete', wait 20 seconds for the email field to resolve from "Loading" to a real email.
                - STRICT READ-ONLY: do NOT click, focus, type, select, hover, or press any copy buttons near the email field; do NOT use navigator.clipboard; do NOT trigger any UI events on the email widget. Only read values/attributes/text via JS.
                - Try multiple robust READ-ONLY ways to read the email (pick the first valid result that includes @):
                    1) JS: document.getElementById('mail')?.value
                    2) JS query: find any input likely holding email (READ ONLY)
                        [...document.querySelectorAll('#mail, input[type="email"], input[readonly], input[aria-label*="email" i], input[placeholder*="mail" i]')]
                           .map(e=>e.value||e.textContent||'').find(v=>v && v.includes('@'))
                    3) READ ONLY: check elements for attribute data-clipboard-text containing '@' (read attribute only, no clicks)
                        [...document.querySelectorAll('[data-clipboard-text]')].map(b=>b.getAttribute('data-clipboard-text')).find(v=>v && v.includes('@'))
                - If the value is still "Loading" or empty after the initial 20s wait → wait 5 more seconds and retry reading; repeat up to 3 times.
        - Store the email as TEMP_EMAIL. It must include @ and not be "test@example.com".
                - Stability: avoid full page reloads too frequently; prefer the site’s own refresh control for inbox. Do not reload more than once per 10s.
                - Before any action, quickly check document.readyState via JS and wait a short moment if it's "loading".
                - Screenshot caution: during the first 5–8 seconds on temp-mail, avoid any non-essential state captures/screenshots; prefer direct JS reads to minimize overhead.
                - IMPORTANT: Once you obtain a valid TEMP_EMAIL, keep it. If the page later shows an empty box, DO NOT discard it — reuse the stored TEMP_EMAIL unless the registration rejects it.
                - Do NOT regenerate a new email unless you detect an explicit rejection/ban/"already used" during registration.

        REGISTRATION ON AIRTABLE:
          - Switch back to the Airtable tab.
          - Fill the Email field with EXACTLY TEMP_EMAIL. First clear the field; then type character by character.
          - Fill Full Name with a realistic two-word name (e.g., Emma Williams). Do NOT use placeholders.
          - Create a strong password (letters+numbers+special): e.g., MyP@ssw0rd456.
          - Check all required checkboxes (terms/privacy).
                    - Click "Create account" (or similarly named primary submit button).
                    - AFTER CLICK ANTI-LOOP CHECK:
                        * If the button becomes disabled, shows a spinner, or the page navigates/changes content — DO NOT click it again.
                        * Confirm state change via URL/title or appearance of new elements (e.g., welcome/onboarding/dashboard).
                        * If you clicked and nothing changes for ~5-8 seconds, re-evaluate: check for inline errors or progressed state in another area.
                        * Never click the same submit button more than 2 times without a clear state change.
          - If you see an email-related error (e.g., domain blocked or already exists), go back to temp-mail tab,
            generate a NEW email (refresh or reload), verify it's different, and retry the registration with the new email.
            Limit total email-retry cycles to {self.max_retries}.
                    - Time cap: spend no more than ~90 seconds on the registration phase. If you observe clear progress (redirect to onboarding/welcome/workspace), stop clicking and proceed to confirmation email step.

        CONFIRMATION EMAIL CHECKPOINT:
          - Only after successful account creation, go to the temp-mail tab.
                    - Prefer using the inbox refresh button on the page (not full browser reload); at most once per 10s.
                    - Wait 3-5 seconds and look for an email from Airtable (sender contains "airtable").
          - Open the email and click the main confirmation link/button.
          - Switch to the new tab (Airtable) and verify confirmation (success text, dashboard, or being logged in).

        FINAL VERIFICATION ON AIRTABLE:
          - Ensure you are on airtable.com (not signup page) and see dashboard/workspace or user menu.

        IMPORTANT EXECUTION NOTES:
          - Always verify visible text and URL before deciding.
          - Prefer stable selectors: id, name, placeholder, label text.
          - For temp-mail, use id=mail; never return the word "Loading" as the email.
                    - Before submit, verify the Email field equals TEMP_EMAIL (not test@example.com).
          - Keep a short memory of recent actions. Avoid repeating the exact same click more than 2 times unless URL/title or key DOM changed.
                    - Use short waits (2-5s) as needed; if no state change is detected — stop repeating and choose a different action.
          - Timeout hygiene: if a tab/page seems frozen or unresponsive for ~10s, switch to another tab and back, re-check readyState, and continue; avoid infinite reload loops.
          - If something fails, explain briefly and continue to the next best step.

        OUTPUT FORMAT (MANDATORY):
          At the very end, call done(text='{{"status":"success|partial|failed","email":"<TEMP_EMAIL>","confirmed":true|false,"notes":"..."}}').
          - status=success: logged in or verified on Airtable
          - status=partial: account created but email not confirmed
          - status=failed: could not create account
          - email: the TEMP_EMAIL actually used in the form
          - confirmed: true only if verification succeeded on Airtable site
          - notes: short reason/explanation
        """

    def _parse_final_json(self, text: str) -> Tuple[Optional[dict], Optional[str]]:
        """Пытаемся извлечь JSON-объект из итогового текста агента. Возвращаем (data, raw)."""
        if not text:
            return None, None
        raw = text.strip()
        # Попробуем найти JSON фигурные скобки
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return None, raw
        json_str = m.group(0)
        try:
            import json
            data = json.loads(json_str)
            return data, raw
        except Exception:
            return None, raw

    async def run_agent_with_rate_limit(self, timeout=STEP_TIMEOUT):
        return await asyncio.wait_for(self.agent.run(), timeout=timeout)

    async def run(self):
        print("\n🚀 Запуск автономной регистрации Airtable (единая миссия)")
        print("=" * 50)
        print(f"⚙️  Настройки: retries={self.max_retries}, timeout={STEP_TIMEOUT}с")
        print("=" * 50)

        try:
            # Оборачиваем LLM для строгого контроля API вызовов
            self.rate_limited_llm = RateLimitedLLM(self.llm)

            # Создаём Agent с master-миссией
            self.agent = Agent(
                task=self.build_master_mission(),
                llm=self.rate_limited_llm,
                browser_profile=self.browser_profile,
                use_vision=True,
                max_failures=15,
            )

            # Один запуск – агент внутри сам планирует и действует
            result = await self.run_agent_with_rate_limit()

            parsed = parse_agent_result(result)
            main_text = (parsed.get("done_text") or parsed.get("raw_text") or "").strip()
            print(f"\n📦 Итог от агента (усечено): {main_text[:400]}...")

            # Пытаемся вытащить JSON-результат
            data, _ = self._parse_final_json(main_text)
            if data:
                self.status = str(data.get("status", "unknown")).lower()
                self.temp_email = data.get("email") or extract_email_from_result(main_text)
                self.confirmed = bool(data.get("confirmed", False))
                self.notes = str(data.get("notes", ""))
            else:
                # Фолбэк: по ключевым словам
                up = main_text.upper()
                self.temp_email = extract_email_from_result(main_text)
                if "SUCCESS" in up or "LOGGED_IN" in up or "VERIFIED" in up:
                    self.status = "success"
                    self.confirmed = True if "VERIFIED" in up else False
                elif "PARTIAL" in up or "ACCOUNT" in up:
                    self.status = "partial"
                else:
                    self.status = "failed"
                self.notes = "fallback parse"

            print("\n" + "=" * 50)
            print("✅ Миссия завершена")
            print("=" * 50)
            print(f"📧 Email: {self.temp_email}")
            print(f"📊 Статус: {self.status}, confirmed={self.confirmed}")
            if self.notes:
                print(f"📝 Notes: {self.notes[:200]}")
            total_llm_calls = getattr(self.rate_limited_llm, "_call_count", "n/a")
            print(f"📈 Внутренних LLM вызовов: {total_llm_calls}")
            print("=" * 50)

            # Сохраняем результат
            self.save_credentials()

            # Держим браузер открытым, чтобы можно было глазами проверить финальное состояние
            print(f"\n💤 Браузер остается открытым на {BROWSER_KEEP_ALIVE // 3600} часов")
            print("   Нажмите Ctrl+C для завершения...")
            await asyncio.sleep(BROWSER_KEEP_ALIVE)

        except KeyboardInterrupt:
            print("\n👋 Прервано пользователем")
            raise
        except asyncio.TimeoutError:
            print(f"\n⏱️  Таймаут на этапе {self.state}")
            raise
        except Exception as e:
            print(f"\n❌ Ошибка на этапе {self.state}: {e}")
            raise
        finally:
            if self.agent:
                print("\n🧹 Закрываем браузер...")
                try:
                    await self.agent.close()
                    print("✅ Браузер закрыт")
                except Exception as e:
                    print(f"⚠️  Ошибка при закрытии браузера: {e}")
    
    def save_credentials(self):
        """Сохранение результата в файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"airtable_registration_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== РЕЗУЛЬТАТ РЕГИСТРАЦИИ AIRTABLE ===\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Email: {self.temp_email}\n")
            f.write(f"Статус: {self.status}\n")
            f.write(f"Подтверждено: {self.confirmed}\n")
            if self.notes:
                f.write(f"Заметки: {self.notes}\n")
            f.write("=" * 40 + "\n")
        
        print(f"\n💾 Данные сохранены в файл: {filename}")


async def main():
    # Инициализация конфигурации
    try:
        config = get_app_config()
        config.print_config()
        
        llm = get_llm()
        profile_path = get_profile_path()
    except ValueError as e:
        print(f"\n❌ Ошибка конфигурации: {e}")
        return
    
    # Проверка дневного лимита (без регистрации запроса здесь)
    can_run = await wait_for_rate_limit()
    if not can_run:
        print("⛔ Достигнут лимит API. Попробуйте позже.")
        return
    
    # Запускаем регистрацию с retry механизмом (100 попыток для обработки ошибок валидации)
    registration = AirtableRegistration(llm, max_retries=100)
    
    try:
        await registration.run()
    except KeyboardInterrupt:
        print("\n👋 Завершение работы...")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
    finally:
        # Показываем статистику
        print_api_stats()


if __name__ == "__main__":
    asyncio.run(main())
