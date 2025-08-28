"""
Модуль анализа веб-страниц и интерфейсов
"""
import asyncio
import json
import base64
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from PIL import Image
import io
import google.generativeai as genai
from playwright.async_api import Page, ElementHandle
import logging

logger = logging.getLogger(__name__)

@dataclass
class PageElement:
    """Элемент страницы"""
    element_type: str  # input, button, select, link, etc.
    selector: str
    text: str
    attributes: Dict[str, str]
    position: Dict[str, int]  # x, y, width, height
    is_visible: bool
    is_enabled: bool
    required: bool = False
    placeholder: str = ""

@dataclass
class PageInterface:
    """Полный интерфейс страницы"""
    page_type: str
    title: str
    url: str
    elements: List[PageElement]
    forms: List[Dict[str, Any]]
    navigation_elements: List[PageElement]
    interactive_elements: List[PageElement]
    has_captcha: bool
    has_modal: bool
    error_messages: List[str]
    success_messages: List[str]
    recommended_actions: List[Dict[str, Any]]

class WebPageAnalyzer:
    """Анализатор веб-страниц с ИИ"""
    
    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        self.vision_model = genai.GenerativeModel('gemini-1.5-flash')
        self.text_model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Rate limiting для Gemini API
        self.last_request_time = 0
        self.min_delay_between_requests = 3.0  # 3 секунды между запросами
        self.request_count = 0
        self.requests_per_minute = 8  # Консервативный лимит
        self.minute_start = time.time()
        self.logger = logger
        
    async def _wait_for_rate_limit(self):
        """Соблюдение rate limits для Gemini API"""
        current_time = time.time()
        
        # Сброс счетчика каждую минуту
        if current_time - self.minute_start >= 60:
            self.request_count = 0
            self.minute_start = current_time
        
        # Проверка лимита запросов в минуту
        if self.request_count >= self.requests_per_minute:
            wait_time = 60 - (current_time - self.minute_start) + 5  # +5 секунд запаса
            if wait_time > 0:
                self.logger.info(f"Rate limit: ожидание {wait_time:.1f} секунд...")
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.minute_start = time.time()
        
        # Минимальная задержка между запросами
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay_between_requests:
            wait_time = self.min_delay_between_requests - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
    async def analyze_page_complete(self, page: Page) -> PageInterface:
        """Полный анализ страницы"""
        
        # Получаем базовую информацию
        title = await page.title()
        url = page.url
        
        # Делаем скриншот
        screenshot_bytes = await page.screenshot(full_page=True)
        
        # Получаем HTML и текст
        html_content = await page.content()
        page_text = await page.inner_text('body')
        
        # Анализируем элементы DOM
        elements = await self._extract_page_elements(page)
        
        # Анализируем с помощью ИИ
        ai_analysis = await self._ai_analyze_interface(
            screenshot_bytes, page_text, html_content[:10000]
        )
        
        # Группируем элементы по типам
        forms = await self._extract_forms(page)
        navigation_elements = [e for e in elements if e.element_type in ['link', 'nav']]
        interactive_elements = [e for e in elements if e.element_type in ['button', 'input', 'select', 'checkbox', 'radio']]
        
        # Определяем сообщения об ошибках/успехе
        error_messages = await self._find_messages(page, 'error')
        success_messages = await self._find_messages(page, 'success')
        
        # Планируем рекомендованные действия
        recommended_actions = await self._plan_recommended_actions(ai_analysis, elements)
        
        return PageInterface(
            page_type=ai_analysis.get('page_type', 'unknown'),
            title=title,
            url=url,
            elements=elements,
            forms=forms,
            navigation_elements=navigation_elements,
            interactive_elements=interactive_elements,
            has_captcha=ai_analysis.get('has_captcha', False),
            has_modal=await self._check_modal(page),
            error_messages=error_messages,
            success_messages=success_messages,
            recommended_actions=recommended_actions
        )
    
    async def _extract_page_elements(self, page: Page) -> List[PageElement]:
        """Извлекает все интерактивные элементы страницы"""
        elements = []
        
        # Селекторы для поиска элементов
        selectors = {
            'input': 'input',
            'button': 'button, input[type="submit"], input[type="button"]',
            'select': 'select',
            'textarea': 'textarea',
            'link': 'a[href]',
            'checkbox': 'input[type="checkbox"]',
            'radio': 'input[type="radio"]',
            'file': 'input[type="file"]',
            'dropdown': '.dropdown, .select-wrapper'
        }
        
        for element_type, selector in selectors.items():
            try:
                element_handles = await page.query_selector_all(selector)
                
                for handle in element_handles:
                    element_info = await self._get_element_info(handle, element_type)
                    if element_info:
                        elements.append(element_info)
                        
            except Exception as e:
                print(f"Ошибка при поиске {element_type}: {e}")
                
        return elements
    
    async def _get_element_info(self, handle: ElementHandle, element_type: str) -> Optional[PageElement]:
        """Получает информацию об элементе"""
        try:
            # Проверяем видимость
            is_visible = await handle.is_visible()
            is_enabled = await handle.is_enabled()
            
            # Получаем атрибуты
            attributes = {}
            common_attrs = ['id', 'class', 'name', 'type', 'value', 'placeholder', 'required', 'href']
            
            for attr in common_attrs:
                value = await handle.get_attribute(attr)
                if value:
                    attributes[attr] = value
            
            # Получаем текст
            text = await handle.inner_text() or await handle.get_attribute('value') or ""
            
            # Получаем позицию
            box = await handle.bounding_box()
            position = {}
            if box:
                position = {
                    'x': int(box['x']),
                    'y': int(box['y']),
                    'width': int(box['width']),
                    'height': int(box['height'])
                }
            
            # Создаем селектор
            selector = await self._create_selector(handle)
            
            return PageElement(
                element_type=element_type,
                selector=selector,
                text=text.strip(),
                attributes=attributes,
                position=position,
                is_visible=is_visible,
                is_enabled=is_enabled,
                required=attributes.get('required') == 'true' or 'required' in attributes,
                placeholder=attributes.get('placeholder', '')
            )
            
        except Exception as e:
            print(f"Ошибка получения информации об элементе: {e}")
            return None
    
    async def _create_selector(self, handle: ElementHandle) -> str:
        """Создает надежный селектор для элемента"""
        try:
            # Получаем основные атрибуты
            element_id = await handle.get_attribute('id')
            element_name = await handle.get_attribute('name')
            element_class = await handle.get_attribute('class')
            element_type = await handle.get_attribute('type')
            tag_name = await handle.evaluate('el => el.tagName.toLowerCase()')
            
            # Строим селектор по приоритету
            if element_id:
                return f"#{element_id}"
            elif element_name:
                return f"[name='{element_name}']"
            elif element_type and tag_name == 'input':
                return f"input[type='{element_type}']"
            elif element_class:
                classes = element_class.split()
                if classes:
                    return f".{classes[0]}"
            
            return tag_name
            
        except:
            return "unknown"
    
    async def _extract_forms(self, page: Page) -> List[Dict[str, Any]]:
        """Извлекает информацию о формах"""
        forms = []
        
        try:
            form_handles = await page.query_selector_all('form')
            
            for i, form_handle in enumerate(form_handles):
                form_info = {
                    'index': i,
                    'action': await form_handle.get_attribute('action') or '',
                    'method': await form_handle.get_attribute('method') or 'GET',
                    'fields': []
                }
                
                # Находим поля в форме
                field_selectors = ['input', 'select', 'textarea']
                for selector in field_selectors:
                    field_handles = await form_handle.query_selector_all(selector)
                    
                    for field_handle in field_handles:
                        field_info = await self._get_element_info(field_handle, selector)
                        if field_info:
                            form_info['fields'].append(field_info)
                
                forms.append(form_info)
                
        except Exception as e:
            print(f"Ошибка извлечения форм: {e}")
            
        return forms
    
    async def _ai_analyze_interface(self, screenshot: bytes, page_text: str, html: str) -> Dict[str, Any]:
        """ИИ анализ интерфейса страницы"""
        
        image = Image.open(io.BytesIO(screenshot))
        
        prompt = f"""
        Проанализируй этот веб-интерфейс и определи:

        1. Тип страницы (login, registration, verification, dashboard, form, etc.)
        2. Основную цель страницы
        3. Наличие специальных элементов (капча, двухфакторная аутентификация, модальные окна)
        4. Последовательность действий, которые пользователь должен выполнить
        5. Возможные проблемы или препятствия

        Текст со страницы (первые 2000 символов):
        {page_text[:2000]}

        Верни результат в JSON формате:
        {{
            "page_type": "тип страницы",
            "main_purpose": "основная цель",
            "user_journey_step": "этап пользовательского пути",
            "required_actions": [
                {{
                    "action": "действие",
                    "element_type": "тип элемента",
                    "description": "описание",
                    "priority": 1-5
                }}
            ],
            "has_captcha": true/false,
            "has_2fa": true/false,
            "has_modal": true/false,
            "obstacles": ["препятствие1", "препятствие2"],
            "completion_indicators": ["индикатор завершения"],
            "next_expected_page": "ожидаемая следующая страница"
        }}
        """
        
        # Соблюдаем rate limits
        await self._wait_for_rate_limit()
        
        try:
            # Retry механизм для обработки rate limits
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self.vision_model.generate_content([prompt, image])
                    )
                    
                    json_text = response.text.strip()
                    
                    # Очистка от markdown
                    if '```' in json_text:
                        lines = json_text.split('\n')
                        json_lines = []
                        in_json = False
                        for line in lines:
                            if line.strip().startswith('```'):
                                in_json = not in_json
                                continue
                            if in_json:
                                json_lines.append(line)
                        json_text = '\n'.join(json_lines)
                    
                    return json.loads(json_text)
                    
                except Exception as e:
                    error_msg = str(e)
                    if ("429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower()) and attempt < max_retries - 1:
                        # Rate limit - ждем дольше
                        retry_delay = 15 * (2 ** attempt)  # 15, 30, 60 секунд
                        self.logger.warning(f"Rate limit, попытка {attempt + 1}/{max_retries}, ожидание {retry_delay} секунд")
                        await asyncio.sleep(retry_delay)
                        continue
                    raise e
            
        except Exception as e:
            print(f"Ошибка ИИ анализа: {e}")
            return {
                "page_type": "unknown",
                "main_purpose": "unclear",
                "user_journey_step": "unknown",
                "required_actions": [],
                "has_captcha": False,
                "has_2fa": False,
                "has_modal": False,
                "obstacles": [],
                "completion_indicators": [],
                "next_expected_page": "unknown"
            }
    
    async def _find_messages(self, page: Page, message_type: str) -> List[str]:
        """Находит сообщения об ошибках или успехе"""
        messages = []
        
        selectors = {
            'error': [
                '.error', '.alert-danger', '.text-danger', '.invalid-feedback',
                '[class*="error"]', '[class*="danger"]', '.message.error'
            ],
            'success': [
                '.success', '.alert-success', '.text-success', '.valid-feedback',
                '[class*="success"]', '.message.success'
            ]
        }
        
        try:
            for selector in selectors.get(message_type, []):
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        text = await element.inner_text()
                        if text.strip():
                            messages.append(text.strip())
                            
        except Exception as e:
            print(f"Ошибка поиска сообщений {message_type}: {e}")
            
        return messages
    
    async def _check_modal(self, page: Page) -> bool:
        """Проверяет наличие модальных окон"""
        modal_selectors = [
            '.modal', '.popup', '.dialog', '.overlay',
            '[role="dialog"]', '[aria-modal="true"]'
        ]
        
        try:
            for selector in modal_selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        return True
        except:
            pass
            
        return False
    
    async def _plan_recommended_actions(self, ai_analysis: Dict, elements: List[PageElement]) -> List[Dict[str, Any]]:
        """Планирует рекомендованные действия на основе анализа"""
        actions = []
        
        # Добавляем действия из ИИ анализа
        for action in ai_analysis.get('required_actions', []):
            actions.append(action)
        
        # Добавляем действия на основе найденных элементов
        for element in elements:
            if element.element_type == 'input' and element.is_visible and element.is_enabled:
                actions.append({
                    "action": "fill_field",
                    "element_type": "input",
                    "selector": element.selector,
                    "description": f"Заполнить поле: {element.placeholder or element.text}",
                    "priority": 3 if element.required else 2
                })
            elif element.element_type == 'button' and element.is_visible and element.is_enabled:
                actions.append({
                    "action": "click_button",
                    "element_type": "button", 
                    "selector": element.selector,
                    "description": f"Нажать кнопку: {element.text}",
                    "priority": 4 if 'submit' in element.text.lower() else 1
                })
        
        # Сортируем по приоритету
        actions.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        return actions

class InterfaceMemory:
    """Память для интерфейсов и паттернов"""
    
    def __init__(self):
        self.page_patterns: Dict[str, Dict] = {}
        self.successful_actions: List[Dict] = []
        self.failed_actions: List[Dict] = []
        
    def remember_page_pattern(self, url_pattern: str, page_interface: PageInterface):
        """Запоминает паттерн страницы"""
        self.page_patterns[url_pattern] = {
            'page_type': page_interface.page_type,
            'common_elements': [
                {
                    'type': elem.element_type,
                    'selector_pattern': elem.selector,
                    'text_pattern': elem.text
                }
                for elem in page_interface.interactive_elements
            ],
            'recommended_actions': page_interface.recommended_actions
        }
    
    def get_pattern_for_url(self, url: str) -> Optional[Dict]:
        """Получает запомненный паттерн для URL"""
        for pattern, info in self.page_patterns.items():
            if pattern in url:
                return info
        return None
    
    def remember_successful_action(self, action: Dict, page_url: str):
        """Запоминает успешное действие"""
        self.successful_actions.append({
            'action': action,
            'url': page_url,
            'timestamp': asyncio.get_event_loop().time()
        })
    
    def remember_failed_action(self, action: Dict, page_url: str, error: str):
        """Запоминает неудачное действие"""
        self.failed_actions.append({
            'action': action,
            'url': page_url,
            'error': error,
            'timestamp': asyncio.get_event_loop().time()
        })
