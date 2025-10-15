"""
Упрощенная автоматическая регистрация в Airtable
Стратегия: Single Task - весь процесс в одном запросе к агенту

Преимущества:
- Минимум кода
- Агент сам управляет всем процессом
- Меньше API запросов
- Естественный flow для LLM
"""
import asyncio
import random
from pathlib import Path
from browser_use import Agent
from dotenv import load_dotenv
from datetime import datetime

# Импорт конфигурации
from config import (
    get_app_config,
    get_llm,
    wait_for_rate_limit,
    register_api_request,
    print_api_stats
)

# Загружаем переменные окружения
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def generate_user_data():
    """Генерация случайных данных пользователя"""
    first_names = ["Alex", "Sam", "Jordan", "Taylor", "Casey", "Morgan", "Riley", "Avery"]
    last_names = ["Johnson", "Smith", "Brown", "Davis", "Wilson", "Moore", "Taylor", "Anderson"]
    
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    full_name = f"{first_name} {last_name}"
    
    # Генерируем пароль
    word = random.choice(["Sunny", "Happy", "Lucky", "Bright", "Smart", "Quick", "Fresh", "Cool"])
    number = random.randint(100, 999)
    special = random.choice(["!", "@", "#", "$"])
    password = f"{word}{number}{special}"
    
    return full_name, password


def save_credentials(email, full_name, password):
    """Сохранение учетных данных в файл"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"airtable_account_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=== AIRTABLE REGISTRATION SUCCESS ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Email: {email}\n")
        f.write(f"Full Name: {full_name}\n")
        f.write(f"Password: {password}\n")
        f.write("=" * 40 + "\n")
    
    print(f"\n💾 Credentials saved to: {filename}")
    return filename


async def register_airtable_simple(max_retries=3):
    """
    Упрощенная регистрация в Airtable - все в одном запросе
    
    Args:
        max_retries: Количество попыток при ошибках (по умолчанию 3)
    """
    print("\n🚀 Starting Airtable Registration (Simple Version)")
    print("=" * 60)
    
    # Генерируем данные
    full_name, password = generate_user_data()
    
    print(f"📝 Generated user data:")
    print(f"   Name: {full_name}")
    print(f"   Password: {password}")
    print(f"⚙️  Max retries: {max_retries}")
    print("=" * 60)
    
    # Создаем ОДИН большой task со всей бизнес-логикой
    task = f"""
You are automating an Airtable registration process. Follow these steps carefully:

CRITICAL: Data Format Requirements
- Email field: ONLY email address (format: xxx@xxx.xxx) - NO name, NO extra text
- Full name field: ONLY full name - NO email, NO extra text
- Password field: ONLY password - NO email, NO name
DO NOT mix up the fields or put multiple values in one field!

STEP 1: Open Airtable Registration
- Navigate to https://airtable.com/invite/r/ovoAP1zR
- Wait for the page to fully load (5 seconds minimum)

STEP 2: Get Temporary Email
- Open https://temp-mail.io/ru in a NEW TAB (not a new window)
- Wait for temp-mail page to fully load (at least 5 seconds)
- IMPORTANT: The email address is visible on the page in multiple ways:
  * There might be an input field with the email
  * There might be a text element showing the email
  * Use your vision capability to find any text matching email format (xxx@xxx.xxx)
  * The email is usually displayed prominently near the top of the page
- Copy the temporary email address you find
- Remember this email - you will use it in the registration form

STEP 3: Fill Registration Form
- Switch back to the Airtable tab (first tab)
- Fill in the registration form with these credentials:
  * Email address field: [use ONLY the email you got from temp-mail, format: xxx@xxx.xxx]
  * Full name field: {full_name}
  * Password field: {password}
- VALIDATION - Before submitting, verify each field:
  * Email field contains ONLY email (no name, no extra text, just email address)
  * Full name field contains ONLY the name: {full_name}
  * Password field contains ONLY the password: {password}
  * If any field has wrong data, clear it and enter correct data
- Find and click the "Sign up" or "Create account" button
- IMPORTANT: After clicking, verify that the button was pressed successfully:
  * Wait 3-5 seconds for the page to react
  * Check if the page changed (new URL, loading indicator, or success message)
  * If you see an error message about invalid data, report it and try to fix it
  * If nothing happens, try clicking the button again
  * Only proceed to next step when you confirm the form was submitted successfully

STEP 4: Wait for Confirmation Email
- Switch to the temp-mail.io tab
- You should now wait for Airtable to send a confirmation email
- Refresh the temp-mail page every 10 seconds
- Check for an email from Airtable (subject usually contains "Confirm" or "Verify")
- Maximum waiting time: 2 minutes (12 checks total)
- If you see the email from Airtable, proceed to next step
- If no email arrives after 2 minutes, report this issue

