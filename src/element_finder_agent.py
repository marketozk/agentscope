"""
Умный ReAct Agent для поиска веб-элементов
Использует рассуждение → действие → наблюдение для нахождения элементов
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit
from agentscope.message import Msg
from pydantic import BaseModel

class ElementSearchResult(BaseModel):
    """Структурированный результат поиска элемента"""
    selector: str
    confidence: float
    alternative_selectors: List[str]
    element_type: str
    reasoning: str
    success: bool

class WebElementToolkit(Toolkit):
    """Набор инструментов для поиска веб-элементов"""
    
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.register_tool_function(self.analyze_page_structure)
        self.register_tool_function(self.find_by_text)
        self.register_tool_function(self.find_by_xpath)
        self.register_tool_function(self.find_by_css)
        self.register_tool_function(self.find_buttons)
        self.register_tool_function(self.find_inputs)
        self.register_tool_function(self.test_selector)
    
    async def analyze_page_structure(self) -> str:
        """Анализирует структуру страницы"""
        try:
            # Получаем основную информацию о странице
            title = await self.page.title()
            url = self.page.url
            
            # Считаем основные элементы
            buttons_count = await self.page.locator('button, [role="button"], input[type="submit"]').count()
            inputs_count = await self.page.locator('input, textarea, select').count()
            forms_count = await self.page.locator('form').count()
            
            # Получаем текст всех кнопок
            buttons = await self.page.query_selector_all('button, [role="button"], input[type="submit"]')
            button_texts = []
            for button in buttons[:10]:  # Первые 10 кнопок
                try:
                    text = await button.text_content()
                    if text and text.strip():
                        button_texts.append(text.strip()[:50])
                except:
                    pass
            
            return f"""
Структура страницы:
- URL: {url}
- Заголовок: {title}
- Кнопок: {buttons_count}
- Полей ввода: {inputs_count}
- Форм: {forms_count}
- Тексты кнопок: {button_texts}
"""
        except Exception as e:
            return f"Ошибка анализа страницы: {e}"
    
    async def find_by_text(self, text: str) -> str:
        """Ищет элементы по тексту"""
        try:
            # Пробуем разные варианты поиска по тексту
            selectors = [
                f'text="{text}"',
                f'button:has-text("{text}")',
                f'[aria-label*="{text}"]',
                f'xpath=//button[contains(text(),"{text}")]',
                f'xpath=//*[contains(text(),"{text}")]'
            ]
            
            found = []
            for selector in selectors:
                try:
                    count = await self.page.locator(selector).count()
                    if count > 0:
                        found.append(f"{selector} ({count} элементов)")
                except:
                    pass
            
            return f"Найдено по тексту '{text}': {found}" if found else f"Не найдено по тексту '{text}'"
        except Exception as e:
            return f"Ошибка поиска по тексту: {e}"
    
    async def find_by_xpath(self, xpath: str) -> str:
        """Тестирует XPath селектор"""
        try:
            count = await self.page.locator(f"xpath={xpath}").count()
            return f"XPath '{xpath}' найден: {count} элементов"
        except Exception as e:
            return f"Ошибка XPath '{xpath}': {e}"
    
    async def find_by_css(self, css: str) -> str:
        """Тестирует CSS селектор"""
        try:
            count = await self.page.locator(css).count()
            return f"CSS '{css}' найден: {count} элементов"
        except Exception as e:
            return f"Ошибка CSS '{css}': {e}"
    
    async def find_buttons(self) -> str:
        """Находит все кнопки на странице с их атрибутами"""
        try:
            buttons = await self.page.query_selector_all('button, [role="button"], input[type="submit"]')
            button_info = []
            
            for i, button in enumerate(buttons[:15]):  # Первые 15 кнопок
                try:
                    text = await button.text_content() or ""
                    tag = await button.evaluate("el => el.tagName")
                    classes = await button.get_attribute("class") or ""
                    aria_label = await button.get_attribute("aria-label") or ""
                    btn_type = await button.get_attribute("type") or ""
                    
                    info = f"{i+1}. {tag}"
                    if text.strip():
                        info += f" text='{text.strip()[:30]}'"
                    if classes:
                        info += f" class='{classes[:30]}'"
                    if aria_label:
                        info += f" aria='{aria_label[:30]}'"
                    if btn_type:
                        info += f" type='{btn_type}'"
                    
                    button_info.append(info)
                except:
                    button_info.append(f"{i+1}. (ошибка получения данных)")
            
            return "Найденные кнопки:\n" + "\n".join(button_info)
        except Exception as e:
            return f"Ошибка поиска кнопок: {e}"
    
    async def find_inputs(self) -> str:
        """Находит все поля ввода"""
        try:
            inputs = await self.page.query_selector_all('input, textarea, select')
            input_info = []
            
            for i, inp in enumerate(inputs[:10]):
                try:
                    tag = await inp.evaluate("el => el.tagName")
                    inp_type = await inp.get_attribute("type") or ""
                    placeholder = await inp.get_attribute("placeholder") or ""
                    name = await inp.get_attribute("name") or ""
                    
                    info = f"{i+1}. {tag}"
                    if inp_type:
                        info += f" type='{inp_type}'"
                    if placeholder:
                        info += f" placeholder='{placeholder[:30]}'"
                    if name:
                        info += f" name='{name}'"
                    
                    input_info.append(info)
                except:
                    input_info.append(f"{i+1}. (ошибка)")
            
            return "Найденные поля:\n" + "\n".join(input_info)
        except Exception as e:
            return f"Ошибка поиска полей: {e}"
    
    async def test_selector(self, selector: str) -> str:
        """Тестирует любой селектор"""
        try:
            count = await self.page.locator(selector).count()
            if count > 0:
                # Получаем информацию о первом найденном элементе
                element = self.page.locator(selector).first
                try:
                    text = await element.text_content() or ""
                    tag = await element.evaluate("el => el.tagName")
                    classes = await element.get_attribute("class") or ""
                    return f"✅ Селектор '{selector}' найден: {count} элементов. Первый: {tag} text='{text[:30]}' class='{classes[:30]}'"
                except:
                    return f"✅ Селектор '{selector}' найден: {count} элементов"
            else:
                return f"❌ Селектор '{selector}' не найден"
        except Exception as e:
            return f"❌ Ошибка селектора '{selector}': {e}"

class ElementFinderAgent(ReActAgent):
    """ReAct Agent для умного поиска веб-элементов"""
    
    def __init__(self, page, model):
        # Создаем toolkit для этого агента
        toolkit = WebElementToolkit(page)
        
        # Сначала инициализируем родительский класс со всеми нужными параметрами
        super().__init__(
            name="ElementFinder",
            model=model,
            memory=InMemoryMemory(),
            toolkit=toolkit,
            formatter=None,  # Исправляем название параметра
            sys_prompt="""Ты - эксперт по поиску веб-элементов. Твоя задача - найти нужный элемент на странице любой ценой.

