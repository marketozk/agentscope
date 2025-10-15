"""
Автоматическая регистрация в Airtable через реферальную ссылку
с использованием временной почты от temp-mail.io

Стратегия: Один Agent + add_new_task() для последовательных шагов
"""
import asyncio
import os
import random
import string
import re
from pathlib import Path
from browser_use import Agent
from browser_use.browser.profile import BrowserProfile
from dotenv import load_dotenv
from datetime import datetime

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
from browser_use_helpers import extract_email_from_result, is_valid_email

# Загружаем переменные окружения
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Константы таймаутов и повторов
STEP_TIMEOUT = 120  # Таймаут для одного шага Agent (секунды)
RETRY_DELAY_SHORT = 3  # Короткая задержка между повторами
RETRY_DELAY_MEDIUM = 5  # Средняя задержка
RETRY_DELAY_LONG = 10  # Длинная задержка
MAX_EMAIL_CHECKS = 12  # Максимум проверок почты (2 минуты)
MAX_BUTTON_CLICKS = 3  # Максимум кликов по кнопке
BROWSER_KEEP_ALIVE = 86400  # Держать браузер открытым (24 часа)


class AirtableRegistration:
    """
    Автоматическая регистрация в Airtable через реферальную ссылку
    с использованием временной почты от temp-mail.io
    
    Стратегия: Один Agent для всех шагов (add_new_task) + retry mechanism
    """
    
    def __init__(self, llm, max_retries=5):
        self.llm = llm
        self.state = "INIT"
        self.temp_email = None
        self.password = None
        self.full_name = None
        self.max_retries = max_retries
        self.agent = None  # Единый Agent для всех шагов
        self.browser_profile = BrowserProfile(keep_alive=True)  # Держим браузер открытым!
        
    def generate_user_data(self):
        """Генерация случайных данных пользователя"""
        # Генерируем имя
        first_names = ["Alex", "Sam", "Jordan", "Taylor", "Casey", "Morgan", "Riley", "Avery"]
        last_names = ["Johnson", "Smith", "Brown", "Davis", "Wilson", "Moore", "Taylor", "Anderson"]
        
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        self.full_name = f"{first_name} {last_name}"
        
        # Генерируем пароль (безопасный, но запоминаемый)
        word = random.choice(["Sunny", "Happy", "Lucky", "Bright", "Smart", "Quick", "Fresh", "Cool"])
        number = random.randint(100, 999)
        special = random.choice(["!", "@", "#", "$"])
        self.password = f"{word}{number}{special}"
        
        print(f"📝 Сгенерированы данные:")
        print(f"   Имя: {self.full_name}")
        print(f"   Пароль: {self.password}")
    
    async def get_temp_email(self):
        """Получение временной почты с temp-mail.io"""
        print("\n📧 Получаем временную почту...")
        
        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"   Попытка {attempt}/{self.max_retries}...")
                
                task = """
                Task: Get temporary email address
                
                Steps:
                1. Open NEW tab with Ctrl+T (important: TAB not window)
                2. Go to https://temp-mail.org/en/
                3. Wait 5 seconds
                4. Find the email address on page (looks like: xxxxx@xxxxx.xxx)
                5. Copy it
                
                Return format: Just the email address, nothing else
                Example: user123@tempmail.com
                
                Note: temp-mail.org is more reliable than temp-mail.io
                """
                
                # Добавляем задачу и выполняем с таймаутом
                self.agent.add_new_task(task)
                result = await asyncio.wait_for(
                    self.agent.run(),
                    timeout=STEP_TIMEOUT
                )
                
                # Извлекаем и валидируем email
                email = extract_email_from_result(result)
                
                if email and is_valid_email(email):
                    self.temp_email = email
                    print(f"✅ Получен email: {self.temp_email}")
                    return True
                
                print(f"⚠️  Попытка {attempt} не удалась. Результат: {str(result)[:150]}...")
                
            except asyncio.TimeoutError:
                print(f"⏱️  Попытка {attempt}: таймаут ({STEP_TIMEOUT}с)")
            except Exception as e:
                print(f"⚠️  Попытка {attempt}: ошибка - {str(e)[:150]}")
            
            # Задержка перед повтором
            if attempt < self.max_retries:
                print(f"   ⏳ Ожидание {RETRY_DELAY_SHORT} сек...")
                await asyncio.sleep(RETRY_DELAY_SHORT)
        
        print("❌ Не удалось получить email после всех попыток")
        return False
    
    async def fill_registration_form(self):
        """Заполнение формы регистрации на Airtable"""
        print("\n📝 Заполняем форму регистрации...")
        
        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"   Попытка {attempt}/{self.max_retries}...")
                
                task = f"""
                Task: Fill Airtable registration form carefully
                
                Steps:
                1. Switch to the Airtable tab (first tab)
                2. Wait 2 seconds
                3. CLICK on the email input field (first input)
                4. Clear the field completely
                5. Type email slowly: {self.temp_email}
                6. Wait 1 second
                7. CLICK on the full name input field (second input)
                8. Clear the field completely
                9. Type name slowly: {self.full_name}
                10. Wait 1 second
                11. CLICK on the password input field (third input)
                12. Clear the field completely
                13. Type password slowly: {self.password}
                14. Wait 2 seconds
                15. CLICK the "Sign up" or "Create account" button
                16. Wait 5 seconds for page reaction
                
                IMPORTANT: 
                - Click each field BEFORE typing
                - Clear field BEFORE entering new data
                - Type slowly (one field at a time)
                
                Return:
                - "SUCCESS" if form submitted (page changed or confirmation visible)
                - "ERROR_INVALID_EMAIL" if email validation error
                - Otherwise: describe what you see
                """
                
                # Выполняем с таймаутом
                self.agent.add_new_task(task)
                result = await asyncio.wait_for(
                    self.agent.run(),
                    timeout=STEP_TIMEOUT
                )
                
                result_str = str(result).upper()
                
                # Проверяем результат
                if "ERROR_INVALID_EMAIL" in result_str or "INVALID EMAIL" in result_str:
                    print("⚠️  Ошибка: почта невалидна или уже используется")
                    print("   🔄 Получаем новую почту...")
                    
                    if await self.get_temp_email():
                        print(f"   ✅ Новая почта: {self.temp_email}")
                        print("   🔄 Повторяем заполнение формы...")
                        continue
                    else:
                        print("   ❌ Не удалось получить новую почту")
                        return False
                
                elif "SUCCESS" in result_str:
                    print("✅ Форма успешно отправлена")
                    return True
                
                else:
                    print(f"⚠️  Неясный результат: {str(result)[:200]}")
                
            except asyncio.TimeoutError:
                print(f"⏱️  Попытка {attempt}: таймаут ({STEP_TIMEOUT}с)")
            except Exception as e:
                print(f"⚠️  Попытка {attempt}: ошибка - {str(e)[:150]}")
            
            # Задержка перед повтором
            if attempt < self.max_retries:
                print(f"   ⏳ Ожидание {RETRY_DELAY_MEDIUM} сек...")
                await asyncio.sleep(RETRY_DELAY_MEDIUM)
        
        print("❌ Не удалось заполнить форму после всех попыток")
        return False
    
    async def wait_for_confirmation_email(self):
        """Ожидание письма подтверждения на temp-mail"""
        print("\n⏳ Ожидаем письмо подтверждения...")
        
        for attempt in range(1, MAX_EMAIL_CHECKS + 1):
            print(f"   Проверка {attempt}/{MAX_EMAIL_CHECKS}...")
            
            # Retry для каждой проверки почты
            for retry in range(1, self.max_retries + 1):
                try:
                    check_task = """
                    Switch to temp-mail.io tab.
                    Refresh the page.
                    Check for email from Airtable.
                    
                    Return:
                    - "FOUND" if email from Airtable exists
                    - "NOT_FOUND" if no emails
                    """
                    
                    self.agent.add_new_task(check_task)
                    result = await asyncio.wait_for(
                        self.agent.run(),
                        timeout=STEP_TIMEOUT
                    )
                    
                    result_str = str(result).upper()
                    if "FOUND" in result_str:
                        print("✅ Письмо найдено!")
                        return True
                    elif "NOT_FOUND" in result_str or "NOT FOUND" in result_str:
                        break  # Нормально, писем пока нет
                    else:
                        # Неясный ответ - retry
                        print(f"   ⚠️  Retry {retry}: неясный ответ...")
                        if retry < self.max_retries:
                            await asyncio.sleep(2)
                            continue
                        break
                        
                except asyncio.TimeoutError:
                    print(f"   ⏱️  Retry {retry}: таймаут")
                    if retry < self.max_retries:
                        await asyncio.sleep(2)
                        continue
                    break
                except Exception as e:
                    print(f"   ⚠️  Retry {retry}: ошибка - {str(e)[:100]}")
                    if retry < self.max_retries:
                        await asyncio.sleep(2)
                        continue
                    break
            
            # Ожидание перед следующей проверкой
            if attempt < MAX_EMAIL_CHECKS:
                print(f"   📭 Нет писем, ожидание {RETRY_DELAY_LONG} сек...")
                await asyncio.sleep(RETRY_DELAY_LONG)
        
        print(f"❌ Письмо не получено за {MAX_EMAIL_CHECKS * RETRY_DELAY_LONG // 60} минут")
        return False
    
    async def confirm_email(self):
        """Подтверждение email через ссылку в письме"""
        print("\n🔗 Подтверждаем email...")
        
        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"   Попытка {attempt}/{self.max_retries}...")
                
                task = """
                You are on temp-mail.io tab.
                
                Steps:
                1. Open the email from Airtable (click on it)
                2. Find confirmation button/link (usually "Confirm" or "Verify")
                3. Click it and wait for confirmation page
                
                Return:
                - "SUCCESS" if confirmed (words like "verified" or "confirmed")
                - Otherwise: describe what you see
                """
                
                self.agent.add_new_task(task)
                result = await asyncio.wait_for(
                    self.agent.run(),
                    timeout=STEP_TIMEOUT
                )
                
                result_str = str(result).upper()
                if "SUCCESS" in result_str or "VERIFIED" in result_str or "CONFIRMED" in result_str:
                    print("✅ Email подтвержден!")
                    return True
                
                print(f"⚠️  Попытка {attempt}: неясный результат - {str(result)[:150]}...")
                
            except asyncio.TimeoutError:
                print(f"⏱️  Попытка {attempt}: таймаут ({STEP_TIMEOUT}с)")
            except Exception as e:
                print(f"⚠️  Попытка {attempt}: ошибка - {str(e)[:150]}")
            
            # Задержка перед повтором
            if attempt < self.max_retries:
                print(f"   ⏳ Ожидание {RETRY_DELAY_MEDIUM} сек...")
                await asyncio.sleep(RETRY_DELAY_MEDIUM)
        
        print("❌ Не удалось подтвердить email после всех попыток")
        return False
    
    async def run(self):
        """Основной процесс регистрации"""
        print("\n🚀 Начинаем процесс регистрации в Airtable")
        print("=" * 50)
        print(f"⚙️  Настройки: max_retries={self.max_retries}, timeout={STEP_TIMEOUT}с")
        print("=" * 50)
        
        try:
            # Генерируем данные пользователя
            self.generate_user_data()
            
            # Шаг 1: Создаём Agent и открываем Airtable
            print("\n📍 Шаг 1: Открываем Airtable")
            open_task = "Open https://airtable.com/invite/r/ovoAP1zR and wait for the page to load."
            self.agent = Agent(
                task=open_task, 
                llm=self.llm, 
                browser_profile=self.browser_profile,  # keep_alive=True!
                use_vision=False,  # Отключаем vision для стабильности
                max_failures=5  # Увеличиваем tolerance к ValidationError
            )
            
            await asyncio.wait_for(
                self.agent.run(),
                timeout=STEP_TIMEOUT
            )
            self.state = "AIRTABLE_OPENED"
            print("✅ Airtable открыт")
            
            # Шаг 2: Получаем временную почту
            print("\n📍 Шаг 2: Получаем временную почту")
            if not await self.get_temp_email():
                raise Exception("Не удалось получить временную почту")
            self.state = "EMAIL_OBTAINED"
            
            # Шаг 3: Заполняем форму регистрации
            print("\n📍 Шаг 3: Заполняем форму")
            if not await self.fill_registration_form():
                raise Exception("Не удалось заполнить форму регистрации")
            self.state = "FORM_SUBMITTED"
            
            # Шаг 4: Ждем письмо подтверждения
            print("\n📍 Шаг 4: Ожидаем письмо")
            if not await self.wait_for_confirmation_email():
                raise Exception("Не получено письмо подтверждения")
            self.state = "EMAIL_RECEIVED"
            
            # Шаг 5: Подтверждаем email
            print("\n📍 Шаг 5: Подтверждаем email")
            if not await self.confirm_email():
                raise Exception("Не удалось подтвердить email")
            self.state = "COMPLETED"
            
            # Успех!
            print("\n" + "=" * 50)
            print("✅ УСПЕХ! Регистрация завершена")
            print("=" * 50)
            print(f"📧 Email: {self.temp_email}")
            print(f"👤 Имя: {self.full_name}")
            print(f"🔑 Пароль: {self.password}")
            print("=" * 50)
            
            # Сохраняем данные
            self.save_credentials()
            
            # Держим браузер открытым
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
            print(f"\n❌ Ошибка на этапе {self.state}: {str(e)}")
            raise
        finally:
            # Cleanup: закрываем браузер
            if self.agent:
                print("\n🧹 Закрываем браузер...")
                try:
                    await self.agent.close()
                    print("✅ Браузер закрыт")
                except Exception as e:
                    print(f"⚠️  Ошибка при закрытии браузера: {e}")
    
    def save_credentials(self):
        """Сохранение учетных данных в файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"airtable_registration_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== ДАННЫЕ РЕГИСТРАЦИИ AIRTABLE ===\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Email: {self.temp_email}\n")
            f.write(f"Имя: {self.full_name}\n")
            f.write(f"Пароль: {self.password}\n")
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
    
    # Проверка rate limit
    if not await wait_for_rate_limit():
        print("⛔ Достигнут лимит API. Попробуйте позже.")
        return
    
    # Регистрируем запрос API
    register_api_request()
    
    # Запускаем регистрацию с retry механизмом (5 попыток для обработки ошибок валидации)
    registration = AirtableRegistration(llm, max_retries=5)
    
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
