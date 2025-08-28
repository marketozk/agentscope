"""
Интеллектуальный агент регистрации с AgentScope ReAct архитектурой
"""
import asyncio
import os
from playwright.async_api import async_playwright
import google.generativeai as genai
from PIL import Image
import io
import json
from dotenv import load_dotenv
import random
import string
from datetime import datetime, timedelta

# Импортируем новых AgentScope агентов
try:
    from agentscope.model import DashScopeChatModel
    from agentscope.memory import InMemoryMemory
    from src.element_finder_agent import ElementFinderAgent, ElementSearchResult
    from src.error_recovery_agent import ErrorRecoveryAgent, RecoveryResult
    from src.form_filler_agent import FormFillerAgent, FormFillResult
    from src.checkbox_agent import CheckboxAgent, CheckboxActionResult
    from src.page_analyzer_agent import PageAnalyzerAgent, PageAnalysis
    from src.registration_orchestrator import RegistrationOrchestrator
    AGENTSCOPE_AVAILABLE = True
    print("✅ AgentScope модули загружены успешно")
except ImportError as e:
    AGENTSCOPE_AVAILABLE = False
    print(f"⚠️ AgentScope недоступен: {e}")
    print("Работаем в режиме совместимости с Gemini")

# Остальные импорты
from src.temp_mail_agent import TempMailAgent
from src.email_verification_agent import EmailVerificationAgent

# Загружаем переменные окружения из .env файла
load_dotenv()