СТРАТЕГИЯ ReAct:
1. РАССУЖДЕНИЕ: Анализируй задачу и доступную информацию
2. ДЕЙСТВИЕ: Используй инструменты для поиска и анализа
3. НАБЛЮДЕНИЕ: Оцени результаты
4. Повторяй до успеха

ИНСТРУМЕНТЫ:
- analyze_page_structure() - анализ страницы
- find_by_text(text) - поиск по тексту
- find_by_xpath(xpath) - тест XPath
- find_by_css(css) - тест CSS
- find_buttons() - все кнопки
- find_inputs() - все поля
- test_selector(selector) - тест селектора

ПРИНЦИПЫ:
- Пробуй разные подходы
- Анализируй структуру страницы
- Ищи альтернативы
- Возвращай JSON с селектором

ФОРМАТ ОТВЕТА (JSON):
{
    "selector": "найденный_селектор",
    "confidence": 0.9,
    "alternative_selectors": ["альтернатива1", "альтернатива2"],
    "element_type": "button|input|link",
    "reasoning": "объяснение_поиска",
    "success": true
}"""
        )
        
        # Теперь можно устанавливать дополнительные атрибуты
        self.page = page
        self.toolkit = toolkit
    
    async def find_element(self, description: str, element_type: str = "button") -> ElementSearchResult:
        """Главный метод поиска элемента"""
        try:
            # Создаём сообщение для агента
            task_msg = Msg(
                name="user",
                content=f"""Найди элемент на веб-странице:

ЗАДАЧА: {description}
ТИП ЭЛЕМЕНТА: {element_type}

Используй инструменты для анализа страницы и поиска элемента.
Верни JSON с результатами поиска в формате:
{{
    "selector": "найденный селектор",
    "confidence": 0.8,
    "alternative_selectors": ["альтернативы"],
    "element_type": "{element_type}",
    "reasoning": "объяснение поиска",
    "success": true
}}""",
                role="user"
            )
            
            # Агент анализирует и ищет элемент
            response = await self(task_msg)
            
            # Парсим результат
            return self._parse_response(response.content)
            
        except Exception as e:
            return ElementSearchResult(
                selector="",
                confidence=0.0,
                alternative_selectors=[],
                element_type=element_type,
                reasoning=f"Ошибка агента: {e}",
                success=False
            )
    
    def _parse_response(self, content: str) -> ElementSearchResult:
        """Парсит ответ агента в структурированный результат"""
        try:
            # Ищем JSON в ответе
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return ElementSearchResult(**data)
            
            # Если JSON не найден, создаём базовый результат
            return ElementSearchResult(
                selector="",
                confidence=0.0,
                alternative_selectors=[],
                element_type="unknown",
                reasoning=content,
                success=False
            )
            
        except Exception as e:
            return ElementSearchResult(
                selector="",
                confidence=0.0,
                alternative_selectors=[],
                element_type="unknown",
                reasoning=f"Ошибка парсинга: {e}\nОтвет: {content}",
                success=False
            )
