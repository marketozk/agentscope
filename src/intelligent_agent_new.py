"""
Главный интеллектуальный агент для регистрации с продвинутым анализом интерфейса
"""
import asyncio
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Page
import inquirer
from .agent_core import BaseAgent, BrowserAgent, PageAnalysis
from .ai_analyzer import GeminiAnalyzer, ActionPlanner
from .page_analyzer import WebPageAnalyzer, PageInterface
from .interface_agent import InterfaceInteractionAgent, ActionResult

class IntelligentRegistrationAgent(BaseAgent):
    """Интеллектуальный агент для автоматической регистрации с продвинутым анализом интерфейса"""
    
    def __init__(self, gemini_api_key: str):
        super().__init__(
            "IntelligentRegistrationAgent",
            ["registration", "form_filling", "page_analysis", "interface_understanding"]
        )
        self.browser_agent = BrowserAgent()
        self.ai_analyzer = GeminiAnalyzer(gemini_api_key)
        self.action_planner = ActionPlanner(self.ai_analyzer)
        self.page_analyzer = WebPageAnalyzer(gemini_api_key)
        self.interface_agent = InterfaceInteractionAgent(gemini_api_key)
        self.user_data = {}
        self.registration_steps = []
        
    async def execute(self, referral_link: str) -> bool:
        """Выполнить регистрацию по реферальной ссылке с интеллектуальным анализом"""
        async with async_playwright() as p:
            # Создаём браузер
            browser = await self.browser_agent.create_browser(p, headless=False)
            page = await browser.new_page()
            
            try:
                # Настройка страницы
                await self._setup_page(page)
                
                # Переход по ссылке
                print(f"🔗 Переход по ссылке: {referral_link}")
                await page.goto(referral_link, wait_until='networkidle')
                
                # Интеллектуальный цикл регистрации
                result = await self._intelligent_registration_flow(page)
                
                return result['success']
                
            except Exception as e:
                self.logger.error(f"Ошибка выполнения регистрации: {e}")
                return False
            finally:
                await browser.close()
    
    async def _intelligent_registration_flow(self, page: Page) -> Dict[str, Any]:
        """Интеллектуальный процесс регистрации с полным анализом интерфейса"""
        
        max_steps = 25
        step_count = 0
        
        while step_count < max_steps:
            step_count += 1
            print(f"\n📍 Шаг {step_count}: Анализирую интерфейс...")
            
            # Полный анализ страницы с новой системой
            page_interface = await self.interface_agent.analyze_and_remember_page(page)
            
            print(f"📄 Тип страницы: {page_interface.page_type}")
            print(f"🎯 Найдено интерактивных элементов: {len(page_interface.interactive_elements)}")
            
            # Показываем найденные элементы
            if page_interface.interactive_elements:
                print("🔍 Найденные элементы:")
                for elem in page_interface.interactive_elements[:5]:  # Показываем первые 5
                    print(f"  - {elem.element_type}: {elem.text[:30]}... ({elem.selector})")
            
            # Проверяем завершение регистрации
            completion_status = await self._check_completion_status(page_interface)
            if completion_status['completed']:
                print(f"✅ {completion_status['reason']}")
                return {
                    "success": True,
                    "message": "Регистрация завершена успешно",
                    "steps_taken": step_count,
                    "completion_reason": completion_status['reason']
                }
            
            # Показываем ошибки если есть
            if page_interface.error_messages:
                print(f"❌ Найдены ошибки: {page_interface.error_messages}")
            
            # Получаем рекомендации по действиям
            suggested_actions = await self.interface_agent.suggest_next_actions({
                'user_data': self.user_data,
                'registration_goal': True,
                'required_fields': ['email', 'username', 'password', 'first_name', 'last_name']
            })
            
            if not suggested_actions:
                print("⚠️ Нет доступных действий")
                # Пробуем стандартный анализ
                fallback_result = await self._fallback_analysis(page)
                if not fallback_result:
                    return {
                        "success": False,
                        "error": "Не найдены действия для выполнения",
                        "steps_taken": step_count
                    }
                continue
            
            # Показываем доступные действия
            print(f"🎬 Рекомендованные действия ({len(suggested_actions)}):")
            for i, action in enumerate(suggested_actions[:3]):
                print(f"  {i+1}. {action.get('description', action.get('action'))}")
            
            # Выбираем лучшее действие
            best_action = suggested_actions[0]
            print(f"▶️ Выполняю: {best_action.get('description', best_action.get('action'))}")
            
            # Подготавливаем данные для действия
            action_data = await self._prepare_action_data(best_action, page_interface)
            
            # Выполняем действие
            result = await self.interface_agent.execute_action(page, best_action, action_data)
            
            # Записываем результат
            self.registration_steps.append({
                'step': step_count,
                'action': best_action,
                'result': result,
                'page_type': page_interface.page_type,
                'url': page.url
            })
            
            if result.success:
                print(f"✅ {result.message}")
                
                # Если страница изменилась, ждем загрузки
                if result.page_changed:
                    print("🔄 Страница изменилась, ожидаю загрузки...")
                    await asyncio.sleep(2)
                    await page.wait_for_load_state('networkidle', timeout=10000)
            else:
                print(f"❌ {result.message}")
                # Пробуем следующее действие если есть
                if len(suggested_actions) > 1:
                    print("🔄 Пробую альтернативное действие...")
                    continue
        
        return {
            "success": False,
            "error": "Превышено максимальное количество шагов",
            "steps_taken": step_count
        }
    
    async def _check_completion_status(self, page_interface: PageInterface) -> Dict[str, Any]:
        """Проверяет статус завершения регистрации"""
        
        # Проверяем успешные сообщения
        if page_interface.success_messages:
            success_keywords = ['success', 'registered', 'welcome', 'confirmed', 'activated', 'complete', 'verify']
            for message in page_interface.success_messages:
                if any(keyword in message.lower() for keyword in success_keywords):
                    return {
                        'completed': True,
                        'reason': f'Найдено сообщение об успехе: {message}'
                    }
        
        # Проверяем тип страницы
        completion_page_types = ['success', 'welcome', 'dashboard', 'profile', 'verification_sent', 'email_verification']
        if page_interface.page_type in completion_page_types:
            return {
                'completed': True,
                'reason': f'Достигнута страница завершения: {page_interface.page_type}'
            }
        
        # Проверяем URL
        completion_urls = ['success', 'welcome', 'dashboard', 'complete', 'verified', 'confirm']
        if any(url_part in page_interface.url.lower() for url_part in completion_urls):
            return {
                'completed': True,
                'reason': f'URL указывает на завершение: {page_interface.url}'
            }
        
        # Проверяем заголовок страницы
        if page_interface.title:
            completion_titles = ['welcome', 'success', 'registered', 'dashboard', 'profile', 'verify']
            if any(title_part in page_interface.title.lower() for title_part in completion_titles):
                return {
                    'completed': True,
                    'reason': f'Заголовок указывает на завершение: {page_interface.title}'
                }
        
        return {'completed': False, 'reason': 'Регистрация не завершена'}
    
    async def _prepare_action_data(self, action: Dict[str, Any], page_interface: PageInterface) -> Dict[str, Any]:
        """Подготавливает данные для выполнения действия"""
        
        action_type = action.get('action')
        selector = action.get('selector', '')
        
        # Находим элемент по селектору
        target_element = None
        for element in page_interface.interactive_elements:
            if element.selector == selector:
                target_element = element
                break
        
        if not target_element:
            return {}
        
        # Определяем данные на основе типа элемента
        data = {}
        
        if action_type == 'fill_field':
            field_value = self._determine_field_value(target_element)
            if field_value:
                data[target_element.attributes.get('name', 'value')] = field_value
        
        return data
    
    def _determine_field_value(self, element) -> str:
        """Определяет значение для заполнения поля на основе анализа элемента"""
        
        # Получаем контекстную информацию об элементе
        name = element.attributes.get('name', '').lower()
        placeholder = element.placeholder.lower()
        field_type = element.attributes.get('type', 'text').lower()
        element_text = element.text.lower()
        
        # Объединяем всю контекстную информацию
        context = f"{name} {placeholder} {element_text}".lower()
        
        # Определяем тип поля и возвращаем соответствующее значение
        if any(keyword in context for keyword in ['email', 'mail', 'e-mail']):
            return self.user_data.get('email', 'test@example.com')
        elif any(keyword in context for keyword in ['username', 'login', 'user']):
            return self.user_data.get('username', 'testuser123')
        elif any(keyword in context for keyword in ['password', 'pass']):
            return self.user_data.get('password', 'TestPassword123!')
        elif any(keyword in context for keyword in ['first', 'fname', 'name']) and 'last' not in context:
            return self.user_data.get('first_name', 'John')
        elif any(keyword in context for keyword in ['last', 'lname', 'surname']):
            return self.user_data.get('last_name', 'Doe')
        elif any(keyword in context for keyword in ['phone', 'tel', 'mobile']):
            return self.user_data.get('phone', '+1234567890')
        elif any(keyword in context for keyword in ['birth', 'birthday', 'date']):
            return self.user_data.get('birthday', '01/15/1990')
        
        return ''
    
    async def _fallback_analysis(self, page: Page) -> bool:
        """Запасной анализ если основной не сработал"""
        try:
            # Старый метод анализа
            analysis = await self._analyze_page(page)
            
            if analysis.get('has_form'):
                print("🔄 Использую запасной метод анализа...")
                # Выполняем базовые действия
                return await self._execute_basic_registration(page, analysis)
        except Exception as e:
            print(f"❌ Ошибка запасного анализа: {e}")
        
        return False
    
    async def _setup_page(self, page: Page):
        """Настройка страницы для обхода защиты"""
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        """)
    
    async def _analyze_page(self, page: Page) -> Dict[str, Any]:
        """Анализ текущей страницы (старый метод)"""
        # Скриншот
        screenshot = await page.screenshot(full_page=True)
        
        # Текст страницы
        page_text = await page.inner_text('body')
        
        # HTML
        html_content = await page.content()
        
        # Анализ с помощью Gemini
        return await self.ai_analyzer.analyze_page(screenshot, page_text, html_content)
    
    async def _execute_basic_registration(self, page: Page, analysis: Dict) -> bool:
        """Базовая регистрация (запасной метод)"""
        try:
            # Пытаемся найти и заполнить основные поля
            await self._fill_basic_fields(page)
            
            # Ищем кнопку отправки
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]', 
                'button:has-text("Register")',
                'button:has-text("Sign up")',
                '.submit-btn'
            ]
            
            for selector in submit_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    await page.wait_for_load_state('networkidle', timeout=5000)
                    return True
                except:
                    continue
                    
        except Exception as e:
            print(f"❌ Ошибка базовой регистрации: {e}")
        
        return False
    
    async def _fill_basic_fields(self, page: Page):
        """Заполняет базовые поля формы"""
        
        basic_fields = [
            ('input[name*="email"]', self.user_data.get('email', 'test@example.com')),
            ('input[name*="username"]', self.user_data.get('username', 'testuser123')),
            ('input[name*="password"]', self.user_data.get('password', 'TestPassword123!')),
            ('input[name*="first"]', self.user_data.get('first_name', 'John')),
            ('input[name*="last"]', self.user_data.get('last_name', 'Doe')),
        ]
        
        for selector, value in basic_fields:
            try:
                if await page.is_visible(selector):
                    await page.fill(selector, value)
                    print(f"✅ Заполнено поле: {selector}")
            except:
                continue
    
    async def collect_user_data(self):
        """Сбор данных пользователя"""
        questions = [
            inquirer.Text('email', message="Email адрес"),
            inquirer.Text('username', message="Имя пользователя"),
            inquirer.Password('password', message="Пароль"),
            inquirer.Text('first_name', message="Имя"),
            inquirer.Text('last_name', message="Фамилия"),
            inquirer.Text('phone', message="Телефон (необязательно)", default=""),
            inquirer.Text('birthday', message="Дата рождения (MM/DD/YYYY, необязательно)", default=""),
        ]
        
        self.user_data = inquirer.prompt(questions)
        print("✅ Данные пользователя собраны")
    
    def get_registration_report(self) -> Dict[str, Any]:
        """Возвращает отчет о процессе регистрации"""
        
        total_steps = len(self.registration_steps)
        successful_steps = len([step for step in self.registration_steps if step['result'].success])
        failed_steps = total_steps - successful_steps
        
        pages_visited = list(set([step['page_type'] for step in self.registration_steps]))
        
        return {
            'total_steps': total_steps,
            'successful_steps': successful_steps,
            'failed_steps': failed_steps,
            'success_rate': successful_steps / total_steps if total_steps > 0 else 0,
            'pages_visited': pages_visited,
            'interface_summary': self.interface_agent.get_interaction_summary(),
            'steps_detail': self.registration_steps
        }