class IntelligentRegistrationAgent:
    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.temp_mail_agent = None  # Будет инициализирован позже
        
        # Новые AgentScope агенты (инициализируются позже с page)
        self.element_finder_agent = None
        self.error_recovery_agent = None
        self.form_filler_agent = None
        self.checkbox_agent = None
        self.page_analyzer_agent = None
        self.registration_orchestrator = None
        
        # Настройки скорости выполнения
        self.action_delay = 3.0  # Пауза между действиями (секунды)
        self.page_load_delay = 5.0  # Пауза после загрузки страницы
        self.typing_delay = 0.1  # Задержка между символами при вводе
        
        self.context = {
            "email": None,
            "password": None,
            "username": None,
            "phone": None,
            "first_name": None,
            "last_name": None,
            "birth_date": None,
            "company": None,
            "website": None,
            "country": "United States",
            "city": "New York",
            "zip_code": "10001",
            "address": "123 Test Street",
            "gender": "male",
            "preferences": {
                "newsletter": False,
                "marketing": False,
                "terms": True,
                "privacy": True
            }
        }
    
    def init_agents(self, page):
        """Инициализирует AgentScope агентов после создания page"""
        if AGENTSCOPE_AVAILABLE:
            try:
                # Создаём Gemini модель для AgentScope агентов
                model = DashScopeChatModel(
                    model_name="gemini-1.5-flash",
                    api_key=os.getenv("GEMINI_API_KEY"),
                )
                
                # Инициализируем все агенты
                self.element_finder_agent = ElementFinderAgent(page, model)
                self.error_recovery_agent = ErrorRecoveryAgent(page, model)
                self.form_filler_agent = FormFillerAgent(page, model)
                self.checkbox_agent = CheckboxAgent(page, model)
                self.page_analyzer_agent = PageAnalyzerAgent(page, model)
                
                # Инициализируем RegistrationOrchestrator для координации
                self.registration_orchestrator = RegistrationOrchestrator()
                print("✅ Все AgentScope агенты и оркестратор инициализированы")
            except Exception as e:
                print(f"⚠️ Ошибка инициализации агентов: {e}")
                self.element_finder_agent = None
                self.error_recovery_agent = None
                self.form_filler_agent = None
                self.checkbox_agent = None
                self.page_analyzer_agent = None
                self.registration_orchestrator = None
        else:
            print("⚠️ AgentScope недоступен, используем fallback методы")
            self.element_finder_agent = None
            self.error_recovery_agent = None
            self.form_filler_agent = None
            self.checkbox_agent = None
            self.page_analyzer_agent = None
            self.registration_orchestrator = None
        
    async def register_with_orchestrator(self, referral_link: str):
        """
        Новый метод регистрации через RegistrationOrchestrator
        Обеспечивает централизованную координацию агентов
        """
        if not AGENTSCOPE_AVAILABLE or not self.registration_orchestrator:
            print("⚠️ RegistrationOrchestrator недоступен, используем стандартный метод")
            return await self.register(referral_link)
        
        print("\n🎭 РЕГИСТРАЦИЯ ЧЕРЕЗ ORCHESTRATOR")
        print("=" * 60)
        
        try:
            # Передаем URL и пользовательские данные в оркестратор
            user_data = {
                "registration_url": referral_link,
                "user_context": self.context.copy()
            }
            
            print("🎯 Запуск процесса через RegistrationOrchestrator...")
            result = await self.registration_orchestrator.start_registration(
                registration_url=referral_link,
                user_data=user_data
            )
            
            if result.success:
                print("✅ Регистрация через оркестратор завершена успешно!")
                print(f"📧 Email верифицирован: {result.email_verified}")
                print(f"🔗 Финальный URL: {result.final_url}")
                return True
            else:
                print("❌ Ошибка в процессе оркестратора:")
                for error in result.errors:
                    print(f"   💥 {error}")
                print("🔄 Переключаемся на стандартный метод...")
                return await self.register(referral_link)
                
        except Exception as e:
            print(f"❌ Критическая ошибка оркестратора: {e}")
            print("🔄 Переключаемся на стандартный метод...")
            return await self.register(referral_link)
        
    async def generate_user_data(self):
        """Генерация случайных данных пользователя с реальным временным email"""
        print("🎲 Генерация случайных пользовательских данных...")
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        print(f"   🔑 Уникальный ID: {random_string}")
        
        # Создаем временный email через TempMailAgent
        try:
            print("\n📧 Создание временного email адреса...")
            print("   🔗 Подключение к сервису temp-mail.io...")
            async with TempMailAgent() as mail_agent:
                temp_email = await mail_agent.create_temp_email()
                if temp_email:
                    self.context["email"] = temp_email.email
                    self.temp_mail_agent = mail_agent
                    print(f"   ✅ Временный email создан: {temp_email.email}")
                    print(f"   ⏰ Действителен до: {temp_email.expires_at}")
                else:
                    print("   ⚠️ Не удалось создать временный email через API")
                    # Fallback к случайному email
                    domains = ["tempmail.org", "10minutemail.com", "guerrillamail.com"]
                    selected_domain = random.choice(domains)
                    self.context["email"] = f"testuser_{random_string}@{selected_domain}"
                    print(f"   🔄 Использую fallback email: {self.context['email']}")
        except Exception as e:
            print(f"   ❌ Ошибка создания временного email: {e}")
            # Fallback к случайному email
            domains = ["tempmail.org", "10minutemail.com", "guerrillamail.com"] 
            selected_domain = random.choice(domains)
            self.context["email"] = f"testuser_{random_string}@{selected_domain}"
            print(f"   🔄 Использую fallback email: {self.context['email']}")
        
        # Генерация остальных данных
        print("\n🛡️ Генерация пароля...")
        self.context["password"] = f"SecurePass{random_string}123!"
        print(f"   ✅ Пароль создан (содержит буквы, цифры и символы)")
        
        print("👤 Генерация имени пользователя...")
        self.context["username"] = f"user_{random_string}"
        self.context["first_name"] = "Test"
        self.context["last_name"] = "User"
        print(f"   ✅ Пользователь: {self.context['first_name']} {self.context['last_name']}")
        print(f"   ✅ Username: {self.context['username']}")
        
        print("📞 Генерация контактных данных...")
        self.context["phone"] = "+1234567890"
        self.context["company"] = f"Test Company {random_string}"
        self.context["website"] = f"https://test{random_string}.com"
        print(f"   ✅ Телефон: {self.context['phone']}")
        print(f"   ✅ Компания: {self.context['company']}")
        print(f"   ✅ Сайт: {self.context['website']}")
        
        # Генерируем случайную дату рождения (возраст от 25 до 45 лет)
        print("🎂 Генерация даты рождения...")
        age = random.randint(25, 45)
        birth_date = datetime.now() - timedelta(days=age*365)
        self.context["birth_date"] = birth_date.strftime("%m/%d/%Y")
        print(f"   ✅ Дата рождения: {self.context['birth_date']} (возраст: {age} лет)")
        
        print("\n📋 СВОДКА СГЕНЕРИРОВАННЫХ ДАННЫХ:")
        print("="*50)
        print(f"📧 Email: {self.context['email']}")
        print(f"🛡️ Password: {self.context['password']}")
        print(f"👤 Username: {self.context['username']}")
        print(f"🎂 Birth Date: {self.context['birth_date']}")
        print(f"📞 Phone: {self.context['phone']}")
        print(f"🏢 Company: {self.context['company']}")
        print(f"🌐 Website: {self.context['website']}")
        print("="*50)
        
    async def simulate_human_behavior(self, page):
        """Имитирует поведение реального пользователя"""
        print("   🎭 Имитация поведения пользователя...")
        
        # Случайные движения мыши
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 1200)
            y = random.randint(100, 600)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Случайная прокрутка
        scroll_amount = random.randint(-200, 200)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(0.5, 1.0))
    
    async def simulate_page_viewing(self, page):
        """Имитирует просмотр страницы пользователем"""
        print("   👀 Имитация просмотра страницы...")
        
        # Прокручиваем страницу как настоящий пользователь
        viewport_height = await page.evaluate("window.innerHeight")
        page_height = await page.evaluate("document.body.scrollHeight")
        
        if page_height > viewport_height:
            # Медленно прокручиваем вниз
            scroll_steps = random.randint(3, 6)
            scroll_per_step = page_height // scroll_steps
            
            for i in range(scroll_steps):
                await page.evaluate(f"window.scrollTo(0, {scroll_per_step * i})")
                await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Возвращаемся наверх
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(random.uniform(0.5, 1.0))
    
    async def human_like_fill(self, element, text):
        """Заполняет поле как настоящий человек"""
        # Кликаем на поле
        await element.click()
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Очищаем поле
        await element.fill("")
        await asyncio.sleep(random.uniform(0.1, 0.2))
        
        # Вводим текст с человеческими паузами
        for char in text:
            await element.type(char, delay=random.randint(50, 150))
            # Иногда делаем паузы при вводе
            if random.random() < 0.1:  # 10% вероятность паузы
                await asyncio.sleep(random.uniform(0.2, 0.5))

    def get_xpath_fallback_selectors(self, action_type: str) -> list:
        """Возвращает список XPath селекторов для разных типов действий"""
        
        if action_type == "fill":
            return [
                # CSS селекторы
                'input[type="email"]', 'input[name*="email"]', '[placeholder*="email"]',
                'input[type="text"]', 'input[name*="name"]', '[placeholder*="name"]',
                'input[type="password"]', 'input[name*="password"]', '[placeholder*="password"]',
                'input[name*="company"]', '[placeholder*="company"]',
                'textarea[name*="message"]', '[placeholder*="message"]',
                # XPath селекторы для полей ввода
                'xpath=//input[@type="email"]',
                'xpath=//input[contains(@name,"email")]',
                'xpath=//input[contains(@placeholder,"email")]',
                'xpath=//input[@type="text"]',
                'xpath=//input[contains(@name,"name")]',
                'xpath=//input[contains(@placeholder,"name")]',
                'xpath=//input[@type="password"]',
                'xpath=//input[contains(@name,"password")]',
                'xpath=//input[contains(@placeholder,"password")]',
                'xpath=//input[contains(@name,"company")]',
                'xpath=//input[contains(@placeholder,"company")]',
                'xpath=//textarea[contains(@name,"message")]',
                'xpath=//textarea[contains(@placeholder,"message")]',
                'xpath=//input[@type="text"][position()=1]',  # Первое текстовое поле
                'xpath=//input[@type="text"][position()=last()]'  # Последнее текстовое поле
            ]
            
        elif action_type == "click":
            return [
                # CSS селекторы
                'button[type="submit"]',
                '[role="button"]', 
                'button:visible',
                '[aria-label*="next"]',
                '[aria-label*="continue"]',
                '[aria-label*="submit"]',
                '[data-testid*="next"]',
                '[data-testid*="submit"]',
                'button[class*="submit"]',
                'button[class*="next"]',
                'button[class*="continue"]',
                'input[type="submit"]',
                '.submit-button',
                '.next-button',
                '.continue-button',
                # XPath селекторы
                'xpath=//button[@type="submit"]',
                'xpath=//input[@type="submit"]',
                'xpath=//*[@role="button"]',
                'xpath=//button[contains(@class,"submit")]',
                'xpath=//button[contains(@class,"next")]',
                'xpath=//button[contains(@class,"continue")]',
                'xpath=//button[contains(@aria-label,"next")]',
                'xpath=//button[contains(@aria-label,"continue")]',
                'xpath=//button[contains(@aria-label,"submit")]',
                'xpath=//button[contains(text(),"→")]',
                'xpath=//button[contains(text(),"Next")]',
                'xpath=//button[contains(text(),"Continue")]',
                'xpath=//button[contains(text(),"Submit")]',
                'xpath=//button[position()=last()]',  # Последняя кнопка на странице
                'xpath=//*[contains(@class,"btn") and contains(@class,"submit")]',
                'xpath=//*[contains(@class,"button") and contains(@class,"primary")]'
            ]
            
        elif action_type == "checkbox":
            return [
                # CSS селекторы
                'input[type="checkbox"]',
                '[role="checkbox"]',
                'label input[type="checkbox"]',
                # XPath селекторы
                'xpath=//input[@type="checkbox"]',
                'xpath=//*[@role="checkbox"]',
                'xpath=//label//input[@type="checkbox"]',
                'xpath=//input[@type="checkbox"][position()=1]',
                'xpath=//input[@type="checkbox"][position()=last()]'
            ]
            
        return []
    
    async def human_like_element_click(self, page, element) -> bool:
        """Выполняет человекоподобный клик по уже найденному элементу"""
        try:
            # Прокручиваем к элементу если нужно
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(0.2, 0.4))
            
            # Симулируем движение мыши к элементу
            box = await element.bounding_box()
            if box:
                x = box['x'] + box['width'] / 2 + random.uniform(-3, 3)
                y = box['y'] + box['height'] / 2 + random.uniform(-3, 3)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.2))
            
            await element.click(timeout=3000)
            return True
        except Exception as e:
            print(f"   ❌ Ошибка клика по элементу: {e}")
            return False

    async def human_like_click(self, page, selector: str, description: str = "", is_optional: bool = False) -> bool:
        """Умный клик с использованием AgentScope ReAct агентов"""
        try:
            print(f"   🔍 Поиск элемента для клика...")
            print(f"   🎯 Начальный селектор: '{selector}'")
            
            # Сначала пытаемся с оригинальным селектором
            success = await self._try_selector_click(page, selector)
            if success:
                print(f"   ✅ Клик выполнен с оригинальным селектором!")
                return True
            
            print(f"   ⚠️ Оригинальный селектор не сработал")
            
            # Используем умного AgentScope агента для поиска элемента
            if AGENTSCOPE_AVAILABLE and self.element_finder_agent:
                print(f"   🤖 Запускаем ElementFinder Agent...")
                try:
                    search_result = await self.element_finder_agent.find_element(description, "button")
                    
                    if search_result.success and search_result.selector:
                        print(f"   🎯 Agent нашёл селектор: '{search_result.selector}' (confidence: {search_result.confidence})")
                        success = await self._try_selector_click(page, search_result.selector)
                        if success:
                            print(f"   ✅ Клик выполнен с Agent селектором!")
                            return True
                        
                        # Пробуем альтернативные селекторы
                        for alt_selector in search_result.alternative_selectors:
                            print(f"   🔄 Пробуем альтернативу: '{alt_selector}'")
                            success = await self._try_selector_click(page, alt_selector)
                            if success:
                                print(f"   ✅ Клик выполнен с альтернативным селектором!")
                                return True
                    
                    print(f"   💭 Agent рассуждение: {search_result.reasoning}")
                except Exception as e:
                    print(f"   ❌ Ошибка ElementFinder Agent: {e}")
            
            # Если AgentScope агент не помог, используем Error Recovery Agent
            if AGENTSCOPE_AVAILABLE and self.error_recovery_agent:
                print(f"   🚨 Запускаем Error Recovery Agent...")
                try:
                    error_context = {
                        'action_type': 'click',
                        'selector': selector,
                        'description': description,
                        'page_url': page.url,
                        'required': not is_optional
                    }
                    
                    recovery_result = await self.error_recovery_agent.recover_from_error(error_context)
                    
                    if recovery_result.success:
                        print(f"   ✅ Recovery Agent успешно восстановил: {recovery_result.action_taken}")
                        return True
                    else:
                        print(f"   ⚠️ Recovery Agent не смог восстановить: {recovery_result.action_taken}")
                
                except Exception as e:
                    print(f"   ❌ Ошибка Recovery Agent: {e}")
            
            # Fallback для случаев без AgentScope
            if not AGENTSCOPE_AVAILABLE:
                print(f"   🔄 Fallback: пробуем стандартные методы...")
                
                # Пробуем базовые селекторы
                fallback_selectors = self.get_xpath_fallback_selectors("click")
                for fallback_selector in fallback_selectors:
                    success = await self._try_selector_click(page, fallback_selector)
                    if success:
                        print(f"   ✅ Fallback селектор сработал: {fallback_selector}")
                        return True
                
                # Пробуем клавиатуру
                try:
                    print(f"   ⌨️ Пробуем Enter...")
                    original_url = page.url
                    await page.keyboard.press('Enter')
                    await asyncio.sleep(2)
                    # Простая проверка - изменился ли URL
                    current_url = page.url
                    if current_url != original_url:
                        print(f"   ✅ Enter сработал!")
                        return True
                except:
                    pass
            
            # Если ничего не помогло
            if is_optional:
                print(f"   ℹ️ Необязательное действие пропущено")
                return True
            else:
                print(f"   ❌ Обязательное действие не выполнено")
                # Сохраняем скриншот для отладки
                timestamp = datetime.now().strftime("%H%M%S")
                screenshot_path = f"debug_screenshot_{timestamp}.png"
                await page.screenshot(path=screenshot_path)
                print(f"   📸 Скриншот сохранен: {screenshot_path}")
                return False
                
        except Exception as e:
            print(f"   ❌ Критическая ошибка клика: {e}")
            return is_optional
    
    async def _try_selector_click(self, page, selector: str) -> bool:
        """Пробует выполнить клик по селектору"""
        try:
            await page.wait_for_selector(selector, timeout=3000, state='visible')
            element = page.locator(selector)
            
            # Прокрутка к элементу
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(0.2, 0.4))
            
            # Человекоподобное движение мыши
            box = await element.bounding_box()
            if box:
                x = box['x'] + box['width'] / 2 + random.uniform(-3, 3)
                y = box['y'] + box['height'] / 2 + random.uniform(-3, 3)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.2))
            
            await element.click(timeout=3000)
            return True
            
        except Exception:
            return False
    
    def is_relevant_button(self, button_text: str, description: str) -> bool:
        """Проверяет релевантность кнопки по тексту"""
        if not button_text:
            return False
            
        button_text = button_text.lower().strip()
        description = description.lower()
        
        # Точные совпадения
        exact_matches = [
            ("accept all", ["accept all", "accept cookies"]),
            ("continue without", ["continue without", "skip", "not now", "later"]),
            ("create account", ["create", "sign up", "register", "join"]),
            ("login", ["login", "sign in", "log in"]),
            ("submit", ["submit", "send", "continue", "next"])
        ]
        
        for desc_key, text_variants in exact_matches:
            if desc_key in description:
                for variant in text_variants:
                    if variant in button_text:
                        return True
        
        return False
    
    def get_text_patterns(self, description: str) -> list:
        """Возвращает паттерны текста для поиска на основе описания"""
        description = description.lower()
        patterns = []
        
        if "accept all" in description or "accept" in description:
            patterns.extend([
                "Accept All",
                "Accept all cookies",
                "Accept",
                "OK",
                "Agree",
                "I Accept"
            ])
        elif "continue without" in description or "skip" in description:
            patterns.extend([
                "Continue without accepting",
                "Continue without",
                "Skip",
                "Not now",
                "Later",
                "No thanks",
                "Decline"
            ])
        elif "create account" in description or "create" in description:
            patterns.extend([
                "Create account",
                "Create Account",
                "Sign up",
                "Sign Up",
                "Register",
                "Join",
                "Get Started"
            ])
        elif "login" in description:
            patterns.extend([
                "Login",
                "Log in",
                "Sign in",
                "Sign In"
            ])
        else:
            # Универсальные паттерны
            patterns.extend([
                "Continue",
                "Next",
                "Submit",
                "OK",
                "Confirm"
            ])
        
        return patterns
    
    async def debug_available_buttons(self, page):
        """Выводит все доступные кнопки на странице для отладки"""
        print("   🔍 ОТЛАДКА: Доступные кнопки на странице:")
        
        try:
            # Ищем все кнопки
            buttons = await page.query_selector_all("button, [role='button'], input[type='button'], input[type='submit'], a")
            
            for i, button in enumerate(buttons[:10]):  # Показываем первые 10
                try:
                    is_visible = await button.is_visible()
                    if is_visible:
                        text = await button.text_content()
                        tag_name = await button.evaluate("el => el.tagName")
                        classes = await button.get_attribute("class") or ""
                        aria_label = await button.get_attribute("aria-label") or ""
                        
                        print(f"      {i+1}. {tag_name}: '{text}' (class: {classes[:30]}, aria: {aria_label[:30]})")
                except:
                    continue
                    
        except Exception as e:
            print(f"   ❌ Ошибка отладки: {e}")
    
    async def ask_gemini_for_selector(self, screenshot: bytes, page_html: str, description: str, action_type: str) -> str:
        """Просит Gemini найти правильный селектор для элемента на странице"""
        try:
            image = Image.open(io.BytesIO(screenshot))
            
            prompt = f"""
            Ты - эксперт по HTML анализу и созданию XPath селекторов. Мне нужно найти элемент на веб-странице.
            
            ЗАДАЧА: {description}
            ТИП ДЕЙСТВИЯ: {action_type}
            
            Внимательно изучи HTML код страницы и скриншот. Найди нужный элемент и создай ТОЧНЫЙ селектор.
            
            HTML код всей страницы:
            {page_html}
            
            ПОШАГОВЫЙ АНАЛИЗ:
            1. Прочитай ВЕСЬ HTML код полностью
            2. Найди элемент, который соответствует задаче: "{description}"
            3. Изучи все атрибуты элемента: id, class, data-*, aria-*, type, role, name, value, placeholder
            4. Посмотри на текст внутри элемента и его родителей/детей
            5. Определи позицию элемента среди похожих элементов
            6. Создай САМЫЙ ТОЧНЫЙ и УНИКАЛЬНЫЙ селектор
            
            ТИПЫ СЕЛЕКТОРОВ (используй любой, какой лучше подходит):
            
            CSS СЕЛЕКТОРЫ:
            - #unique-id (лучший вариант)
            - .class-name
            - [data-testid="value"]
            - [aria-label="text"]
            - input[type="email"]
            - button[class*="submit"]
            - text="точный текст"
            - button:has-text("частичный")
            
            XPATH СЕЛЕКТОРЫ (используй для сложных случаев):
            - xpath=//button[@id='specific-id']
            - xpath=//button[contains(@class,'submit-button')]
            - xpath=//button[text()='Точный текст']
            - xpath=//button[contains(text(),'Частичный текст')]
            - xpath=//button[contains(@aria-label,'описание')]
            - xpath=//div[@class='form']//button[1]
            - xpath=//button[contains(@class,'primary') and contains(@class,'submit')]
            - xpath=//button[contains(@onclick,'function')]
            - xpath=//button[@type='submit' and contains(@class,'btn')]
            - xpath=//*[@role='button'][position()=2]
            - xpath=//form//button[last()]
            - xpath=//div[contains(@class,'actions')]//button[contains(text(),'Next')]
            - xpath=//button[ancestor::div[@class='specific-parent']]
            - xpath=//button[following-sibling::input[@type='text']]
            - xpath=//button[preceding-sibling::label[text()='Company']]
            
            ПРОДВИНУТЫЕ XPATH (для сложных случаев):
            - xpath=//button[normalize-space(text())='→']
            - xpath=//button[contains(@style,'background') and not(@disabled)]
            - xpath=//button[count(preceding-sibling::button)=1]
            - xpath=//div[@class='button-container']//button[contains(@class,'primary')]
            - xpath=//form[@id='registration']//button[@type='submit']
            - xpath=//button[contains(@class,'icon') and contains(@aria-label,'continue')]
            
            ОСОБЫЕ СЛУЧАИ:
            - Для кнопок со стрелками: xpath=//button[text()='→'] или xpath=//button[contains(@aria-label,'next')]
            - Для иконок: xpath=//button[contains(@class,'icon')] или xpath=//*[@role='button'][contains(@class,'icon')]
            - Для позиции: xpath=//button[position()=2] или xpath=//div//button[last()]
            - Для родителей: xpath=//div[@class='actions']//button
            
            АЛГОРИТМ СОЗДАНИЯ XPATH:
            1. Найди уникальный атрибут (id, data-testid) - используй его
            2. Нет уникального? Используй комбинацию class + text/aria-label
            3. Много похожих? Используй position() или ancestor/descendant
            4. Сложная структура? Используй путь от родителя: //parent//child
            5. Последний вариант: точный путь от корня
            
            ВАЖНО:
            - Создавай САМЫЙ НАДЕЖНЫЙ селектор
            - Предпочитай уникальные атрибуты
            - Если элемент единственный - можешь использовать простой селектор
            - Если много похожих - используй позицию или родителя
            - XPath более мощный чем CSS - используй его для сложных случаев
            
            Изучи HTML и скриншот. Верни ТОЛЬКО селектор, без объяснений.
            Если элемент не найден, верни "NOT_FOUND".
            """
            
            response = self.model.generate_content([prompt, image])
            selector = response.text.strip()
            
            # Очищаем от лишнего текста
            if '```' in selector:
                selector = selector.split('```')[1].strip()
            
            # Убираем переносы строк и лишние пробелы
            selector = selector.replace('\n', '').strip()
            
            if selector == "NOT_FOUND" or not selector:
                return None
                
            return selector
            
        except Exception as e:
            print(f"   ❌ Ошибка запроса к Gemini: {e}")
            return None
        
    async def register(self, referral_link: str):
        print("\n🚀 НАЧИНАЕМ ПРОЦЕСС РЕГИСТРАЦИИ")
        print("=" * 60)
        
        # Шаг 1: Генерируем данные для регистрации
        print("📝 Шаг 1: Генерация пользовательских данных...")
        await self.generate_user_data()
        
        print("\n⏳ Ожидание 3 секунды перед запуском браузера...")
        await asyncio.sleep(3)
        
        async with async_playwright() as p:
            print("\n🌐 Шаг 2: Запуск браузера с маскировкой...")
            
            # Настройки для полной маскировки автоматизации
            browser_args = [
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=VizDisplayCompositor',
                '--disable-ipc-flooding-protection',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-field-trial-config',
                '--disable-back-forward-cache',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-features=BlinkGenPropertyTrees',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--hide-scrollbars',
                '--mute-audio',
                '--disable-background-networking',
                '--disable-default-apps',
                '--disable-extensions',
                '--disable-sync',
                '--disable-translate',
                '--disable-logging',
                '--disable-permissions-api',
                '--disable-client-side-phishing-detection',
                '--disable-component-extensions-with-background-pages',
                '--disable-background-timer-throttling',
                '--disable-ipc-flooding-protection',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-domain-reliability',
                '--disable-component-update',
                '--disable-background-networking',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            
            browser = await p.chromium.launch(
                headless=False,
                slow_mo=500,  # Немного замедляем для естественности
                args=browser_args,
                channel="chrome"  # Используем настоящий Chrome вместо Chromium
            )
            
            # Создаем контекст с реальными настройками
            print("🎭 Создание контекста браузера с реальными настройками...")
            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},  # Популярное разрешение
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                geolocation={"latitude": 40.7128, "longitude": -74.0060},  # Нью-Йорк
                permissions=["geolocation"],
                color_scheme="light",
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Cache-Control": "max-age=0"
                }
            )
            
            page = await context.new_page()
            
            # Инициализируем AgentScope агентов
            print("🤖 Инициализация AgentScope агентов...")
            self.init_agents(page)
            
            # Дополнительные настройки для маскировки
            print("🔧 Применение дополнительных настроек маскировки...")
            
            # Удаляем webdriver признаки
            await page.add_init_script("""
                // Удаляем webdriver флаги
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Переопределяем permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Делаем chrome объект более реалистичным
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // Переопределяем плагины
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Переопределяем языки
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Эмулируем батарею
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                });
            """)
            
            # Настройки браузера
            print("⚙️ Настройка viewport и других параметров...")
            await page.set_viewport_size({"width": 1366, "height": 768})
            
            # Эмулируем реальное поведение пользователя
            await page.set_extra_http_headers({
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"'
            })
            
            try:
                print(f"\n🔗 Шаг 3: Переход по реферальной ссылке...")
                print(f"   URL: {referral_link}")
                
                # Добавляем случайную задержку перед переходом
                random_delay = random.uniform(2, 5)
                print(f"   ⏳ Случайная пауза {random_delay:.1f} секунд перед переходом...")
                await asyncio.sleep(random_delay)
                
                # Имитируем реальное поведение - двигаем мышь перед переходом
                await self.simulate_human_behavior(page)
                
                await page.goto(referral_link, wait_until='networkidle')
                
                print(f"⏳ Ожидание {self.page_load_delay} секунд для полной загрузки страницы...")
                await asyncio.sleep(self.page_load_delay)
                
                # Имитируем просмотр страницы
                await self.simulate_page_viewing(page)
                
                for step in range(1, 30):
                    print(f"\n{'='*60}")
                    print(f"📍 ШАГ АВТОМАТИЗАЦИИ #{step}")
                    print(f"{'='*60}")
                    
                    # Получаем информацию о текущей странице
                    current_url = page.url
                    print(f"🌐 Текущий URL: {current_url}")
                    
                    # Делаем скриншот для анализа
                    print("📸 Создание скриншота страницы...")
                    screenshot = await page.screenshot()
                    
                    # Получаем HTML код страницы
                    print("📄 Получение HTML кода страницы...")
                    page_html = await page.content()
                    
                    print("🤖 Отправка данных в Gemini AI для анализа...")
                    print("   ⏳ Это может занять несколько секунд...")
                    
                    # Gemini анализирует страницу и решает что делать
                    actions = await self.analyze_and_decide(screenshot, page_html, current_url)
                    
                    if not actions:
                        print("⚠️ AI не смог определить действия для этой страницы")
                        print("   Возможные причины:")
                        print("   • Превышена квота API")
                        print("   • Неожиданное содержимое страницы")
                        print("   • Сетевые проблемы")
                        
                        print(f"\n⏳ Пауза {self.action_delay * 2} секунд перед следующей попыткой...")
                        await asyncio.sleep(self.action_delay * 2)
                        continue
                    
                    # Проверяем завершение
                    if actions.get("completed", False):
                        print("\n🎉 РЕГИСТРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
                        print("✅ Все необходимые шаги выполнены")
                        break
                    
                    # Выполняем действия медленно и с комментариями
                    print(f"\n🔧 Выполнение действий (найдено {len(actions.get('actions', []))} действий)...")
                    success = await self.execute_gemini_actions_slowly(page, actions)
                    
                    if not success:
                        print("⚠️ Не все действия выполнены успешно")
                        print("   Это может быть нормально для некоторых страниц")
                        
                    # Пауза перед следующим шагом с имитацией чтения
                    reading_time = random.uniform(self.page_load_delay, self.page_load_delay * 2)
                    print(f"\n📖 Имитация чтения страницы и обдумывания ({reading_time:.1f} секунд)...")
                    await asyncio.sleep(reading_time)
                    
                    # Случайные движения мыши между шагами
                    await self.simulate_human_behavior(page)
                    
                else:
                    print(f"\n⚠️ Достигнуто максимальное количество шагов ({30})")
                    print("   Процесс регистрации может быть не завершен")
                    
            except Exception as e:
                # Анализируем ошибку
                error_context = {
                    "url": page.url if 'page' in locals() else "unknown",
                    "step": "registration_process"
                }
                # Используем ErrorRecoveryAgent для анализа ошибки
                if AGENTSCOPE_AVAILABLE and self.error_recovery_agent:
                    try:
                        print("🚨 Запускаем Error Recovery Agent...")
                        recovery_result = await self.error_recovery_agent.recover_from_error(error_context)
                        if recovery_result.success:
                            print(f"✅ Recovery Agent: {recovery_result.action_taken}")
                        else:
                            print(f"⚠️ Recovery Agent: {recovery_result.action_taken}")
                    except Exception as recovery_error:
                        print(f"❌ Ошибка Recovery Agent: {recovery_error}")
                else:
                    print(f"⚠️ Критическая ошибка: {str(e)}")
                    print("💡 Рекомендация: Проверьте интернет-соединение и перезапустите")
                
            finally:
                print("\n⏸️ Нажмите Enter для закрытия браузера...")
                input()
                await context.close()
                await browser.close()
                print("🔚 Браузер закрыт. Процесс завершен.")
    
    async def analyze_and_decide(self, screenshot: bytes, page_html: str, current_url: str) -> dict:
        """Анализирует страницу и принимает решение о действиях (с PageAnalyzerAgent)"""
        try:
            # Используем PageAnalyzerAgent если доступен
            if AGENTSCOPE_AVAILABLE and self.page_analyzer_agent:
                print("   🤖 Используем PageAnalyzer Agent для глубокого анализа...")
                try:
                    page_analysis = await self.page_analyzer_agent.analyze_current_page()
                    
                    print(f"   📄 Тип страницы: {page_analysis.page_type} (confidence: {page_analysis.page_confidence:.2f})")
                    print(f"   🎯 Основное действие: {page_analysis.main_action}")
                    print(f"   📊 Найдено элементов: {len(page_analysis.interactive_elements)}")
                    
                    # Преобразуем анализ PageAnalyzer в формат для execute_gemini_actions_slowly
                    actions = []
                    
                    if page_analysis.page_type == "registration":
                        # Для страницы регистрации создаем действия заполнения формы
                        form_elements = [e for e in page_analysis.interactive_elements if e.element_type in ['input', 'textarea']]
                        for element in form_elements[:5]:  # Ограничиваем количество
                            field_value = self._get_value_for_field(element.text, element.attributes)
                            if field_value:
                                actions.append({
                                    "type": "fill",
                                    "selector": element.selector,
                                    "value": field_value,
                                    "description": f"Заполнение поля: {element.text[:30]}",
                                    "required": True
                                })
                        
                        # Добавляем обработку чекбоксов
                        checkbox_elements = [e for e in page_analysis.interactive_elements if e.element_type == 'input' and e.attributes.get('type') == 'checkbox']
                        for checkbox in checkbox_elements[:3]:
                            actions.append({
                                "type": "check" if "terms" in checkbox.text.lower() or "privacy" in checkbox.text.lower() else "uncheck",
                                "selector": checkbox.selector,
                                "value": "",
                                "description": f"Чекбокс: {checkbox.text[:30]}",
                                "required": False
                            })
                        
                        # Добавляем кнопку продолжения
                        button_elements = [e for e in page_analysis.interactive_elements if e.element_type == 'button']
                        if button_elements:
                            actions.append({
                                "type": "click",
                                "selector": button_elements[0].selector,
                                "value": "",
                                "description": f"Кнопка: {button_elements[0].text[:30]}",
                                "required": True
                            })
                    
                    elif page_analysis.page_type == "success":
                        return {
                            "page_analysis": "Страница успешного завершения",
                            "page_type": "success",
                            "completed": True,
                            "actions": [],
                            "next_step": "Регистрация завершена"
                        }
                    
                    else:
                        # Для других типов страниц ищем основные кнопки
                        button_elements = [e for e in page_analysis.interactive_elements if e.element_type == 'button']
                        for button in button_elements[:2]:
                            actions.append({
                                "type": "click",
                                "selector": button.selector,
                                "value": "",
                                "description": f"Кнопка: {button.text[:30]}",
                                "required": False
                            })
                    
                    return {
                        "page_analysis": page_analysis.reasoning,
                        "page_type": page_analysis.page_type,
                        "completed": page_analysis.page_type == "success",
                        "actions": actions,
                        "detected_elements": {
                            "forms": [str(page_analysis.forms_count)],
                            "buttons": [e.text[:30] for e in page_analysis.interactive_elements if e.element_type == 'button'][:3],
                            "links": page_analysis.navigation_options[:3]
                        },
                        "next_step": page_analysis.next_step_prediction
                    }
                    
                except Exception as e:
                    print(f"   ❌ Ошибка PageAnalyzer Agent: {e}")
                    # Fallback к Gemini
            
            # Fallback к оригинальному Gemini анализу
            print("   🤖 Используем Gemini AI для анализа...")
            image = Image.open(io.BytesIO(screenshot))
            
            prompt = f"""
            Ты - интеллектуальный агент для автоматической регистрации на сайтах.
            
            Текущий URL: {current_url}
            
            Контекст (используй эти данные для заполнения форм):
            - Email: {self.context['email']}
            - Password: {self.context['password']}
            - Username: {self.context['username']}
            - First Name: {self.context['first_name']}
            - Last Name: {self.context['last_name']}
            - Phone: {self.context['phone']}
            - Birth Date: {self.context['birth_date']}
            - Company: {self.context['company']}
            - Website: {self.context['website']}
            - Country: {self.context['country']}
            - City: {self.context['city']}
            - Zip Code: {self.context['zip_code']}
            - Address: {self.context['address']}
            - Gender: {self.context['gender']}
            
            Правила для принятия решений:
            - Для опциональных полей (company, website) - заполняй только если они обязательны
            - Для чекбоксов: соглашайся с terms/privacy, отказывайся от marketing/newsletter
            - Для выбора плана: выбирай бесплатный/trial/free вариант
            - Если есть кнопка "Skip" или "Later" для необязательных шагов - используй её
            - Для выпадающих списков: выбирай первый подходящий вариант
            
            ВАЖНО! Используй ТОЛЬКО правильные Playwright селекторы:
            - text="точный_текст" (для поиска по ТОЧНОМУ тексту)
            - button:has-text("частичный текст") (для кнопок с частичным текстом)
            - input[type="email"] (CSS селекторы)
            - [data-testid="selector"] (data атрибуты)
            - [aria-label="текст"] (ARIA атрибуты)
            - button[type="submit"] (кнопки отправки)
            - [role="button"] (элементы с ролью кнопки)
            - xpath=//button[contains(text(),'текст')] (XPath для сложных случаев)
            - НЕ используй :contains() - это не работает в Playwright!
            
            ПРИМЕРЫ правильных селекторов:
            - Для кнопки "Accept All": text="Accept All" или button:has-text("Accept")
            - Для кнопки-стрелки "→": xpath=//button[contains(text(),'→')] или [aria-label*="next"]
            - Для поля email: input[type="email"] или [placeholder*="email"]
            - Для чекбокса: input[type="checkbox"] или [role="checkbox"]
            - Для выпадающего списка: select или [role="combobox"]
            - Для кнопки без текста: button[type="submit"] или xpath=//button[position()=last()]
            
            ОБЯЗАТЕЛЬНО анализируй скриншот внимательно и ищи:
            - Точный текст кнопок
            - Типы полей ввода
            - Aria-labels и data атрибуты
            - Классы и ID элементов
            
            Проанализируй скриншот страницы и определи:
            1. На какой странице мы находимся
            2. Какие действия нужно выполнить
            3. Есть ли необязательные элементы, которые можно пропустить
            
            ОЧЕНЬ ВАЖНО для селекторов:
            - Внимательно изучи скриншот
            - Найди ТОЧНЫЙ текст кнопок и элементов
            - Используй text="точный_текст" для кнопок с текстом
            - Ищи уникальные атрибуты (data-testid, aria-label, id, class)
            - Проверь HTML код ниже для точных атрибутов
            - Для кнопок без текста: button[type="submit"], [role="button"], xpath
            - Для стрелок и иконок: xpath=//button[contains(text(),'→')] или [aria-label*="next"]
            
            ПРИОРИТЕТ СЕЛЕКТОРОВ:
            1. Уникальные ID: #unique-id
            2. Data атрибуты: [data-testid="value"]  
            3. Aria атрибуты: [aria-label="value"]
            4. Точный текст: text="exact text"
            5. CSS классы: [class*="submit"]
            6. Type атрибуты: button[type="submit"]
            7. XPath для сложных случаев: xpath=//button[position()=last()]
            
            HTML код страницы (для поиска атрибутов):
            {page_html[:3000]}
            
            Верни ТОЛЬКО валидный JSON без markdown разметки:
            {{
                "page_analysis": "краткое описание страницы",
                "page_type": "registration/login/verification/success/captcha/profile_setup/plan_selection/onboarding/error/other",
                "completed": false,
                "has_optional_fields": false,
                "can_skip": false,
                "actions": [
                    {{
                        "type": "fill/click/select/check/uncheck/wait/scroll/skip",
                        "selector": "ПРАВИЛЬНЫЙ Playwright селектор",
                        "value": "значение для заполнения/выбора",
                        "description": "описание действия",
                        "required": true/false
                    }}
                ],
                "detected_elements": {{
                    "forms": ["описание форм на странице"],
                    "buttons": ["текст кнопок на странице"],
                    "links": ["важные ссылки"]
                }},
                "next_step": "описание следующего ожидаемого шага"
            }}
            
            Важные правила для определения действий:
            - type="fill" - для текстовых полей
            - type="select" - для выпадающих списков
            - type="check"/"uncheck" - для чекбоксов
            - type="click" - для кнопок и ссылок
            - type="skip" - для пропуска необязательных шагов
            - Анализируй визуальные элементы на скриншоте
            - Ищи кнопки "Skip", "Later", "Not now", "Continue without"
            """
            
            response = self.model.generate_content([prompt, image])
            json_text = response.text.strip()
            
            # Очистка JSON от markdown
            if '```' in json_text:
                parts = json_text.split('```')
                for part in parts:
                    if '{' in part and '}' in part:
                        json_text = part.strip()
                        if json_text.startswith('json'):
                            json_text = json_text[4:].strip()
                        break
            
            actions = json.loads(json_text)
            
            print(f"\n🤖 Gemini анализ:")
            print(f"📄 Тип страницы: {actions.get('page_type', 'unknown')}")
            print(f"💭 Описание: {actions.get('page_analysis', 'Нет описания')}")
            print(f"🔘 Можно пропустить: {'Да' if actions.get('can_skip', False) else 'Нет'}")
            print(f"➡️  Следующий шаг: {actions.get('next_step', 'Неизвестно')}")
            
            # Показываем обнаруженные элементы
            detected = actions.get('detected_elements', {})
            if detected.get('buttons'):
                print(f"🔘 Кнопки: {', '.join(detected['buttons'][:3])}")
            
            return actions
            
        except Exception as e:
            print(f"❌ Ошибка анализа Gemini: {e}")
            return None
    
    async def execute_gemini_actions_slowly(self, page, gemini_response: dict) -> bool:
        """Медленно выполняет действия с подробными комментариями и обработкой ошибок"""
        
        actions = gemini_response.get("actions", [])
        
        if not actions:
            print("📭 Нет действий для выполнения на этой странице")
            print("   Это может означать:")
            print("   • Страница уже загружена правильно")
            print("   • Требуется ручное вмешательство")
            print("   • AI не смог определить нужные действия")
            return True
        
        print(f"🎯 Найдено {len(actions)} действий для выполнения:")
        for i, action in enumerate(actions, 1):
            print(f"   {i}. {action.get('description', 'Действие без описания')}")
        
        success_count = 0
        
        for i, action in enumerate(actions):
            action_type = action.get("type")
            selector = action.get("selector")
            value = action.get("value", "")
            description = action.get("description", "Без описания")
            required = action.get("required", True)
            
            print(f"\n🔧 ДЕЙСТВИЕ {i+1}/{len(actions)}")
            print(f"   📝 Описание: {description}")
            print(f"   🎯 Тип: {action_type}")
            print(f"   🔍 Селектор: {selector}")
            if value:
                print(f"   💾 Значение: {value}")
            if not required:
                print(f"   ℹ️ Необязательное действие")
            
            # Пауза перед выполнением действия
            print(f"   ⏳ Пауза {self.action_delay} секунд перед выполнением...")
            await asyncio.sleep(self.action_delay)
            
            try:
                if action_type == "fill":
                    print("   🔍 Поиск поля для ввода...")
                    
                    # Используем FormFillerAgent если доступен
                    if AGENTSCOPE_AVAILABLE and self.form_filler_agent:
                        print("   🤖 Используем FormFiller Agent...")
                        try:
                            from src.form_filler_agent import FormFieldInfo
                            field_info = FormFieldInfo(
                                selector=selector,
                                field_type="text",
                                label=description,
                                placeholder="",
                                required=required,
                                validation_pattern=None,
                                confidence=0.8
                            )
                            
                            fill_success = await self.form_filler_agent.fill_specific_field(field_info, value)
                            if fill_success:
                                print(f"   ✅ FormFiller Agent успешно заполнил поле!")
                                success_count += 1
                            else:
                                print(f"   ⚠️ FormFiller Agent не смог заполнить поле")
                        except Exception as e:
                            print(f"   ❌ Ошибка FormFiller Agent: {e}")
                            # Fallback к стандартному методу
                            element = await page.wait_for_selector(selector, timeout=10000)
                            if element:
                                await self.human_like_fill(element, value)
                                success_count += 1
                    else:
                        # Стандартный метод
                        element = await page.wait_for_selector(selector, timeout=10000)
                        if element:
                            print("   ✅ Поле найдено!")
                            print(f"   ⌨️ Человекоподобный ввод текста: '{value}'")
                            await self.human_like_fill(element, value)
                            print(f"   ✅ Поле заполнено успешно!")
                            success_count += 1
                        else:
                            print(f"   ❌ Поле не найдено по селектору: {selector}")
                            if required:
                                return False
                        
                elif action_type == "select":
                    print("   🔍 Поиск выпадающего списка...")
                    element = await page.wait_for_selector(selector, timeout=10000)
                    if element:
                        print("   ✅ Список найден!")
                        print(f"   📝 Выбор варианта: {value}")
                        
                        # Пробуем разные способы выбора
                        try:
                            await element.select_option(value)
                            print("   ✅ Опция выбрана по значению!")
                        except:
                            try:
                                await page.select_option(selector, label=value)
                                print("   ✅ Опция выбрана по тексту!")
                            except Exception as e:
                                print(f"   ⚠️ Не удалось выбрать опцию: {e}")
                        
                        success_count += 1
                    else:
                        print(f"   ❌ Выпадающий список не найден")
                        if required:
                            return False
                            
                elif action_type == "check":
                    print("   🔍 Поиск чекбокса для отметки...")
                    
                    # Используем CheckboxAgent если доступен
                    if AGENTSCOPE_AVAILABLE and self.checkbox_agent:
                        print("   🤖 Используем Checkbox Agent...")
                        try:
                            checkbox_result = await self.checkbox_agent.handle_specific_checkbox(
                                selector, "check", f"Отметка чекбокса: {description}"
                            )
                            if checkbox_result.success:
                                print(f"   ✅ Checkbox Agent: {checkbox_result.action_taken}")
                                success_count += 1
                            else:
                                print(f"   ⚠️ Checkbox Agent: {checkbox_result.reasoning}")
                        except Exception as e:
                            print(f"   ❌ Ошибка Checkbox Agent: {e}")
                            # Fallback к стандартному методу
                            element = await page.wait_for_selector(selector, timeout=10000)
                            if element and not await element.is_checked():
                                await self.human_like_element_click(page, element)
                                success_count += 1
                    else:
                        # Стандартный метод
                        element = await page.wait_for_selector(selector, timeout=10000)
                        if element:
                            print("   ✅ Чекбокс найден!")
                            is_checked = await element.is_checked()
                            if not is_checked:
                                print("   ☑️ Человекоподобная отметка чекбокса...")
                                await self.human_like_element_click(page, element)
                                print("   ✅ Чекбокс отмечен!")
                            else:
                                print("   ℹ️ Чекбокс уже отмечен")
                            success_count += 1
                            success_count += 1
                        else:
                            print(f"   ❌ Чекбокс не найден")
                        
                elif action_type == "uncheck":
                    print("   🔍 Поиск чекбокса для снятия отметки...")
                    
                    # Используем CheckboxAgent если доступен
                    if AGENTSCOPE_AVAILABLE and self.checkbox_agent:
                        print("   🤖 Используем Checkbox Agent...")
                        try:
                            checkbox_result = await self.checkbox_agent.handle_specific_checkbox(
                                selector, "uncheck", f"Снятие отметки чекбокса: {description}"
                            )
                            if checkbox_result.success:
                                print(f"   ✅ Checkbox Agent: {checkbox_result.action_taken}")
                                success_count += 1
                            else:
                                print(f"   ⚠️ Checkbox Agent: {checkbox_result.reasoning}")
                        except Exception as e:
                            print(f"   ❌ Ошибка Checkbox Agent: {e}")
                            # Fallback к стандартному методу
                            element = await page.wait_for_selector(selector, timeout=10000)
                            if element and await element.is_checked():
                                await self.human_like_element_click(page, element)
                                success_count += 1
                    else:
                        # Стандартный метод
                        element = await page.wait_for_selector(selector, timeout=10000)
                        if element:
                            print("   ✅ Чекбокс найден!")
                            is_checked = await element.is_checked()
                            if is_checked:
                                print("   ☐ Человекоподобное снятие отметки...")
                                await self.human_like_element_click(page, element)
                                print("   ✅ Отметка снята!")
                            else:
                                print("   ℹ️ Чекбокс уже не отмечен")
                            success_count += 1
                        else:
                            print(f"   ❌ Чекбокс не найден")
                        
                elif action_type == "click":
                    print("   🔍 Поиск элемента для клика...")
                    
                    # Используем новый метод human_like_click с AgentScope агентами
                    clicked = await self.human_like_click(page, selector, description, not required)
                    if clicked:
                        success_count += 1
                    
                    if not clicked:
                        print(f"   ❌ Не удалось найти элемент для клика")
                        if required:
                            print(f"   🚨 Это обязательное действие")
                            
                            # Сохраняем скриншот для отладки
                            screenshot_path = f"debug_screenshot_{datetime.now().strftime('%H%M%S')}.png"
                            await page.screenshot(path=screenshot_path)
                            print(f"   📸 Скриншот сохранен: {screenshot_path}")
                            
                            # Используем ErrorAnalyzer для умного анализа ошибки
                            print(f"   🤖 ErrorAnalyzer анализирует ситуацию...")
                            
                            error_context = {
                                "action_type": action_type,
                                "selector": selector,
                                "description": description,
                                "page_url": page.url,
                                "element_not_found": True,
                                "required": required
                            }
                            
                            # Используем ErrorRecoveryAgent для анализа ошибки
                            if AGENTSCOPE_AVAILABLE and self.error_recovery_agent:
                                try:
                                    recovery_result = await self.error_recovery_agent.recover_from_error(error_context)
                                    if recovery_result.success:
                                        print(f"   ✅ Recovery Agent успешен: {recovery_result.action_taken}")
                                        success_count += 1
                                    else:
                                        print(f"   ⚠️ Recovery Agent: {recovery_result.action_taken}")
                                except Exception as re:
                                    print(f"   ❌ Ошибка Recovery Agent: {re}")
                            else:
                                print(f"   ⚠️ Fallback: элемент не найден, пропускаем...")
                            
                elif action_type == "wait":
                    wait_time = int(value) if value else 3
                    print(f"   ⏳ Ожидание {wait_time} секунд...")
                    await asyncio.sleep(wait_time)
                    print(f"   ✅ Ожидание завершено")
                    success_count += 1
                    
                elif action_type == "scroll":
                    scroll_amount = int(value) if value else 500
                    print(f"   📜 Прокрутка страницы на {scroll_amount} пикселей...")
                    await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    print(f"   ✅ Прокрутка выполнена")
                    success_count += 1
                    
                elif action_type == "skip":
                    print("   ⏭️ Попытка пропустить шаг...")
                    # Ищем кнопки пропуска
                    skip_selectors = [
                        selector,
                        "text=Skip",
                        "text=Later", 
                        "text=Not now",
                        "button:has-text('Skip')",
                        "button:has-text('Later')",
                        "button:has-text('Not now')",
                        "a:has-text('Skip')",
                        "[data-test*='skip']"
                    ]
                    
                    skipped = False
                    for skip_sel in skip_selectors:
                        try:
                            skip_element = await page.wait_for_selector(skip_sel, timeout=3000)
                            if skip_element:
                                await skip_element.click()
                                print(f"   ✅ Шаг пропущен успешно!")
                                skipped = True
                                success_count += 1
                                break
                        except:
                            continue
                    
                    if not skipped:
                        print(f"   ℹ️ Кнопка пропуска не найдена, продолжаем...")
                        
                else:
                    print(f"   ⚠️ Неизвестный тип действия: {action_type}")
                    
                # Пауза после каждого действия
                print(f"   ⏳ Пауза {self.action_delay/2} секунд после действия...")
                await asyncio.sleep(self.action_delay/2)
                    
            except Exception as e:
                # Анализируем ошибку
                error_context = {
                    "action_type": action_type,
                    "selector": selector,
                    "action_number": i+1,
                    "description": description
                }
                # Используем ErrorRecoveryAgent для анализа ошибки
                if AGENTSCOPE_AVAILABLE and self.error_recovery_agent:
                    try:
                        recovery_result = await self.error_recovery_agent.recover_from_error(error_context)
                        if recovery_result.success:
                            print(f"   ✅ ErrorRecoveryAgent восстановил: {recovery_result.action_taken}")
                            success_count += 1
                        else:
                            print(f"   ⚠️ ErrorRecoveryAgent: {recovery_result.action_taken}")
                            if required:
                                print(f"   🚨 Критическая ошибка обязательного действия")
                                return False
                    except Exception as recovery_error:
                        print(f"   ❌ Ошибка ErrorRecoveryAgent: {recovery_error}")
                        if required:
                            return False
                else:
                    print(f"   ❌ Ошибка: {str(e)}")
                    if required:
                        print(f"   🚨 Критическая ошибка обязательного действия") 
                        return False
        
        print(f"\n📊 ИТОГИ ВЫПОЛНЕНИЯ:")
        print(f"   ✅ Успешно: {success_count}/{len(actions)} действий")
        print(f"   📈 Процент успеха: {(success_count/len(actions)*100):.1f}%")
        
        return success_count > 0  # Возвращаем True если хотя бы одно действие выполнено

async def main():
    # Получаем API ключ из переменных окружения
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ Не найден GEMINI_API_KEY в файле .env")
        print("Создайте файл .env и добавьте: GEMINI_API_KEY=ваш_ключ")
        return
    
    agent = IntelligentRegistrationAgent(api_key)
    
    # Автоматически используем Airtable реферальную ссылку
    def _get_value_for_field(self, field_text: str, attributes: dict) -> str:
        """Определяет значение для поля на основе его текста и атрибутов"""
        field_text = field_text.lower()
        field_type = attributes.get('type', '').lower()
        field_name = attributes.get('name', '').lower()
        field_class = attributes.get('class', '').lower()
        
        combined = f"{field_text} {field_type} {field_name} {field_class}"
        
        # Email поля
        if any(keyword in combined for keyword in ['email', 'mail', 'e-mail']):
            return self.context.get('email', '')
        
        # Пароль
        elif any(keyword in combined for keyword in ['password', 'pass', 'pwd']):
            return self.context.get('password', '')
        
        # Имя
        elif any(keyword in combined for keyword in ['first', 'fname', 'firstname']):
            return self.context.get('first_name', '')
        elif any(keyword in combined for keyword in ['last', 'lname', 'lastname']):
            return self.context.get('last_name', '')
        elif 'name' in combined and 'user' not in combined:
            return f"{self.context.get('first_name', '')} {self.context.get('last_name', '')}"
        
        # Username
        elif any(keyword in combined for keyword in ['username', 'user', 'login']):
            return self.context.get('username', '')
        
        # Телефон
        elif any(keyword in combined for keyword in ['phone', 'tel', 'mobile']):
            return self.context.get('phone', '')
        
        # Компания
        elif any(keyword in combined for keyword in ['company', 'organization', 'business']):
            return self.context.get('company', '')
        
        # Сайт
        elif any(keyword in combined for keyword in ['website', 'url', 'site']):
            return self.context.get('website', '')
        
        # Дата рождения
        elif any(keyword in combined for keyword in ['birth', 'born', 'date', 'birthday']):
            return self.context.get('birth_date', '')
        
        return ""  # Если не удалось определить тип поля

async def main():
    print("🚀 Запуск системы умной регистрации...")
    
    agent = IntelligentRegistrationAgent(
        gemini_api_key=os.getenv("GEMINI_API_KEY")
    )
    
    referral_link = "https://airtable.com/invite/r/ovoAP1zR"
    print(f"🔗 Используем реферальную ссылку: {referral_link}")
    
    await agent.register(referral_link)

if __name__ == "__main__":
    asyncio.run(main())