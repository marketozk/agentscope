"""
🧠 Автономная регистрация в Airtable с ДВУМЯ браузерами в распоряжении
Агент САМ решает, как использовать браузеры для выполнения задачи:
- Браузер 1 и Браузер 2 доступны одновременно
- Агент распределяет задачи между ними (email, регистрация, подтверждение)
- Может переключаться между браузерами, открывать вкладки, кликать — полная свобода
- Цель: зарегистрироваться на Airtable и подтвердить email
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
from pydantic import BaseModel, Field

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

# Константы
STEP_TIMEOUT = 180
BROWSER_KEEP_ALIVE = 86400


# ==================== СТРУКТУРИРОВАННАЯ СХЕМА ВЫВОДА ====================

class RegistrationResult(BaseModel):
    """Структурированный результат регистрации для агента"""
    status: str = Field(
        description="Статус регистрации: 'success', 'partial', или 'failed'"
    )
    email: str = Field(
        description="Временная почта, использованная для регистрации (например: wayedip717@gamegta.com)"
    )
    confirmed: bool = Field(
        description="Подтверждена ли почта через письмо от Airtable"
    )
    notes: str = Field(
        description="Краткое объяснение того, что произошло"
    )


# ==================== ОБЕРТКА ДЛЯ LLM С RATE LIMIT ====================

class RateLimitedLLM:
    """Обертка вокруг LLM для контроля rate limit на каждый вызов"""
    
    def __init__(self, llm):
        self.llm = llm
        self._call_count = 0
    
    async def ainvoke(self, input: Any, config: Any = None, **kwargs) -> Any:
        """Обертка вокруг ainvoke с rate limit контролем"""
        if not await wait_for_rate_limit():
            raise Exception("Достигнут дневной лимит API")
        
        register_api_request()
        self._call_count += 1
        
        print(f"   🔷 LLM вызов #{self._call_count}")
        
        if config is not None:
            return await self.llm.ainvoke(input, config, **kwargs)
        else:
            return await self.llm.ainvoke(input, **kwargs)
    
    def __getattr__(self, name):
        return getattr(self.llm, name)


# ==================== ПАРСИНГ РЕЗУЛЬТАТОВ ====================

def _extract_text_from_action(action: Any) -> Optional[str]:
    """Извлечь текст из ActionResult"""
    for attr in ("text", "extracted_content", "output"):
        try:
            val = getattr(action, attr, None)
            if isinstance(val, str) and val.strip():
                return val
        except Exception:
            pass
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
    """Структурированный парсер результата Agent"""
    parsed = {
        "is_done": None,
        "success": None,
        "error": None,
        "done_text": None,
        "raw_text": str(result) if result is not None else ""
    }

    try:
        all_results = getattr(result, "all_results", None)
        if isinstance(all_results, (list, tuple)) and all_results:
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
            
            parsed["done_text"] = _extract_text_from_action(final)
            if not parsed["done_text"]:
                parsed["done_text"] = _extract_text_from_action(result) or None

    except Exception:
        pass

    return parsed


class DualBrowserRegistration:
    """Регистрация: агент сам управляет двумя браузерами"""

    def __init__(self, llm, referral_url: str = "https://airtable.com/invite/r/ovoAP1zR"):
        self.llm = llm
        self.referral_url = referral_url
        self.temp_email: Optional[str] = None
        self.status: str = "unknown"
        self.confirmed: bool = False
        self.notes: str = ""
        self.rate_limited_llm: Optional[RateLimitedLLM] = None

    def build_master_mission(self) -> str:
        """Единая миссия: агент сам решает, как использовать два браузера"""
        return f"""

MISSION GOAL:
  Register a new Airtable account using {self.referral_url} and a temporary email from temp-mail.org,
  then confirm the account via email. 

NOTE: Two tabs are already open for you:
  - Tab 1: https://temp-mail.org/en/ (temporary email service)
  - Tab 2: {self.referral_url} (Airtable registration page)

