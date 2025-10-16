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


class EmailParserResult(BaseModel):
    """Результат парсинга email с temp-mail.org"""
    email: str = Field(
        description="Полученный временный email адрес (например: user123@gamegta.com)"
    )
    success: bool = Field(
        description="Успешно ли получен email"
    )
    notes: str = Field(
        description="Дополнительная информация о процессе"
    )


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

    def build_email_parser_mission(self) -> str:
        """ШАГ 1: Миссия для парсинга email с temp-mail.org"""
        return """
MISSION: Get temporary email from temp-mail.org

YOUR TASK:
  You need to extract a temporary email address from https://temp-mail.org/en/

CRITICAL STEPS:
  1. WAIT 20 seconds after page loads (email needs time to generate)
  2. LOCATE the email address on the page using one of these methods:
     - Method A: Extract text from the main email display area
     - Method B: Use JavaScript: document.querySelector('#mail').textContent
     - Method C: Use vision API to read email from screenshot
     - Method D: Look for any visible text matching email pattern (xxx@yyy.zzz)
  
  3. VERIFY you found a valid email (must contain @ and domain)
  4. RETURN the email in structured format

ANTI-LOOP RULES:
  - If email not visible after 20s → Refresh page ONCE
  - If still not visible → Try different selector or JavaScript
  - Maximum 3 attempts total
  - DO NOT click random elements hoping to find email

OUTPUT FORMAT (MANDATORY):
  {
    "email": "the-extracted-email@domain.com",
    "success": true,
    "notes": "Email successfully extracted using method X"
  }

IMPORTANT:
  - Email MUST be valid format (xxx@domain.com)
  - DO NOT invent or guess email
  - If you can't find email after 3 attempts, set success=false
"""

    def build_registration_mission(self, email: str) -> str:
        """ШАГ 2: Миссия для регистрации с полученным email"""
        return f"""
MISSION: Register on Airtable using provided email and confirm account

YOUR EMAIL: {email}
REGISTRATION URL: {self.referral_url}

YOUR TASK:
  Register a new Airtable account using the email above and confirm via email.

CRITICAL WORKFLOW:
  📝 PHASE 1: REGISTER ON AIRTABLE
  -------------------------------------------
  - STEP 1: Navigate to {self.referral_url}
  
  - STEP 2: WAIT 5 seconds for form to load
  
  - STEP 3: Fill registration form:
    * Email: {email} (EXACTLY this email, DO NOT MODIFY!)
    * Full Name: Generate realistic name (e.g., "Sarah Mitchell")
    * Password: Generate strong password (e.g., "SecureP@ss2024!")
    * Checkboxes: Check all required (Terms, Privacy Policy)
  
  - STEP 4: VERIFY before submitting:
    * Email field = {email}
    * Name and password filled
    * Checkboxes checked
  
  - STEP 5: Click "Create account" button ONCE (only once!)
  
  - STEP 6: ⚠️ CRITICAL - After clicking "Create account", you MUST:
    1. **WAIT 10 seconds** for page to react
    2. **CHECK current URL** - did it change?
       ✓ If URL contains "/workspace" or "/verify" → Registration SUCCESS, proceed to STEP 7
       ✓ If URL contains "email" or "confirm" → Check page for instructions
       ✗ If URL is still /invite/... → Check for error messages on page
    3. **READ page content** - what does it say?
       ✓ "Check your email" or "Verify your email" → SUCCESS, proceed to STEP 7
       ✓ "Welcome" or dashboard elements → SUCCESS, proceed to STEP 7
       ✗ Error message visible → READ IT, report in output, set status=failed
       ⏳ Page is loading/empty → WAIT 10 MORE seconds, then re-check
    4. **DECISION**:
       - If registration succeeded (URL changed OR success message) → Continue to PHASE 2
       - If error occurred → STOP, report error in output
       - If unclear after 20s wait → Take screenshot, analyze, decide

  ✉️ PHASE 2: CONFIRM EMAIL VIA TEMP-MAIL
  -------------------------------------------
  - STEP 7: Open NEW TAB with https://temp-mail.org/en/
    * DO NOT close the Airtable tab!
    * Keep Airtable tab open in background
  
  - STEP 8: WAIT 30 seconds for confirmation email from Airtable to arrive
    * Look for new email in inbox
    * Email subject will contain "verify", "confirm", or "Airtable"
  
  - STEP 9: Find and OPEN the email from Airtable
    * Click on the email to view its content
    * DO NOT click links yet - just open to read
  
  - STEP 10: LOCATE the confirmation/verification link in the email
    * Look for button with "Verify", "Confirm", or similar text
    * Or find URL link that looks like verification link
  
  - STEP 11: COPY the verification link URL
    * Extract the full URL from the link/button
    * It should look like: https://airtable.com/verify/...
  
  - STEP 12: SWITCH back to Airtable tab (the one from STEP 1)
    * DO NOT open new tab for verification
    * Use the SAME tab where you registered
  
  - STEP 13: NAVIGATE to the verification link in Airtable tab
    * Paste/navigate to the URL you copied from email
    * This confirms email in the same browser session
  
  - STEP 14: WAIT 5 seconds for confirmation to process
  
  - STEP 15: CHECK if account is now verified
    * Look for "Email verified" or "Account confirmed" message
    * Or check if you're redirected to workspace/dashboard

ANTI-LOOP PROTECTION:
  ⛔ If you repeat the same action 3+ times:
    STOP → ANALYZE current state → TRY DIFFERENT APPROACH
  
  Common issues & solutions:
  - ❌ Button not working after 2 clicks? 
    → Check for inline error messages FIRST
    → Don't keep clicking - READ the error
  
  - ❌ Email not arriving after 30s?
    → WAIT up to 60s total (emails can be slow)
    → Check ALL emails in temp-mail inbox
    → Refresh temp-mail page if needed
  
  - ❌ Can't find verification link in email?
    → Use vision API to READ email content
    → Look for ANY clickable link
    → Extract URL manually if needed
  
  - ❌ Registration seemed to succeed but no email?
    → Check Airtable tab - maybe already verified?
    → Wait longer (up to 90s total for email)
  
  NEVER:
    - Click same button more than 2 times
    - Fill same field twice if already filled
    - Wait indefinitely (max 90s for email arrival)
    - Open verification link in NEW tab (use existing Airtable tab!)

SUCCESS INDICATORS:
  ✅ Registration successful if:
    - URL changed from /invite/... to something else
    - OR page shows "check your email" message
    - OR page shows dashboard/workspace
  
  ✅ Email confirmed if:
    - After clicking verification link, page shows success
    - OR redirected to workspace/dashboard
    - OR message says "email verified"

OUTPUT FORMAT (MANDATORY):
  {{
    "status": "success|partial|failed",
    "email": "{email}",
    "confirmed": true|false,
    "notes": "Brief explanation of what happened"
  }}

  Status meanings:
  - "success" = Account created AND email confirmed
  - "partial" = Account created but email NOT confirmed yet
  - "failed" = Registration failed (error occurred)

REMEMBER: 
  - Use EXACT email {email}
  - Open verification link in SAME tab as registration (not new tab)
  - After clicking "Create account", MUST wait and analyze result before proceeding
"""

    async def run_agent_with_timeout(self, agent: Agent, timeout: int) -> Any:
        return await asyncio.wait_for(agent.run(), timeout=timeout)

    async def run_step1_get_email(self) -> Tuple[bool, Optional[str]]:
        """ШАГ 1: Получение временного email через агента"""
        print("\n" + "=" * 60)
        print("📧 ШАГ 1: ПАРСИНГ EMAIL С TEMP-MAIL.ORG")
        print("=" * 60)
        
        try:
            profile = BrowserProfile(
                keep_alive=True,
                disable_security=False,
            )
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            conversation_path = Path(f"logs/step1_email_parser_{timestamp}.json")
            conversation_path.parent.mkdir(exist_ok=True)
            task_id = f"email_parser_{timestamp}"
            
            print(f"\n⚙️  Настройки агента (ШАГ 1):")
            print(f"   📝 Task ID: {task_id}")
            print(f"   💾 История: {conversation_path}")
            print(f"   🎬 GIF: logs/step1_email_{timestamp}.gif")
            print(f"   🌐 URL: https://temp-mail.org/en/")
            
            agent = Agent(
                task=self.build_email_parser_mission(),
                llm=self.rate_limited_llm,
                browser_profile=profile,
                
                # Основные настройки
                use_vision=True,
                max_failures=10,
                
                # Структурированный вывод
                output_model_schema=EmailParserResult,
                
                # Тайминги
                step_timeout=120,  # 2 минуты достаточно для получения email
                llm_timeout=60,
                
                # Оптимизация
                max_actions_per_step=10,
                use_thinking=True,
                flash_mode=False,
                
                # Логирование
                save_conversation_path=str(conversation_path),
                generate_gif=f"logs/step1_email_{timestamp}.gif",
                task_id=task_id,
                source="email_parser_step1",
                
                # Дополнительно
                include_recent_events=True,
                calculate_cost=True,
                display_files_in_done_text=True,
                final_response_after_failure=True,
                vision_detail_level='high',
                include_attributes=['data-testid', 'name', 'id', 'type', 'class'],
            )
            
            print("\n🤖 Агент запущен для парсинга email...\n")
            
            result = await self.run_agent_with_timeout(agent, timeout=120)
            
            # Извлекаем email из результата
            email = None
            success = False
            
            try:
                if hasattr(result, 'model_output') and result.model_output:
                    structured = result.model_output
                    email = structured.email
                    success = structured.success
                    notes = structured.notes
                    print(f"\n✅ Структурированный результат получен:")
                    print(f"   📧 Email: {email}")
                    print(f"   ✓ Success: {success}")
                    print(f"   📝 Notes: {notes}")
                else:
                    # Fallback парсинг
                    parsed = parse_agent_result(result)
                    text = parsed.get("done_text") or parsed.get("raw_text") or ""
                    email = extract_email_from_result(text)
                    success = bool(email and "@" in email)
                    print(f"\n⚠️  Fallback парсинг:")
                    print(f"   📧 Email: {email}")
                    print(f"   ✓ Success: {success}")
            except Exception as e:
                print(f"\n❌ Ошибка извлечения email: {e}")
            
            # Закрываем агент
            await agent.close()
            
            if success and email:
                print("\n" + "=" * 60)
                print(f"✅ ШАГ 1 ЗАВЕРШЁН УСПЕШНО")
                print(f"📧 Полученный email: {email}")
                print("=" * 60)
                return True, email
            else:
                print("\n" + "=" * 60)
                print(f"❌ ШАГ 1 НЕ УДАЛСЯ")
                print(f"   Email не получен или невалидный")
                print("=" * 60)
                return False, None
                
        except Exception as e:
            print(f"\n❌ Критическая ошибка в ШАГ 1: {e}")
            return False, None

    async def run_step2_register(self, email: str) -> bool:
        """ШАГ 2: Регистрация с полученным email"""
        print("\n" + "=" * 60)
        print("📝 ШАГ 2: РЕГИСТРАЦИЯ НА AIRTABLE")
        print("=" * 60)
        print(f"📧 Используем email: {email}")
        
        try:
            profile = BrowserProfile(
                keep_alive=True,
                disable_security=False,
            )
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            conversation_path = Path(f"logs/step2_registration_{timestamp}.json")
            conversation_path.parent.mkdir(exist_ok=True)
            task_id = f"registration_{timestamp}"
            
            print(f"\n⚙️  Настройки агента (ШАГ 2):")
            print(f"   📝 Task ID: {task_id}")
            print(f"   💾 История: {conversation_path}")
            print(f"   🎬 GIF: logs/step2_registration_{timestamp}.gif")
            print(f"   🌐 URL: {self.referral_url}")
            
            agent = Agent(
                task=self.build_registration_mission(email),
                llm=self.rate_limited_llm,
                browser_profile=profile,
                
                # Основные настройки
                use_vision=True,
                max_failures=20,
                
                # Структурированный вывод
                output_model_schema=RegistrationResult,
                
                # Тайминги
                step_timeout=STEP_TIMEOUT,
                llm_timeout=60,
                
                # Оптимизация
                max_actions_per_step=15,
                use_thinking=True,
                flash_mode=False,
                
                # Логирование
                save_conversation_path=str(conversation_path),
                generate_gif=f"logs/step2_registration_{timestamp}.gif",
                task_id=task_id,
                source="registration_step2",
                
                # Дополнительно
                include_recent_events=True,
                calculate_cost=True,
                display_files_in_done_text=True,
                final_response_after_failure=True,
                vision_detail_level='high',
                include_attributes=['data-testid', 'name', 'id', 'type', 'class'],
            )
            
            print("\n🤖 Агент запущен для регистрации...\n")
            
            result = await self.run_agent_with_timeout(agent, timeout=STEP_TIMEOUT)
            parsed = parse_agent_result(result)
            text = (parsed.get("done_text") or parsed.get("raw_text") or "").strip()
            
            print(f"\n📦 Результат агента (усечено): {text[:400]}")
            
            # Извлекаем структурированный результат
            try:
                if hasattr(result, 'model_output') and result.model_output:
                    structured = result.model_output
                    self.status = str(structured.status).lower()
                    self.temp_email = structured.email
                    self.confirmed = bool(structured.confirmed)
                    self.notes = str(structured.notes)
                    print("\n✅ Структурированный результат получен")
                else:
                    # Fallback парсинг
                    json_match = re.search(r'\{[\s\S]*\}', text)
                    if json_match:
                        import json
                        data = json.loads(json_match.group(0))
                        self.status = str(data.get("status", "unknown")).lower()
                        self.temp_email = email
                        self.confirmed = bool(data.get("confirmed", False))
                        self.notes = str(data.get("notes", ""))
                        print("\n⚠️  Структурированный результат из JSON")
            except Exception as e:
                print(f"\n⚠️  Ошибка парсинга результата: {e}")
                self.temp_email = email
                self.status = "unknown"
                
            # Держим браузер открытым для проверки
            print(f"\n💤 Браузер останется открытым на 1 час для проверки")
            print("   Нажмите Ctrl+C для завершения...")
            await asyncio.sleep(3600)  # 1 час
            await agent.close()
            
            return self.status == "success"
            
        except Exception as e:
            print(f"\n❌ Критическая ошибка в ШАГ 2: {e}")
            return False

    async def run(self):
        print("\n🚀 Запуск двухэтапной регистрации")
        print("=" * 60)

        try:
            self.rate_limited_llm = RateLimitedLLM(self.llm)
            
            # ШАГ 1: Получаем email
            success_step1, email = await self.run_step1_get_email()
            
            if not success_step1 or not email:
                print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить email")
                print("   Регистрация невозможна без email")
                self.status = "failed"
                self.notes = "Failed to get temporary email"
                self.save_credentials()
                return
            
            self.temp_email = email
            
            # Небольшая пауза между шагами
            print("\n⏳ Пауза 5 секунд между шагами...")
            await asyncio.sleep(5)
            
            # ШАГ 2: Регистрируемся с полученным email
            success_step2 = await self.run_step2_register(email)
            
            print("\n" + "=" * 60)
            print("✅ РЕГИСТРАЦИЯ ЗАВЕРШЕНА")
            print("=" * 60)
            print(f"📧 Email: {self.temp_email}")
            print(f"📊 Статус: {self.status}")
            print(f"✓ Подтверждено: {self.confirmed}")
            if self.notes:
                print(f"📝 Notes: {self.notes[:200]}")
            total_llm = getattr(self.rate_limited_llm, "_call_count", "n/a")
            print(f"📈 Всего LLM вызовов: {total_llm}")
            print("=" * 60)
            
            self.save_credentials()

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
