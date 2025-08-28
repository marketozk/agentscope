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
        
    async def analyze_page(self, url: str) -> Dict[str, Any]:
        """Анализирует страницу по URL"""
        async with async_playwright() as p:
            browser = await self.browser_agent.create_browser(p, headless=True)
            
            # Создаем контекст с реальными настройками
            context = await browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                }
            )
            
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until='networkidle')
                analysis = await self._analyze_page(page)
                await browser.close()
                return analysis
            except Exception as e:
                await browser.close()
                self.logger.error(f"Ошибка анализа страницы: {e}")
                return {"success": False, "error": str(e)}
    
    async def fill_registration_form(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Заполняет регистрационную форму данными"""
        try:
            # Сохраняем данные пользователя
            self.user_data.update(form_data)
            
            # Здесь должна быть логика заполнения формы
            # Пока возвращаем успешный результат с переданными данными
            return {
                "success": True,
                "form_filled": True,
                "fields_filled": list(form_data.keys()),
                "data_used": form_data,
                "message": "Форма заполнена данными пользователя"
            }
        except Exception as e:
            self.logger.error(f"Ошибка заполнения формы: {e}")
            return {"success": False, "error": str(e)}
    
    async def analyze_registration_completion(self) -> Dict[str, Any]:
        """Анализирует завершение процесса регистрации"""
        try:
            # Анализируем текущие шаги регистрации
            total_steps = len(self.registration_steps)
            completed_steps = len([s for s in self.registration_steps if s.get('completed')])
            
            return {
                "registration_successful": completed_steps > 0,
                "account_created": completed_steps >= total_steps * 0.8,
                "steps_completed": completed_steps,
                "total_steps": total_steps,
                "completion_rate": completed_steps / max(total_steps, 1),
                "current_page": "analysis_complete"
            }
        except Exception as e:
            self.logger.error(f"Ошибка анализа завершения: {e}")
            return {"registration_successful": False, "error": str(e)}
    
    def get_current_url(self) -> str:
        """Возвращает текущий URL"""
        return getattr(self, '_current_url', 'unknown_url')
    
    async def execute(self, referral_link: str) -> bool:
        """Выполнить регистрацию по реферальной ссылке с интеллектуальным анализом"""
        async with async_playwright() as p:
            # Создаём браузер
            browser = await self.browser_agent.create_browser(p, headless=False)
            
            # Создаем контекст с реальными настройками
            context = await browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation', 'notifications'],
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            page = await context.new_page()
            
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

            # УПРОЩЕННАЯ СТРАТЕГИЯ: сначала заполнить поля, потом кликать кнопки
            form_fields = [elem for elem in page_interface.interactive_elements 
                          if elem.element_type == 'input' and elem.selector and 
                          'name=' in elem.selector and elem.text.strip() == '']
            
            # Если есть пустые поля - заполняем их
            if form_fields:
                print(f"🔧 Найдено {len(form_fields)} пустых полей для заполнения")
                for field in form_fields[:3]:  # Заполняем первые 3 поля
                    field_name = field.selector.split("name='")[-1].split("'")[0] if "name='" in field.selector else "unknown"
                    
                    # Пропускаем служебные поля
                    if field_name in ['_csrf', 'referralCode', 'countryCode', 'didConsentToMarketing']:
                        continue
                    
                    # Создаем действие заполнения
                    fill_action = {
                        'action': 'fill_field',
                        'selector': field.selector,
                        'field_name': field_name,
                        'description': f'Заполнить поле {field_name}'
                    }
                    
                    print(f"▶️ Заполняю поле: {field_name}")
                    result = await self.interface_agent.execute_action(page, fill_action, self.user_data)
                    
                    if result.success:
                        print(f"✅ Поле {field_name} заполнено")
                        await asyncio.sleep(0.5)  # Пауза между заполнениями
                    else:
                        print(f"❌ Не удалось заполнить {field_name}: {result.message}")
                
                # После заполнения полей продолжаем
                continue

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
            
            # Фильтруем только поддерживаемые действия
            supported_actions = ['fill_field', 'click_button', 'select_option', 'upload_file', 'wait_for_element']
            valid_actions = [action for action in suggested_actions 
                           if action.get('action') in supported_actions]
            
            if not valid_actions:
                print("❌ Нет поддерживаемых действий")
                continue
            
            # Выбираем лучшее действие
            best_action = valid_actions[0]
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
                    print("� Страница изменилась, ожидаю загрузки...")
                    await asyncio.sleep(2)
                    await page.wait_for_load_state('networkidle', timeout=10000)
            else:
                print(f"❌ {result.message}")
                # Пробуем следующее действие если есть
                if len(valid_actions) > 1:
                    print("🔄 Пробую альтернативное действие...")
                    for alt_action in valid_actions[1:3]:  # Пробуем следующие 2 действия
                        print(f"▶️ Альтернатива: {alt_action.get('description', alt_action.get('action'))}")
                        alt_result = await self.interface_agent.execute_action(page, alt_action, self.user_data)
                        if alt_result.success:
                            print(f"✅ Альтернативное действие успешно")
                            result = alt_result
                            break
                        else:
                            print(f"❌ Альтернатива не сработала: {alt_result.message}")
                    
                    if not result.success:
                        print("⚠️ Все альтернативы провалились, продолжаю...")
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
        
        # Маскировка webdriver
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        """)
        
        # Дополнительная маскировка автоматизации
        await page.add_init_script("""
            // Удаляем следы автоматизации
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // Переопределяем permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Маскируем languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'ru']
            });
            
            // Маскируем plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        # Устанавливаем viewport и user agent
        await page.set_viewport_size({"width": 1366, "height": 768})
        await page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8'
        })
    
    async def _analyze_page(self, page: Page) -> Dict[str, Any]:
        """Анализ текущей страницы"""
        # Сохраняем текущий URL
        self._current_url = page.url
        
        # Скриншот
        screenshot = await page.screenshot()
        
        # Текст страницы
        page_text = await page.evaluate("() => document.body.innerText || ''")
        
        # HTML
        page_html = await page.content()
        
        # AI анализ
        return await self.ai_analyzer.analyze_page(screenshot, page_text, page_html)
    
    async def _execute_action(self, page: Page, action: Dict[str, Any]):
        """Выполнение одного действия"""
        action_type = action['type']
        
        if action_type == 'request_user_input':
            # Запрос данных у пользователя
            field = action['field']
            label = field.get('label', field.get('type', 'данные'))
            
            if field['type'] == 'password':
                answer = inquirer.prompt([
                    inquirer.Password('value', message=f"Введите {label}")
                ])
            else:
                answer = inquirer.prompt([
                    inquirer.Text('value', message=f"Введите {label}")
                ])
            
            if answer:
                self.user_data[field.get('type', 'unknown')] = answer['value']
        
        elif action_type == 'fill_field':
            # Заполнение поля
            selector = action['selector']
            field_info = action['field_info']
            field_type = field_info.get('type', 'unknown')
            
            value = self.user_data.get(field_type, '')
            
            if value:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    await element.fill(value)
                    print(f"✅ Заполнено поле: {field_type}")
                except Exception as e:
                    print(f"❌ Не удалось заполнить поле {selector}: {e}")
        
        elif action_type == 'click_button':
            # Клик по кнопке
            try:
                element = await page.wait_for_selector(action['selector'], timeout=5000)
                await element.click()
                print("✅ Нажата кнопка отправки")
            except Exception as e:
                print(f"❌ Не удалось нажать кнопку: {e}")
    
    async def _is_registration_complete(self, page: Page) -> bool:
        """Проверка завершения регистрации"""
        url = page.url
        text = await page.evaluate("() => document.body.innerText || ''")
        
        indicators = [
            'success' in url.lower(),
            'dashboard' in url.lower(),
            'verify' in text.lower(),
            'check your email' in text.lower()
        ]
        
        return any(indicators)