CRITICAL WORKFLOW WITH TIMING:
  📧 PHASE 1: GET TEMPORARY EMAIL (Tab 1)
  -------------------------------------------
  - STEP 1: Switch to temp-mail tab (Tab 1)
  - STEP 2: WAIT 20 seconds for page to fully load and email to generate
  - STEP 3: FIND the email address on the page
    * Try method 1: Extract text from the email display area
    * Try method 2: Use JavaScript: document.querySelector('#mail').textContent
    * Try method 3: Use vision to read the email from screenshot
  - STEP 4: MEMORIZE the exact email (write: "Temporary email obtained: xyz@domain.com")
  - STEP 5: VERIFY you have the email before proceeding
  
  📝 PHASE 2: REGISTER ON AIRTABLE (Tab 2)
  -------------------------------------------
  - STEP 6: Switch to Airtable registration tab (Tab 2)
  - STEP 7: WAIT 5 seconds for registration form to fully load
  - STEP 8: Fill the registration form CAREFULLY:
    * Email field: Type the EXACT temp-mail address from Phase 1 (DO NOT INVENT!)
    * Full Name field: Generate realistic name (e.g., "Sarah Mitchell")
    * Password field: Generate strong password (e.g., "SecureP@ss2024!")
    * Checkboxes: Check all required boxes (Terms of Service, Privacy Policy)
  
  - STEP 9: BEFORE submitting - DOUBLE CHECK:
    * Email field contains the correct temp-mail address
    * Name and password are filled
    * All checkboxes are checked
  
  - STEP 10: Click "Create account" button ONCE
  - STEP 11: WAIT 10 seconds and observe the result:
    * Success: URL changed to dashboard or verification page
    * Loading: Button disabled with spinner → wait 10 more seconds
    * Error: Read error message and decide next action
  
  ✉️ PHASE 3: CONFIRM EMAIL (Tab 1)
  -------------------------------------------
  - STEP 12: Switch back to temp-mail tab (Tab 1)
  - STEP 13: WAIT 30 seconds for confirmation email to arrive
  - STEP 14: Look for email from Airtable with subject about verification
  - STEP 15: Open the email from Airtable
  - STEP 16: Find and click the confirmation/verification link in the email
  - STEP 17: WAIT 5 seconds for confirmation to process
  - STEP 18: Check if account is now verified (look for success message)

