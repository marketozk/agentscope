"""
Интеллектуальный агент для взаимодействия с веб-интерфейсами
"""
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import logging
from playwright.async_api import Page
from .page_analyzer import WebPageAnalyzer, PageInterface, InterfaceMemory, PageElement

@dataclass 
class ActionResult:
    """Результат выполнения действия"""
    success: bool
    action: Dict[str, Any]
    message: str
    page_changed: bool
    new_elements_found: List[str]
    errors: List[str]

class InterfaceInteractionAgent:
    """Агент для интеллектного взаимодействия с веб-интерфейсами"""
    
    def __init__(self, gemini_api_key: str):
        self.page_analyzer = WebPageAnalyzer(gemini_api_key)
        self.memory = InterfaceMemory()
        self.logger = logging.getLogger("InterfaceAgent")
        self.current_page_interface: Optional[PageInterface] = None
        self.interaction_history: List[Dict] = []
        
        # Кэш для анализов страниц (URL -> результат анализа)
        self.page_analysis_cache: Dict[str, PageInterface] = {}
        self.cache_ttl = 300  # 5 минут
        self.last_cache_cleanup = 0
        
    async def analyze_and_remember_page(self, page: Page) -> PageInterface:
        """Анализирует страницу и запоминает её паттерн"""
        
        self.logger.info(f"Анализирую страницу: {page.url}")
        
        # Проверяем кэш
        cache_key = page.url
        if cache_key in self.page_analysis_cache:
            self.logger.info("Используем кэшированный результат анализа")
            page_interface = self.page_analysis_cache[cache_key]
        else:
            # Полный анализ страницы
            page_interface = await self.page_analyzer.analyze_page_complete(page)
            
            # Сохраняем в кэш
            self.page_analysis_cache[cache_key] = page_interface
            self.logger.info("Результат анализа сохранен в кэш")
        
        self.current_page_interface = page_interface
        
        # Запоминаем паттерн
        url_pattern = self._extract_url_pattern(page.url)
        self.memory.remember_page_pattern(url_pattern, page_interface)
        
        # Логируем результаты
        self.logger.info(f"Страница проанализирована:")
        self.logger.info(f"  Тип: {page_interface.page_type}")
        self.logger.info(f"  Интерактивных элементов: {len(page_interface.interactive_elements)}")
        self.logger.info(f"  Рекомендованных действий: {len(page_interface.recommended_actions)}")
        
        if page_interface.error_messages:
            self.logger.warning(f"  Найдены ошибки: {page_interface.error_messages}")
            
        if page_interface.success_messages:
            self.logger.info(f"  Найдены сообщения об успехе: {page_interface.success_messages}")
        
        return page_interface
    
    async def suggest_next_actions(self, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Предлагает следующие действия на основе анализа"""
        
        if not self.current_page_interface:
            return []
        
        suggestions = []
        
        # Проверяем запомненные паттерны
        remembered_pattern = self.memory.get_pattern_for_url(self.current_page_interface.url)
        if remembered_pattern:
            suggestions.extend(remembered_pattern.get('recommended_actions', []))
        
        # Добавляем действия с текущей страницы
        suggestions.extend(self.current_page_interface.recommended_actions)
        
        # Приоритизируем действия на основе контекста
        if context:
            suggestions = self._prioritize_actions(suggestions, context)
        
        # Убираем дубликаты
        unique_suggestions = []
        seen_actions = set()
        
        for suggestion in suggestions:
            action_key = f"{suggestion.get('action')}_{suggestion.get('selector', '')}"
            if action_key not in seen_actions:
                unique_suggestions.append(suggestion)
                seen_actions.add(action_key)
        
        return unique_suggestions[:10]  # Возвращаем топ-10
    
    async def execute_action(self, page: Page, action: Dict[str, Any], data: Dict[str, Any] = None) -> ActionResult:
        """Выполняет действие на странице"""
        
        action_type = action.get('action')
        selector = action.get('selector')
        
        self.logger.info(f"Выполняю действие: {action_type} на {selector}")
        
        try:
            if action_type == 'fill_field':
                return await self._fill_field(page, action, data)
            elif action_type == 'click_button':
                return await self._click_button(page, action)
            elif action_type == 'select_option':
                return await self._select_option(page, action, data)
            elif action_type == 'upload_file':
                return await self._upload_file(page, action, data)
            elif action_type == 'wait_for_element':
                return await self._wait_for_element(page, action)
            else:
                return ActionResult(
                    success=False,
                    action=action,
                    message=f"Неизвестный тип действия: {action_type}",
                    page_changed=False,
                    new_elements_found=[],
                    errors=[f"Неизвестный тип действия: {action_type}"]
                )
                
        except Exception as e:
            error_msg = f"Ошибка выполнения действия {action_type}: {str(e)}"
            self.logger.error(error_msg)
            
            # Запоминаем неудачное действие
            self.memory.remember_failed_action(action, page.url, str(e))
            
            return ActionResult(
                success=False,
                action=action,
                message=error_msg,
                page_changed=False,
                new_elements_found=[],
                errors=[str(e)]
            )
    
    async def _fill_field(self, page: Page, action: Dict, data: Dict) -> ActionResult:
        """Заполняет поле ввода"""
        selector = action.get('selector')
        field_name = action.get('field_name', '')
        field_type = action.get('field_type', 'text')
        
        # Получаем значение для заполнения
        if data and field_name in data:
            value = str(data[field_name])
        elif 'value' in action:
            value = str(action['value'])
        else:
            # Генерируем тестовые данные
            value = self._generate_test_value(field_name, field_type, selector)
            if not value:
                return ActionResult(
                    success=False,
                    action=action,
                    message=f"Не найдено значение для поля {field_name}",
                    page_changed=False,
                    new_elements_found=[],
                    errors=[f"Отсутствует значение для {field_name}"]
                )
        
        # Ждем появления элемента
        try:
            await page.wait_for_selector(selector, timeout=5000)
            
            # Очищаем поле и заполняем
            await page.fill(selector, value)
            
            # Проверяем, что значение заполнилось
            filled_value = await page.input_value(selector)
            
            success = filled_value == value
            message = f"Поле {field_name} заполнено: {value}" if success else f"Не удалось заполнить поле {field_name}"
            
            if success:
                self.memory.remember_successful_action(action, page.url)
            
            return ActionResult(
                success=success,
                action=action,
                message=message,
                page_changed=False,
                new_elements_found=[],
                errors=[] if success else [f"Заполнение поля не удалось"]
            )
            
        except Exception as e:
            error_msg = f"Ошибка заполнения поля {field_name}: {e}"
            return ActionResult(
                success=False,
                action=action,
                message=error_msg,
                page_changed=False,
                new_elements_found=[],
                errors=[error_msg]
            )
    
    def _generate_test_value(self, field_name: str, field_type: str, selector: str) -> str:
        """Генерирует тестовое значение для поля"""
        import random
        import string
        
        field_name_lower = field_name.lower()
        selector_lower = selector.lower()
        
        # Определяем тип поля по имени или селектору
        if any(keyword in field_name_lower for keyword in ['firstname', 'first_name', 'fname']):
            return 'Тест'
        elif any(keyword in field_name_lower for keyword in ['lastname', 'last_name', 'lname', 'surname']):
            return 'Пользователь'
        elif any(keyword in field_name_lower for keyword in ['email', 'e-mail']):
            return f"test{''.join(random.choices(string.digits, k=4))}@example.com"
        elif any(keyword in field_name_lower for keyword in ['phone', 'tel', 'mobile']):
            return '+7900123456'
        elif any(keyword in field_name_lower for keyword in ['password', 'pwd']):
            return 'TestPass123!'
        elif any(keyword in field_name_lower for keyword in ['username', 'login']):
            return f"testuser{''.join(random.choices(string.digits, k=3))}"
        elif any(keyword in field_name_lower for keyword in ['age']):
            return str(random.randint(18, 65))
        elif any(keyword in field_name_lower for keyword in ['city', 'город']):
            return 'Москва'
        elif any(keyword in field_name_lower for keyword in ['country', 'страна']):
            return 'Россия'
        
        # Проверяем по селектору
        if 'firstname' in selector_lower or 'first-name' in selector_lower:
            return 'Тест'
        elif 'lastname' in selector_lower or 'last-name' in selector_lower:
            return 'Пользователь'
        elif 'email' in selector_lower:
            return f"test{''.join(random.choices(string.digits, k=4))}@example.com"
        
        # Проверяем по типу поля
        if field_type == 'email':
            return f"test{''.join(random.choices(string.digits, k=4))}@example.com"
        elif field_type == 'tel':
            return '+7900123456'
        elif field_type == 'password':
            return 'TestPass123!'
        elif field_type == 'number':
            return str(random.randint(1, 100))
        
        # Дефолтное значение
        return f"TestValue{''.join(random.choices(string.digits, k=3))}"
    
    async def _click_button(self, page: Page, action: Dict) -> ActionResult:
        """Нажимает кнопку"""
        selector = action.get('selector')
        
        try:
            # Ждем появления кнопки
            await page.wait_for_selector(selector, timeout=5000)
            
            # Проверяем, что кнопка видима и активна
            is_visible = await page.is_visible(selector)
            is_enabled = await page.is_enabled(selector)
            
            if not is_visible:
                return ActionResult(
                    success=False,
                    action=action,
                    message="Кнопка не видна",
                    page_changed=False,
                    new_elements_found=[],
                    errors=["Кнопка не видна"]
                )
            
            if not is_enabled:
                return ActionResult(
                    success=False,
                    action=action,
                    message="Кнопка неактивна",
                    page_changed=False,
                    new_elements_found=[],
                    errors=["Кнопка неактивна"]
                )
            
            # Сохраняем URL до клика
            old_url = page.url
            
            # Кликаем
            await page.click(selector)
            
            # Ждем возможного изменения страницы
            try:
                await page.wait_for_load_state('networkidle', timeout=3000)
            except:
                pass
            
            # Проверяем изменение страницы
            new_url = page.url
            page_changed = old_url != new_url
            
            # Если страница изменилась, анализируем новые элементы
            new_elements = []
            if page_changed:
                await asyncio.sleep(1)  # Даем время загрузиться
                new_interface = await self.page_analyzer.analyze_page_complete(page)
                new_elements = [elem.selector for elem in new_interface.interactive_elements]
                self.current_page_interface = new_interface
            
            self.memory.remember_successful_action(action, page.url)
            
            return ActionResult(
                success=True,
                action=action,
                message=f"Кнопка нажата успешно",
                page_changed=page_changed,
                new_elements_found=new_elements,
                errors=[]
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                action=action,
                message=f"Ошибка нажатия кнопки: {str(e)}",
                page_changed=False,
                new_elements_found=[],
                errors=[str(e)]
            )
    
    async def _select_option(self, page: Page, action: Dict, data: Dict) -> ActionResult:
        """Выбирает опцию из выпадающего списка"""
        selector = action.get('selector')
        option_value = data.get(action.get('field_name', ''), action.get('value'))
        
        try:
            await page.wait_for_selector(selector, timeout=5000)
            
            # Пытаемся выбрать по значению
            try:
                await page.select_option(selector, value=str(option_value))
            except:
                # Если не получилось по значению, пытаемся по тексту
                await page.select_option(selector, label=str(option_value))
            
            self.memory.remember_successful_action(action, page.url)
            
            return ActionResult(
                success=True,
                action=action,
                message=f"Опция выбрана: {option_value}",
                page_changed=False,
                new_elements_found=[],
                errors=[]
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                action=action,
                message=f"Ошибка выбора опции: {str(e)}",
                page_changed=False,
                new_elements_found=[],
                errors=[str(e)]
            )
    
    async def _upload_file(self, page: Page, action: Dict, data: Dict) -> ActionResult:
        """Загружает файл"""
        selector = action.get('selector')
        file_path = data.get('file_path', action.get('file_path'))
        
        if not file_path:
            return ActionResult(
                success=False,
                action=action,
                message="Не указан путь к файлу",
                page_changed=False,
                new_elements_found=[],
                errors=["Отсутствует путь к файлу"]
            )
        
        try:
            await page.wait_for_selector(selector, timeout=5000)
            await page.set_input_files(selector, file_path)
            
            self.memory.remember_successful_action(action, page.url)
            
            return ActionResult(
                success=True,
                action=action,
                message=f"Файл загружен: {file_path}",
                page_changed=False,
                new_elements_found=[],
                errors=[]
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                action=action,
                message=f"Ошибка загрузки файла: {str(e)}",
                page_changed=False,
                new_elements_found=[],
                errors=[str(e)]
            )
    
    async def _wait_for_element(self, page: Page, action: Dict) -> ActionResult:
        """Ждет появления элемента"""
        selector = action.get('selector')
        timeout = action.get('timeout', 10000)
        
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            
            return ActionResult(
                success=True,
                action=action,
                message=f"Элемент появился: {selector}",
                page_changed=False,
                new_elements_found=[selector],
                errors=[]
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                action=action,
                message=f"Элемент не появился: {selector}",
                page_changed=False,
                new_elements_found=[],
                errors=[str(e)]
            )
    
    def _extract_url_pattern(self, url: str) -> str:
        """Извлекает паттерн URL для запоминания"""
        # Убираем параметры запроса и хэш
        base_url = url.split('?')[0].split('#')[0]
        
        # Заменяем числовые ID на плейсхолдеры
        import re
        pattern = re.sub(r'/\d+/', '/ID/', base_url)
        pattern = re.sub(r'/\d+$', '/ID', pattern)
        
        return pattern
    
    def _prioritize_actions(self, actions: List[Dict], context: Dict) -> List[Dict]:
        """Приоритизирует действия на основе контекста"""
        
        # Добавляем приоритеты на основе контекста
        for action in actions:
            base_priority = action.get('priority', 0)
            
            # Увеличиваем приоритет для обязательных полей
            if action.get('action') == 'fill_field' and context.get('required_fields'):
                field_name = action.get('field_name', '')
                if field_name in context['required_fields']:
                    action['priority'] = base_priority + 2
            
            # Увеличиваем приоритет для кнопок отправки
            if action.get('action') == 'click_button':
                button_text = action.get('description', '').lower()
                if any(word in button_text for word in ['submit', 'send', 'register', 'login', 'continue']):
                    action['priority'] = base_priority + 1
        
        # Сортируем по приоритету
        actions.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        return actions
    
    def get_interaction_summary(self) -> Dict[str, Any]:
        """Возвращает сводку взаимодействий"""
        successful_actions = len(self.memory.successful_actions)
        failed_actions = len(self.memory.failed_actions)
        remembered_patterns = len(self.memory.page_patterns)
        
        return {
            'successful_actions': successful_actions,
            'failed_actions': failed_actions,
            'remembered_patterns': remembered_patterns,
            'current_page_type': self.current_page_interface.page_type if self.current_page_interface else None,
            'last_errors': [action['error'] for action in self.memory.failed_actions[-5:]],
            'interaction_history_length': len(self.interaction_history)
        }
