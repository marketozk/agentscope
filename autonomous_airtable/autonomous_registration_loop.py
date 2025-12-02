"""
🤖 ПОЛНОСТЬЮ АВТОНОМНАЯ СИСТЕМА РЕГИСТРАЦИИ AIRTABLE

Работает БЕЗ API ключей - всё через браузер:
1. Получает имя/пароль с https://api.randomdatatools.ru/?gender=man
2. Получает temp-mail с https://temp-mail.org/
3. Регистрируется на Airtable по реферальной ссылке
4. Подтверждает email
5. Повторяет цикл с новым уникальным fingerprint

Каждая итерация = новый браузерный профиль с уникальным fingerprint
"""
import asyncio
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple

from playwright.async_api import Page

from fingerprint_generator import FingerprintGenerator
from profile_manager import ProfileManager
from browser_framework.browser_agent import BrowserAgent
from browser_framework.steps import BrowserStep, BrowserStepError
from email_providers import get_provider, get_enabled_providers, PROVIDERS


class AutonomousRegistration:
    """Полностью автономная регистрация без API ключей"""
    
    def __init__(self, config_path: Path = None):
        # Загружаем конфигурацию
        if config_path is None:
            config_path = Path(__file__).parent / "config.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # Получаем активную реферальную ссылку
        active_key = self.config.get("active_referral", "my")
        self.referral_url = self.config["referral_links"][active_key]
        self.active_referral_name = active_key
        
        # Настройки из конфига
        self.delay_between_cycles = self.config["settings"].get("delay_between_cycles", 60)
        self.headless = self.config["settings"].get("headless", False)
        self.max_wait_for_email = self.config["settings"].get("max_wait_for_email", 60)
        self.rotate_email_providers = self.config["settings"].get("rotate_email_providers", False)
        self.fallback_on_error = self.config["settings"].get("fallback_on_error", True)
        
        # Email провайдер
        self.active_email_provider = self.config.get("active_email_provider", "guerrillamail")
        self.enabled_providers = get_enabled_providers(self.config)
        self.current_provider_index = 0
        self._init_email_provider()
        
        # Используем абсолютный путь для надёжности
        self.results_dir = Path(__file__).parent.parent / "Browser_Use" / "registration_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Браузерный агент (Playwright + Camoufox, скрыт за абстракцией)
        self.agent = BrowserAgent()
        self.context = None
        
        # Менеджер профилей
        self.profile_manager = ProfileManager()
        
        # Статистика
        self.total_attempts = 0
        self.successful_registrations = 0
        self.failed_registrations = 0
        
        # Шаги с ретраями и логированием
        self.step_get_random_data = BrowserStep("get_random_data", max_retries=2)
        self.step_get_temp_email = BrowserStep("get_temp_email", max_retries=2)
        self.step_register = BrowserStep("register_airtable", max_retries=1)
        self.step_confirm_email = BrowserStep("confirm_email", max_retries=2)
    
    def _init_email_provider(self):
        """Инициализация email провайдера"""
        self.email_provider = get_provider(self.active_email_provider)
        if not self.email_provider:
            # Fallback на guerrillamail
            print(f"⚠️ Провайдер '{self.active_email_provider}' не найден, используем guerrillamail")
            self.email_provider = get_provider("guerrillamail")
        
        print(f"\n📧 Email провайдер: {self.email_provider.name}")
        print(f"   🔗 URL: {self.email_provider.url}")
        print(f"   📋 Включенные провайдеры: {', '.join(self.enabled_providers)}")
        if self.rotate_email_providers:
            print(f"   🔄 Ротация провайдеров: ВКЛЮЧЕНА")
    
    def _get_next_provider(self):
        """Получить следующий провайдер для fallback или ротации"""
        if not self.enabled_providers:
            return None
        
        self.current_provider_index = (self.current_provider_index + 1) % len(self.enabled_providers)
        provider_name = self.enabled_providers[self.current_provider_index]
        return get_provider(provider_name)
    
    def switch_provider(self, provider_name: str = None):
        """Переключить на другой провайдер"""
        if provider_name:
            new_provider = get_provider(provider_name)
            if new_provider:
                self.email_provider = new_provider
                self.active_email_provider = provider_name
                print(f"\n🔄 Переключено на провайдер: {self.email_provider.name}")
                return True
        else:
            # Переключить на следующий
            new_provider = self._get_next_provider()
            if new_provider:
                self.email_provider = new_provider
                print(f"\n🔄 Переключено на провайдер: {self.email_provider.name}")
                return True
        return False
        
    async def init_browser(self, fingerprint: Dict, profile_path: Path):
        """Инициализация браузера через BrowserAgent (Camoufox внутри)."""
        print("\n🦊 Запуск браузера с полноценным профилем...")
        print(f"   📂 Профиль: {profile_path}")
        await self.agent.init(profile_path, headless=self.headless)
        self.context = self.agent.context
        print("✅ Браузерный агент запущен!")
    
    async def get_random_data(self) -> Optional[Tuple[str, str]]:
        """Получить случайные имя и пароль через браузер"""
        print("\n📋 Получение случайных данных...")
        page = await self.context.new_page()
        try:
            await page.goto("https://api.randomdatatools.ru/?gender=man", wait_until="networkidle")
            await asyncio.sleep(2)

            content = await page.content()
            json_match = re.search(r"\{[\s\S]*\}", content)
            if not json_match:
                print("❌ Не удалось извлечь данные из API")
                return None

            data = json.loads(json_match.group(0))
            first_name = data.get("FirstName", "")
            last_name = data.get("LastName", "")
            password = data.get("Password", "")
            full_name = f"{first_name} {last_name}".strip()

            print(f"✅ Получены данные: {full_name}")
            print(f"   🔑 Пароль: {password}")
            return full_name, password
        finally:
            try:
                await page.close()
            except Exception:
                pass
    
    async def get_temp_email(self, page: Page) -> Optional[str]:
        """Получить временную почту через текущий провайдер"""
        # Ротация провайдеров если включена
        if self.rotate_email_providers:
            self.switch_provider()
        
        # Пробуем получить email
        email = await self.email_provider.get_email(page)
        
        # Если не получилось и включен fallback - пробуем другие провайдеры
        if not email and self.fallback_on_error:
            print(f"⚠️ {self.email_provider.name} не сработал, пробуем другие провайдеры...")
            
            for provider_name in self.enabled_providers:
                if provider_name == self.active_email_provider:
                    continue  # Пропускаем текущий
                
                print(f"\n🔄 Пробуем провайдер: {provider_name}")
                fallback_provider = get_provider(provider_name)
                if fallback_provider:
                    email = await fallback_provider.get_email(page)
                    if email:
                        # Переключаемся на работающий провайдер
                        self.email_provider = fallback_provider
                        self.active_email_provider = provider_name
                        print(f"✅ Переключились на {fallback_provider.name}")
                        break
        
        return email
    
    async def register_on_airtable(self, page: Page, email: str, full_name: str, password: str) -> bool:
        """Регистрация на Airtable"""
        print(f"\n🎯 Регистрация на Airtable...")
        print(f"   📧 Email: {email}")
        print(f"   👤 Имя: {full_name}")
        
        try:
            # Открываем реферальную ссылку
            print(f"   🔗 Переход по ссылке: {self.referral_url}")
            
            try:
                await page.goto(self.referral_url, wait_until="networkidle", timeout=45000)
            except Exception as e:
                print(f"   ⚠️ Ошибка при загрузке (продолжаем): {e}")
                # Даём ещё шанс
                await asyncio.sleep(5)
            
            # Ждем загрузки страницы
            await asyncio.sleep(random.uniform(5, 8))
            
            # Проверяем что страница загрузилась
            try:
                current_url = page.url
                page_title = await page.title()
                print(f"   ✓ Страница загружена: {current_url}")
                print(f"   📄 Заголовок: {page_title}")
            except Exception as e:
                print(f"   ⚠️ Не удалось получить URL/Title: {e}")
            
            # Скриншот для отладки
            try:
                screenshot_path = f"debug_screenshot_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot(path=screenshot_path)
                print(f"   📸 Скриншот сохранен: {screenshot_path}")
            except:
                pass
            
            print("   📝 Заполнение формы регистрации...")
            
            # Заполняем форму реалистично (человекоподобно)
            try:
                # Email - только видимые поля
                email_selector = 'input[type="email"]:visible, input[name*="email" i]:not([type="hidden"]):visible'
                try:
                    await page.wait_for_selector(email_selector, timeout=10000)
                    email_field = await page.query_selector(email_selector)
                    
                    # Кликаем и фокусируемся
                    await email_field.click()
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    
                    # Печатаем как человек - посимвольно с задержками
                    for char in email:
                        await page.keyboard.type(char)
                        await asyncio.sleep(random.uniform(0.05, 0.15))
                    
                    print(f"   ✓ Email заполнен")
                except Exception as e:
                    print(f"   ⚠️ Не найдено поле Email: {e}")
                
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Full Name - только видимые текстовые поля
                name_selector = 'input[type="text"]:visible, input[name*="name" i]:not([type="hidden"]):visible'
                try:
                    await page.wait_for_selector(name_selector, timeout=10000)
                    name_field = await page.query_selector(name_selector)
                    
                    await name_field.click()
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    
                    # Печатаем посимвольно
                    for char in full_name:
                        await page.keyboard.type(char)
                        await asyncio.sleep(random.uniform(0.05, 0.15))
                    
                    print(f"   ✓ Имя заполнено")
                except Exception as e:
                    print(f"   ⚠️ Не найдено поле Name: {e}")
                
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Password
                password_selector = 'input[type="password"]:visible'
                try:
                    await page.wait_for_selector(password_selector, timeout=10000)
                    pwd_field = await page.query_selector(password_selector)
                    
                    await pwd_field.click()
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    
                    # Печатаем посимвольно
                    for char in password:
                        await page.keyboard.type(char)
                        await asyncio.sleep(random.uniform(0.05, 0.15))
                    
                    print(f"   ✓ Пароль заполнен")
                except Exception as e:
                    print(f"   ⚠️ Не найдено поле Password: {e}")
                
                await asyncio.sleep(random.uniform(1, 2))
                
                # Чекбоксы (если есть)
                try:
                    checkboxes = await page.query_selector_all('input[type="checkbox"]:visible')
                    for checkbox in checkboxes:
                        try:
                            if not await checkbox.is_checked():
                                await checkbox.check(timeout=5000)
                                print(f"   ✓ Чекбокс отмечен")
                        except:
                            pass
                except Exception as e:
                    print(f"   ⚠️ Не удалось обработать чекбоксы: {e}")
                
                await asyncio.sleep(2)
                
                # Кнопка регистрации
                print("   🔍 Поиск кнопки регистрации...")
                submit_button = None
                
                try:
                    # Пробуем разные селекторы для кнопки
                    selectors = [
                        'button[type="submit"]:visible',
                        'button:has-text("Sign up"):visible',
                        'button:has-text("Create"):visible',
                        'button:has-text("Register"):visible',
                        'input[type="submit"]:visible',
                        'button:has-text("Continue"):visible'
                    ]
                    
                    for selector in selectors:
                        try:
                            submit_button = await page.wait_for_selector(selector, timeout=3000)
                            if submit_button:
                                print(f"   ✓ Найдена кнопка: {selector}")
                                break
                        except:
                            continue
                except:
                    pass
                
                if submit_button:
                    print("   🖱️ Нажатие кнопки регистрации...")
                    try:
                        # Реалистичное наведение мыши
                        box = await submit_button.bounding_box()
                        if box:
                            # Плавное движение к кнопке
                            await page.mouse.move(
                                box['x'] + box['width'] / 2,
                                box['y'] + box['height'] / 2,
                                steps=random.randint(10, 20)
                            )
                            await asyncio.sleep(random.uniform(0.2, 0.5))
                        
                        # Клик
                        await submit_button.click(timeout=10000)
                        print("   ✓ Кнопка нажата, ожидание ответа...")
                        await asyncio.sleep(random.uniform(5, 8))
                    except Exception as e:
                        print(f"   ⚠️ Ошибка при клике: {e}")
                    
                    # Проверяем успех
                    try:
                        current_url = page.url
                        page_title = await page.title()
                        print(f"   📄 URL: {current_url}")
                        print(f"   📄 Title: {page_title}")
                        
                        if "airtable.com" in current_url and "signup" not in current_url.lower():
                            print("✅ Регистрация успешна!")
                            return True
                        elif "workspace" in current_url.lower() or "home" in current_url.lower():
                            print("✅ Регистрация успешна - перенаправлен на workspace!")
                            return True
                        else:
                            print(f"⚠️ Возможно регистрация прошла. URL: {current_url}")
                            return True
                    except Exception as e:
                        print(f"⚠️ Не удалось проверить результат: {e}")
                        return False
                else:
                    print("❌ Не найдена кнопка регистрации")
                    return False
                    
            except Exception as e:
                print(f"❌ Ошибка при заполнении формы: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка регистрации: {e}")
            return False
    
    async def register_step(self, page: Page, email: str, full_name: str, password: str, context: Dict) -> bool:
        """Обёртка для регистрации на Airtable через BrowserStep."""
        screenshots_dir = Path("debug_screenshots")
        screenshots_dir.mkdir(exist_ok=True)

        try:
            return await self.step_register.run(
                lambda: self.register_on_airtable(page, email, full_name, password),
                context=context,
                page=page,
                screenshots_dir=screenshots_dir,
            )
        except BrowserStepError as e:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = screenshots_dir / f"register_fail_{ts}.html"
            try:
                html_content = await page.content()
                html_path.write_text(html_content, encoding="utf-8")
                print(f"   🧾 HTML страницы регистрации сохранён: {html_path}")
            except Exception as save_err:
                print(f"   ⚠️ Не удалось сохранить HTML регистрации: {save_err}")

            print(f"❌ Шаг register_airtable упал: {e}")
            return False
    
    async def confirm_email(self, mail_page: Page, airtable_page: Page) -> bool:
        """Подтверждение email через текущий провайдер"""
        print("\n📬 Ожидание письма подтверждения...")
        print(f"   📧 Провайдер: {self.email_provider.name}")
        print(f"   🔍 URL страницы почты: {mail_page.url}")
        
        max_wait = self.max_wait_for_email
        
        screenshots_dir = Path("debug_screenshots")
        screenshots_dir.mkdir(exist_ok=True)
        
        # Логирование в файл
        log_file = screenshots_dir / f"email_search_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        def log(msg: str):
            """Логировать в файл и консоль"""
            print(msg)
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
            except:
                pass
        
        log(f"📋 Начало поиска письма. Провайдер: {self.email_provider.name}")
        log(f"📋 Max попыток: {max_wait}")
        
        # Ожидаем письмо от Airtable через провайдер
        email_data = await self.email_provider.wait_for_email(mail_page, "airtable", max_wait)
        
        if not email_data:
            log("❌ Письмо от Airtable не найдено")
            # Сохраняем финальный HTML
            try:
                html_path = screenshots_dir / f"mail_page_final_{datetime.now().strftime('%H%M%S')}.html"
                html_content = await mail_page.content()
                html_path.write_text(html_content, encoding="utf-8")
                log(f"   💾 Финальный HTML: {html_path.name}")
            except:
                pass
            return False
        
        log("✅ Найдено письмо от Airtable!")
        
        # Сохраняем скриншот
        try:
            await mail_page.screenshot(path=str(screenshots_dir / "before_open_email.png"))
        except:
            pass
        
        # Открываем письмо
        log("   🖱️ Открытие письма...")
        opened = await self.email_provider.open_email(mail_page, email_data)
        
        if not opened:
            log("⚠️ Не удалось открыть письмо, пробуем fallback методы...")
            # Fallback: пробуем кликнуть напрямую
            try:
                elem = email_data.get("element")
                if elem:
                    await elem.click()
                    await asyncio.sleep(3)
                    opened = True
            except:
                pass
        
        await asyncio.sleep(2)
        log(f"   📍 URL после открытия: {mail_page.url}")
        
        # Сохраняем скриншот открытого письма
        try:
            await mail_page.screenshot(path=str(screenshots_dir / "after_open_email.png"))
            html_path = screenshots_dir / f"opened_email_{datetime.now().strftime('%H%M%S')}.html"
            html_content = await mail_page.content()
            html_path.write_text(html_content, encoding="utf-8")
            log(f"   💾 HTML письма: {html_path.name}")
        except:
            pass
        
        # Ищем ссылку подтверждения через провайдер
        log("   🔍 Поиск ссылки подтверждения...")
        confirm_url = await self.email_provider.get_confirm_link(mail_page)
        
        if not confirm_url:
            log("❌ Ссылка подтверждения не найдена!")
            # Пробуем найти вручную все ссылки на airtable.com
            try:
                all_links = await mail_page.query_selector_all('a[href*="airtable.com"]')
                log(f"   Найдено ссылок на airtable.com: {len(all_links)}")
                for i, link in enumerate(all_links):
                    href = await link.get_attribute('href')
                    log(f"      {i+1}: {href[:80] if href else 'None'}...")
                    if href and ('verify' in href.lower() or 'confirm' in href.lower() or 'auth' in href.lower()):
                        confirm_url = href
                        log(f"   ✅ Найдена подходящая ссылка!")
                        break
            except Exception as e:
                log(f"   ⚠️ Ошибка поиска ссылок: {e}")
        
        if not confirm_url:
            log("❌ Не удалось найти ссылку подтверждения!")
            return False
        
        log(f"   🔗 Переход по ссылке: {confirm_url[:80]}...")
        await airtable_page.goto(confirm_url, wait_until="domcontentloaded")
        await asyncio.sleep(5)
        log("✅ Email подтвержден!")
        
        # Проходим онбординг
        await self.complete_onboarding_steps(airtable_page)
        
        return True
    
    async def complete_onboarding_steps(self, page: Page, max_steps: int = 10):
        """Универсальное прохождение шагов онбординга после регистрации"""
        print("\n🚶 Прохождение шагов онбординга...")
        
        for step_num in range(1, max_steps + 1):
            await asyncio.sleep(2)
            
            current_url = page.url
            print(f"\n   📍 Шаг {step_num}: {current_url[:60]}...")
            
            # Сохраняем скриншот для анализа
            try:
                screenshot_path = Path("debug_screenshots") / f"onboarding_step_{step_num}.png"
                screenshot_path.parent.mkdir(exist_ok=True)
                await page.screenshot(path=str(screenshot_path))
                print(f"      📸 Скриншот: {screenshot_path.name}")
            except Exception as e:
                print(f"      ⚠️ Не удалось сохранить скриншот: {e}")
            
            # Анализируем страницу
            page_info = await self.analyze_onboarding_page(page)
            
            if page_info["is_complete"]:
                print("   ✅ Онбординг завершён - достигнут workspace!")
                return True
            
            # Выполняем действие на основе анализа
            action_result = await self.perform_onboarding_action(page, page_info)
            
            if not action_result:
                print(f"   ⚠️ Не удалось выполнить действие на шаге {step_num}")
                # Пробуем просто нажать любую кнопку продолжения
                if await self.click_next_button(page):
                    print("      ✓ Нажата кнопка продолжения")
                else:
                    print("      ❌ Не найдена кнопка продолжения - останавливаемся")
                    break
        
        print(f"   ⚠️ Достигнут лимит шагов ({max_steps})")
        return False
    
    async def analyze_onboarding_page(self, page: Page) -> Dict:
        """Анализирует текущую страницу онбординга и определяет тип шага"""
        print("      🔍 Анализ страницы...")
        
        info = {
            "is_complete": False,
            "step_type": "unknown",
            "has_form": False,
            "has_continue_button": False,
            "inputs": [],
            "buttons": [],
            "text_hints": []
        }
        
        # Проверяем, достигли ли workspace/home
        url = page.url.lower()
        if any(keyword in url for keyword in ["workspace", "home", "dashboard", "/app"]):
            info["is_complete"] = True
            return info
        
        # Собираем информацию о странице через JavaScript
        page_data = await page.evaluate("""
            () => {
                const data = {
                    title: document.title,
                    headings: [],
                    buttons: [],
                    inputs: [],
                    textAreas: []
                };
                
                // Функция проверки видимости элемента
                function isVisible(el) {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' 
                        && style.visibility !== 'hidden' 
                        && style.opacity !== '0'
                        && el.offsetWidth > 0 
                        && el.offsetHeight > 0;
                }
                
                // Заголовки
                document.querySelectorAll('h1, h2, h3').forEach(h => {
                    const text = h.textContent.trim();
                    if (text && isVisible(h)) data.headings.push(text);
                });
                
                // Кнопки
                document.querySelectorAll('button, input[type="submit"], a.button').forEach(btn => {
                    if (!isVisible(btn)) return;
                    const text = btn.textContent.trim() || btn.value || btn.getAttribute('aria-label') || '';
                    if (text) data.buttons.push(text);
                });
                
                // Поля ввода
                document.querySelectorAll('input:not([type="hidden"])').forEach(input => {
                    if (!isVisible(input)) return;
                    data.inputs.push({
                        type: input.type,
                        name: input.name,
                        placeholder: input.placeholder,
                        required: input.required
                    });
                });
                
                // Текстовые области
                document.querySelectorAll('textarea').forEach(ta => {
                    if (!isVisible(ta)) return;
                    data.textAreas.push({
                        name: ta.name,
                        placeholder: ta.placeholder,
                        required: ta.required
                    });
                });
                
                return data;
            }
        """)
        
        print(f"      📄 Заголовок: {page_data.get('title', 'N/A')[:50]}")
        if page_data.get('headings'):
            print(f"      📝 Основной текст: {page_data['headings'][0][:50]}")
        
        info["text_hints"] = page_data.get('headings', [])
        info["buttons"] = page_data.get('buttons', [])
        info["inputs"] = page_data.get('inputs', [])
        info["has_form"] = len(info["inputs"]) > 0 or len(page_data.get('textAreas', [])) > 0
        info["has_continue_button"] = any(
            keyword in btn.lower() 
            for btn in info["buttons"] 
            for keyword in ["continue", "next", "skip", "finish", "done", "get started"]
        )
        
        # Определяем тип шага
        headings_text = " ".join(info["text_hints"]).lower()
        
        if "workspace" in headings_text or "team" in headings_text:
            info["step_type"] = "workspace_setup"
        elif "name" in headings_text or "profile" in headings_text:
            info["step_type"] = "profile_setup"
        elif "role" in headings_text or "job" in headings_text:
            info["step_type"] = "role_selection"
        elif "invite" in headings_text or "colleague" in headings_text:
            info["step_type"] = "invite_team"
        else:
            info["step_type"] = "generic"
        
        print(f"      🏷️  Тип шага: {info['step_type']}")
        
        return info
    
    async def perform_onboarding_action(self, page: Page, info: Dict) -> bool:
        """Выполняет действие на основе типа шага онбординга"""
        step_type = info["step_type"]
        
        try:
            if step_type == "workspace_setup":
                # Обычно нужно ввести название workspace
                print("      💼 Заполнение workspace...")
                return await self.fill_workspace_form(page, info)
            
            elif step_type == "profile_setup":
                # Профиль - обычно можно пропустить
                print("      👤 Пропуск настройки профиля...")
                return await self.click_next_button(page)
            
            elif step_type == "role_selection":
                # Выбор роли - выбираем случайную или пропускаем
                print("      🎭 Выбор роли...")
                return await self.select_role(page)
            
            elif step_type == "invite_team":
                # Приглашение команды - пропускаем
                print("      📧 Пропуск приглашения команды...")
                return await self.click_next_button(page)
            
            else:
                # Неизвестный шаг - пытаемся нажать кнопку продолжения
                print("      ❓ Неизвестный шаг - пытаемся продолжить...")
                return await self.click_next_button(page)
                
        except Exception as e:
            print(f"      ❌ Ошибка при выполнении действия: {e}")
            return False
    
    async def fill_workspace_form(self, page: Page, info: Dict) -> bool:
        """Заполняет форму создания workspace"""
        try:
            # Ищем поле для названия workspace
            input_selectors = [
                'input[type="text"]:visible',
                'input[name*="workspace"]:visible',
                'input[name*="name"]:visible',
                'input[placeholder*="workspace"]:visible'
            ]
            
            for selector in input_selectors:
                try:
                    field = await page.query_selector(selector)
                    if field:
                        # Генерируем случайное название
                        workspace_name = f"Workspace_{random.randint(1000, 9999)}"
                        await field.click()
                        await asyncio.sleep(0.5)
                        await field.fill(workspace_name)
                        print(f"         ✓ Введено: {workspace_name}")
                        await asyncio.sleep(1)
                        return await self.click_next_button(page)
                except:
                    continue
            
            # Если не нашли поле, пробуем просто продолжить
            return await self.click_next_button(page)
            
        except Exception as e:
            print(f"         ⚠️ Ошибка заполнения формы: {e}")
            return False
    
    async def select_role(self, page: Page) -> bool:
        """Выбирает случайную роль из предложенных"""
        try:
            # Ищем кнопки/чекбоксы с ролями
            role_selectors = [
                'button[role="radio"]:visible',
                'input[type="radio"]:visible',
                'div[role="option"]:visible'
            ]
            
            for selector in role_selectors:
                try:
                    roles = await page.query_selector_all(selector)
                    if roles and len(roles) > 0:
                        # Выбираем первую роль
                        await roles[0].click()
                        print(f"         ✓ Роль выбрана")
                        await asyncio.sleep(1)
                        return await self.click_next_button(page)
                except:
                    continue
            
            # Если не нашли роли, просто продолжаем
            return await self.click_next_button(page)
            
        except Exception as e:
            print(f"         ⚠️ Ошибка выбора роли: {e}")
            return False
    
    async def click_next_button(self, page: Page) -> bool:
        """Находит и нажимает кнопку продолжения"""
        # Селекторы для кнопок продолжения
        button_selectors = [
            'button:has-text("Continue"):visible',
            'button:has-text("Next"):visible',
            'button:has-text("Skip"):visible',
            'button:has-text("Finish"):visible',
            'button:has-text("Done"):visible',
            'button:has-text("Get started"):visible',
            'button[type="submit"]:visible',
            'a:has-text("Continue"):visible',
            'a:has-text("Skip"):visible'
        ]
        
        for selector in button_selectors:
            try:
                button = await page.query_selector(selector)
                if button:
                    await button.click()
                    await asyncio.sleep(2)
                    return True
            except:
                continue
        
        return False

    async def confirm_email_step(self, mail_page: Page, airtable_page: Page, context: Dict) -> bool:
        """Обёртка для подтверждения email через BrowserStep с логами и скриншотами."""
        screenshots_dir = Path("debug_screenshots")
        screenshots_dir.mkdir(exist_ok=True)

        try:
            return await self.step_confirm_email.run(
                lambda: self.confirm_email(mail_page, airtable_page),
                context=context,
                page=mail_page,
                screenshots_dir=screenshots_dir,
            )
        except BrowserStepError as e:
            # Дополнительно сохраняем HTML для пост‑анализа
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = screenshots_dir / f"confirm_email_fail_{ts}.html"
            try:
                html_content = await mail_page.content()
                html_path.write_text(html_content, encoding="utf-8")
                print(f"   🧾 HTML письма сохранён: {html_path}")
            except Exception as save_err:
                print(f"   ⚠️ Не удалось сохранить HTML: {save_err}")

            print(f"❌ Шаг confirm_email упал: {e}")
            return False
    
    async def single_registration_cycle(self, iteration: int):
        """Один полный цикл регистрации"""
        print("\n" + "="*70)
        print(f"🔄 ЦИКЛ РЕГИСТРАЦИИ #{iteration}")
        print("="*70)
        
        self.total_attempts += 1
        
        # 1. Создаем полноценный профиль браузера
        print("   📂 Создание нового браузерного профиля...")
        profile = self.profile_manager.create_profile()
        profile_path = Path(profile["profile_path"])
        
        # 2. Генерируем уникальный fingerprint
        generator = FingerprintGenerator()
        fingerprint = generator.generate_complete_fingerprint()
        generator.print_fingerprint(fingerprint)
        
        # 3. Запускаем браузер с профилем и fingerprint
        await self.init_browser(fingerprint, profile_path)
        
        try:
            # 4. Прогреваем браузер (реалистичное поведение)
            print("\n🔥 Прогрев браузера для реалистичности...")
            try:
                warmup_page = await self.context.new_page()
                
                # Посещаем несколько обычных сайтов
                warmup_sites = [
                    "https://www.google.com",
                    "https://www.wikipedia.org",
                ]
                
                for site in warmup_sites:
                    try:
                        print(f"   🌐 Посещение: {site}")
                        await warmup_page.goto(site, wait_until="domcontentloaded", timeout=15000)
                        await asyncio.sleep(random.uniform(2, 4))
                    except Exception as e:
                        print(f"   ⚠️ Ошибка при посещении {site}: {e}")
                
                try:
                    await warmup_page.close()
                except:
                    pass
                    
                await asyncio.sleep(random.uniform(1, 3))
            except Exception as e:
                print(f"   ⚠️ Ошибка при прогреве браузера: {e}")
            
            # 5. Получаем случайные данные (через шаг)
            random_data = await self.step_get_random_data.run(
                self.get_random_data,
                context={"iteration": iteration},
                page=None,
                screenshots_dir=Path("debug_screenshots"),
            )
            if not random_data:
                print("❌ Не удалось получить случайные данные")
                self.failed_registrations += 1
                return False
            
            full_name, password = random_data
            
            # 6. Проверяем что контекст активен
            if not self.context:
                print("❌ Контекст браузера закрыт")
                self.failed_registrations += 1
                return False
            
            # 7. Создаем две страницы: для temp-mail и для Airtable
            try:
                mail_page = await self.context.new_page()
                airtable_page = await self.context.new_page()
            except Exception as e:
                print(f"❌ Не удалось создать страницы: {e}")
                self.failed_registrations += 1
                return False
            
            # 5. Получаем временную почту (через шаг)
            email = await self.step_get_temp_email.run(
                lambda: self.get_temp_email(mail_page),
                context={"iteration": iteration},
                page=mail_page,
                screenshots_dir=Path("debug_screenshots"),
            )
            if not email:
                print("❌ Не удалось получить временную почту")
                self.failed_registrations += 1
                return False
            
            # 6. Регистрируемся на Airtable
            success = await self.register_step(
                airtable_page,
                email,
                full_name,
                password,
                context={"iteration": iteration, "email": email},
            )
            if not success:
                print("❌ Регистрация не удалась")
                self.failed_registrations += 1
                return False
            
            # 7. Подтверждаем email
            confirmed = await self.confirm_email_step(
                mail_page,
                airtable_page,
                context={"iteration": iteration, "email": email},
            )
            
            # 8. Сохраняем результат
            result = {
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "email": email,
                "full_name": full_name,
                "password": password,
                "registered": success,
                "confirmed": confirmed,
                "fingerprint": {
                    "session_id": fingerprint["session_id"],
                    "user_agent": fingerprint["user_agent"],
                    "city": fingerprint["city"]
                }
            }
            
            self.save_result(result)
            
            if success:
                self.successful_registrations += 1
                print("\n🎉 РЕГИСТРАЦИЯ УСПЕШНА!")
            else:
                self.failed_registrations += 1
            
            # Даем время посмотреть результат
            print("\n⏸️  Пауза 10 секунд перед следующей итерацией...")
            await asyncio.sleep(10)
            
            return success
            
        except KeyboardInterrupt:
            print("\n⚠️ Цикл прерван пользователем")
            raise
        except asyncio.CancelledError:
            print("\n⚠️ Задача отменена")
            self.failed_registrations += 1
            return False
        except Exception as e:
            print(f"\n❌ Ошибка в цикле: {e}")
            import traceback
            traceback.print_exc()
            self.failed_registrations += 1
            return False
            
        finally:
            # Закрываем браузер через BrowserAgent
            try:
                await self.agent.close()
            except Exception as e:
                print(f"⚠️ Ошибка при закрытии BrowserAgent: {e}")
    
    def save_result(self, result: Dict):
        """Сохранение результата регистрации"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON файл
        json_file = self.results_dir / f"result_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Текстовый файл для удобства
        txt_file = self.results_dir / f"result_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("="*50 + "\n")
            f.write(f"РЕЗУЛЬТАТ РЕГИСТРАЦИИ #{result['iteration']}\n")
            f.write("="*50 + "\n")
            f.write(f"Дата: {result['timestamp']}\n")
            f.write(f"Email: {result['email']}\n")
            f.write(f"Имя: {result['full_name']}\n")
            f.write(f"Пароль: {result['password']}\n")
            f.write(f"Зарегистрирован: {'✅ Да' if result['registered'] else '❌ Нет'}\n")
            f.write(f"Email подтвержден: {'✅ Да' if result['confirmed'] else '❌ Нет'}\n")
            f.write("="*50 + "\n")
        
        print(f"💾 Результат сохранен: {txt_file.name}")
    
    def print_statistics(self):
        """Вывод статистики"""
        print("\n" + "="*70)
        print("📊 СТАТИСТИКА")
        print("="*70)
        print(f"Всего попыток: {self.total_attempts}")
        print(f"Успешных: {self.successful_registrations} ✅")
        print(f"Неудачных: {self.failed_registrations} ❌")
        if self.total_attempts > 0:
            success_rate = (self.successful_registrations / self.total_attempts) * 100
            print(f"Процент успеха: {success_rate:.1f}%")
        print("="*70)
    
    async def run_infinite_loop(self):
        """Бесконечный цикл регистраций"""
        print("\n" + "🔄" * 35)
        print("🤖 ЗАПУСК АВТОНОМНОЙ СИСТЕМЫ МАССОВОЙ РЕГИСТРАЦИИ")
        print("🔄" * 35)
        print(f"📍 Реферальная ссылка: {self.referral_url}")
        print(f"🏷️  Активный реферал: {self.active_referral_name}")
        print(f"⏱️  Задержка между циклами: {self.delay_between_cycles} секунд")
        print(f"📂 Результаты сохраняются в: {self.results_dir.absolute()}")
        print("\n⚠️  Нажмите Ctrl+C для остановки\n")
        
        iteration = 1
        
        try:
            while True:
                await self.single_registration_cycle(iteration)
                
                self.print_statistics()
                
                if self.delay_between_cycles > 0:
                    print(f"\n⏳ Ожидание {self.delay_between_cycles} секунд до следующего цикла...")
                    await asyncio.sleep(self.delay_between_cycles)
                
                iteration += 1
                
        except KeyboardInterrupt:
            print("\n\n👋 Остановка системы пользователем...")
            self.print_statistics()
        except Exception as e:
            print(f"\n\n❌ Критическая ошибка: {e}")
            self.print_statistics()


async def main():
    """Главная функция"""
    # Создаем систему (реферальная ссылка загружается из config.json)
    system = AutonomousRegistration()
    
    # Запускаем бесконечный цикл (все настройки из config.json)
    await system.run_infinite_loop()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   🤖 АВТОНОМНАЯ СИСТЕМА МАССОВОЙ РЕГИСТРАЦИИ AIRTABLE 🤖      ║
    ║                                                               ║
    ║   ✓ Без API ключей - всё через браузер                       ║
    ║   ✓ Уникальный fingerprint на каждую регистрацию             ║
    ║   ✓ Автоматическое получение temp-mail                       ║
    ║   ✓ Подтверждение email                                      ║
    ║   ✓ Бесконечный цикл                                         ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())