ANTI-LOOP PROTECTION:
  If you repeat the same action 3+ times without progress:
  ⛔ STOP and ANALYZE:
    - What am I trying to do?
    - What's blocking me?
    - Did my last action succeed? (Check URL, page state, elements)
  
  🔄 TRY DIFFERENT APPROACH:
    - Email not found on temp-mail? → Refresh page or get new email
    - Registration button not working? → Check for inline error messages
    - Email domain blocked by Airtable? → Go back, get NEW email with different domain
    - Confirmation email not arriving? → Wait longer (up to 60 seconds)
    - Action succeeded but system says "Failure"? → Ignore verdict, check actual page state
  
  ❌ NEVER:
    - Click same button more than 3 times
    - Fill same field more than 2 times (if filled successfully, move on!)
    - Wait indefinitely (max wait: 60 seconds for any step)
  
  ✅ WHEN STUCK:
    1. PAUSE (stop current action)
    2. OBSERVE (read current page state, URL, errors)
    3. DECIDE (what's the next best action?)
    4. EXECUTE (try new approach)

OUTPUT FORMAT (MANDATORY):
  When task is complete, you MUST return structured data in this exact format:
  {{
    "status": "success|partial|failed",
    "email": "<the-temp-email-you-used>",
    "confirmed": true|false,
    "notes": "Brief explanation of what happened"
  }}
  
  Examples:
  - Full success: {{"status":"success","email":"user123@gamegta.com","confirmed":true,"notes":"Account created and verified"}}
  - Partial success: {{"status":"partial","email":"user456@tempmail.com","confirmed":false,"notes":"Account created but email not yet confirmed"}}
  - Failure: {{"status":"failed","email":"user789@mail.tm","confirmed":false,"notes":"Email domain blocked by Airtable"}}

"""

    async def run_agent_with_timeout(self, agent: Agent, timeout: int) -> Any:
        return await asyncio.wait_for(agent.run(), timeout=timeout)

    async def run(self):
        print("\n🚀 Запуск регистрации: агент управляет двумя браузерами")
        print("=" * 60)

        try:
            self.rate_limited_llm = RateLimitedLLM(self.llm)

            # Создаём агента с доступом к ДВУм браузерам одновременно
            # Agent в browser-use может работать с несколькими browser_context
            profile_1 = BrowserProfile(
                keep_alive=True,
                disable_security=False,  # Оставляем security для надёжности
            )
            
            # Начальные действия: автоматически открываем нужные вкладки
            initial_actions = [
                {'navigate': {'url': 'https://temp-mail.org/en/', 'new_tab': True}},    # Вкладка 1: temp-mail
                {'navigate': {'url': self.referral_url, 'new_tab': True}},              # Вкладка 2: Airtable
            ]
            
            # Создаём timestamp для сохранения истории
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            conversation_path = Path(f"logs/airtable_registration_{timestamp}.json")
            conversation_path.parent.mkdir(exist_ok=True)
            
            # Генерируем уникальный task_id для трекинга
            task_id = f"airtable_reg_{timestamp}"
            
            print("\n⚙️  Настройки агента:")
            print(f"   📝 Task ID: {task_id}")
            print(f"   💾 История сохранится в: {conversation_path}")
            print(f"   🎬 GIF анимация: logs/registration_{timestamp}.gif")
            print(f"   👁️  Vision API: включен (auto)")
            print(f"   ⏱️  Таймаут шага: {STEP_TIMEOUT}s")
            print(f"   🔄 Макс. действий за шаг: 15")
            print(f"   ❌ Макс. ошибок: 20")
            
            # Основной агент с оптимальными параметрами
            agent = Agent(
                task=self.build_master_mission(),
                llm=self.rate_limited_llm,
                browser_profile=profile_1,
                
                # === ОСНОВНЫЕ НАСТРОЙКИ ===
                use_vision=True,                        # Включаем Vision API для скриншотов
                max_failures=20,                        # Больше попыток перед сдачей
                initial_actions=initial_actions,        # Сразу откроет обе вкладки
                
                # === СТРУКТУРИРОВАННЫЙ ВЫВОД ===
                output_model_schema=RegistrationResult, # Схема для валидации результата
                
                # === ТАЙМИНГИ ===
                step_timeout=STEP_TIMEOUT,              # 180 секунд на шаг
                llm_timeout=60,                         # 60 секунд на LLM запрос
                
                # === ОПТИМИЗАЦИЯ РАБОТЫ ===
                max_actions_per_step=15,                # Больше действий за один шаг
                use_thinking=True,                      # Включить рассуждения (лучшее качество)
                flash_mode=False,                       # Не используем быстрый режим
                
                # === ЛОГИРОВАНИЕ И ОТЛАДКА ===
                save_conversation_path=str(conversation_path),  # Сохранить полную историю
                generate_gif=f"logs/registration_{timestamp}.gif",  # GIF анимация процесса
                task_id=task_id,                        # ID для трекинга
                source="airtable_registration_dual_browser",  # Источник для аналитики
                
                # === ДОПОЛНИТЕЛЬНЫЕ ФИЧИ ===
                include_recent_events=True,             # Включить события браузера для контекста
                calculate_cost=True,                    # Подсчитывать стоимость токенов
                display_files_in_done_text=True,        # Показывать файлы в done()
                final_response_after_failure=True,      # Давать финальный ответ даже при провале
                
                # === ДЕТАЛИЗАЦИЯ ===
                vision_detail_level='high',             # Высокая детализация для Vision API
                include_attributes=['data-testid', 'name', 'id', 'type'],  # Важные HTML атрибуты
            )
            
            print("\n✅ Вкладки автоматически открыты:")
            print("   📧 Tab 1: https://temp-mail.org/en/")
            print(f"   📝 Tab 2: {self.referral_url}")
            print("   🤖 Агент начинает работу с готовыми вкладками...\n")

            result = await self.run_agent_with_timeout(agent, timeout=STEP_TIMEOUT)
            parsed = parse_agent_result(result)
            text = (parsed.get("done_text") or parsed.get("raw_text") or "").strip()

            print(f"\n📦 Результат агента (усечено): {text[:400]}")

            # Попытка извлечь структурированный результат
            try:
                # Если агент вернул структурированный результат (RegistrationResult)
                if hasattr(result, 'model_output') and result.model_output:
                    structured_output = result.model_output
                    self.status = str(structured_output.status).lower()
                    self.temp_email = structured_output.email
                    self.confirmed = bool(structured_output.confirmed)
                    self.notes = str(structured_output.notes)
                    print("\n✅ Получен структурированный результат от агента")
                else:
                    # Fallback: парсим JSON из текста
                    json_match = re.search(r'\{[\s\S]*\}', text)
                    if json_match:
                        import json
                        data = json.loads(json_match.group(0))
                        self.status = str(data.get("status", "unknown")).lower()
                        self.temp_email = data.get("email") or extract_email_from_result(text)
                        self.confirmed = bool(data.get("confirmed", False))
                        self.notes = str(data.get("notes", ""))
                        print("\n⚠️  Структурированный результат извлечён из JSON")
            except Exception as e:
                print(f"\n⚠️  Не удалось извлечь структурированный результат: {e}")
                # Fallback парсинг
                pass
            
            # Дополнительный fallback если ничего не нашли
            if not self.temp_email:
                self.temp_email = extract_email_from_result(text)
            
            if not self.status or self.status == "unknown":
                up = text.upper()
                if "SUCCESS" in up or "VERIFIED" in up:
                    self.status = "success"
                    self.confirmed = "VERIFIED" in up or "CONFIRMED" in up
                elif "PARTIAL" in up:
                    self.status = "partial"
                else:
                    self.status = "failed"
                self.notes = self.notes or "fallback parse"

            print("\n" + "=" * 60)
            print("✅ Миссия завершена")
            print("=" * 60)
            print(f"📧 Email: {self.temp_email}")
            print(f"📊 Статус: {self.status}, confirmed={self.confirmed}")
            if self.notes:
                print(f"📝 Notes: {self.notes[:200]}")
            total_llm = getattr(self.rate_limited_llm, "_call_count", "n/a")
            print(f"📈 Всего LLM вызовов: {total_llm}")
            
            # Показать стоимость если рассчитывалась
            if hasattr(result, 'cost_info') and result.cost_info:
                print(f"💰 Стоимость: {result.cost_info}")
            
            print("=" * 60)

            self.save_credentials()

            # Держим браузер открытым
            print(f"\n💤 Браузер остается открытым на {BROWSER_KEEP_ALIVE // 3600} часов")
            print("   Нажмите Ctrl+C для завершения...")
            await asyncio.sleep(BROWSER_KEEP_ALIVE)
            await agent.close()

        except KeyboardInterrupt:
            print("\n👋 Прервано пользователем")
            self.save_credentials()
            raise
        except Exception as e:
            print(f"\n❌ Критическая ошибка: {e}")
            self.save_credentials()
            raise

    def save_credentials(self):
        """Сохранение результата в файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"airtable_registration_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== РЕЗУЛЬТАТ РЕГИСТРАЦИИ AIRTABLE (DUAL BROWSER) ===\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Email: {self.temp_email}\n")
            f.write(f"Статус: {self.status}\n")
            f.write(f"Подтверждено: {self.confirmed}\n")
            if self.notes:
                f.write(f"Заметки: {self.notes}\n")
            f.write("=" * 50 + "\n")
        
        print(f"\n💾 Данные сохранены в файл: {filename}")


async def main():
    # Создаём директорию для логов
    Path("logs").mkdir(exist_ok=True)
    
    try:
        config = get_app_config()
        config.print_config()
        
        llm = get_llm()
        profile_path = get_profile_path()
    except ValueError as e:
        print(f"\n❌ Ошибка конфигурации: {e}")
        return
    
    can_run = await wait_for_rate_limit()
    if not can_run:
        print("⛔ Достигнут лимит API. Попробуйте позже.")
        return
    
    registration = DualBrowserRegistration(llm)
    
    try:
        await registration.run()
    except KeyboardInterrupt:
        print("\n👋 Завершение работы...")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
    finally:
        print_api_stats()


if __name__ == "__main__":
    asyncio.run(main())