STEP 5: Confirm Email
- Open the confirmation email from Airtable
- Find and click the confirmation button/link (usually says "Confirm email" or "Verify email")
- Wait for the confirmation page to load (3-5 seconds)
- IMPORTANT: Verify that email confirmation was successful:
  * Look for confirmation messages like "verified", "confirmed", "success"
  * Check if you were redirected to Airtable dashboard or welcome page
  * If you see an error, report it
  * Only mark as success when you see clear confirmation

FINAL STEP: Report Success
- Return a summary in this exact format:
  "SUCCESS: Registration completed
   Email: [the temporary email address you used]
   Name: {full_name}
   Password: {password}
   Status: All steps completed successfully"

- If any step failed, report it in this format:
  "FAILED: Registration incomplete
   Failed at: [step name]
   Reason: [describe what went wrong]
   Email used: [if you got the email]"

IMPORTANT NOTES:
- Use "NEW TAB" when opening temp-mail, not a new window
- DO NOT MIX UP FORM FIELDS - each field should contain ONLY its designated data:
  * Email field = email ONLY
  * Name field = name ONLY  
  * Password field = password ONLY
- Always verify button clicks - wait and check if action succeeded
- Validate form data before submitting - check that each field has correct data
- Be patient - wait for pages to load fully before proceeding
- After each critical action (button click, form submit), verify success
- If you see validation errors, fix the data and try again
- If something fails, describe what went wrong clearly
- The temporary email is critical - make sure to extract and use it correctly

Begin the registration process now.
"""

    # Запускаем агента с полной задачей и retry механизмом
    print("\n🤖 Starting browser agent with complete task...")
    print("=" * 60)
    
    llm = get_llm()
    
    # Retry loop для обработки 503 и других ошибок
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n🔄 Attempt {attempt}/{max_retries}...")
            
            agent = Agent(task=task, llm=llm, use_vision=True)
            result = await agent.run()
            
            # Если успешно - выходим из цикла
            print("\n" + "=" * 60)
            print("📊 AGENT RESULT:")
            print("=" * 60)
            print(result)
            print("=" * 60)
            
            # Пытаемся извлечь email из результата
            result_str = str(result)
            if "SUCCESS" in result_str.upper():
                print("\n✅ Registration appears successful!")
                
                # Простой парсинг email из результата
                lines = result_str.split('\n')
                email_line = [line for line in lines if 'Email:' in line or '@' in line]
                
                if email_line:
                    # Пытаемся извлечь email
                    import re
                    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', result_str)
                    if email_match:
                        email = email_match.group(0)
                        print(f"\n📧 Extracted email: {email}")
                        
                        # Сохраняем данные
                        filename = save_credentials(email, full_name, password)
                        
                        print("\n" + "=" * 60)
                        print("✅ REGISTRATION COMPLETED SUCCESSFULLY!")
                        print("=" * 60)
                        print(f"📧 Email: {email}")
                        print(f"👤 Name: {full_name}")
                        print(f"🔑 Password: {password}")
                        print(f"💾 Saved to: {filename}")
                        print("=" * 60)
                    else:
                        print("\n⚠️  Could not extract email from result")
                        print("But registration might still be successful - check the result above")
            else:
                print("\n⚠️  Registration status unclear - check the result above")
            
            # Успешное завершение - выходим из retry loop
            break
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n⚠️  Attempt {attempt} failed: {error_msg[:200]}")
            
            # Проверяем тип ошибки
            if "503" in error_msg or "overloaded" in error_msg.lower():
                print("   🔄 Model is overloaded (503 error)")
            elif "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                print("   ⏳ Rate limit exceeded (429 error)")
            else:
                print("   ❌ Unknown error")
            
            # Если это не последняя попытка - ждем перед retry
            if attempt < max_retries:
                wait_time = 10 * attempt  # Экспоненциальная задержка: 10, 20, 30 секунд
                print(f"   ⏳ Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
            else:
                print(f"\n❌ All {max_retries} attempts failed")
                raise
    
    # Оставляем браузер открытым после успешной регистрации
    print("\n💤 Browser will stay open. Press Ctrl+C to close...")
    await asyncio.sleep(86400)  # 24 hours


async def main():
    """Main entry point"""
    try:
        # Показываем конфигурацию
        config = get_app_config()
        config.print_config()
        
        # Проверяем rate limit
        if not await wait_for_rate_limit():
            print("⛔ API rate limit reached. Try again later.")
            return
        
        # Регистрируем запрос
        register_api_request()
        
        # Запускаем упрощенную регистрацию с retry (по умолчанию 3 попытки)
        # При 503 ошибке будет автоматический retry с экспоненциальной задержкой
        await register_airtable_simple(max_retries=3)
        
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
    finally:
        # Показываем статистику
        print_api_stats()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     AIRTABLE REGISTRATION - SIMPLE VERSION                  ║
║     Single Task Strategy                                    ║
║                                                              ║
║  This version uses ONE big task for the entire process.     ║
║  The agent handles all steps autonomously.                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())
