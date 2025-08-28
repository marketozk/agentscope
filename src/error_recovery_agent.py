"""
Error Recovery Agent с ReAct парадигмой и hooks
Автономно обрабатывает ошибки и находит решения
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit
from agentscope.message import Msg
from pydantic import BaseModel

class RecoveryAction(BaseModel):
    """Структурированное действие для восстановления"""
    action_type: str  # keyboard, alternative_selector, wait_retry, reanalyze
    parameters: Dict[str, Any]
    confidence: float
    reasoning: str

class RecoveryResult(BaseModel):
    """Результат попытки восстановления"""
    success: bool
    action_taken: str
    result_data: Dict[str, Any]
    next_suggestions: List[RecoveryAction]

class ErrorRecoveryToolkit(Toolkit):
    """Инструменты для восстановления после ошибок"""
    
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.register_tool_function(self.try_keyboard_navigation)
        self.register_tool_function(self.scan_for_alternatives)
        self.register_tool_function(self.wait_and_retry)
        self.register_tool_function(self.analyze_page_changes)
        self.register_tool_function(self.try_form_submission)
        self.register_tool_function(self.get_page_state)
    
    async def try_keyboard_navigation(self, key_combination: str) -> str:
        """Пробует клавиатурную навигацию"""
        try:
            keys_map = {
                "enter": "Enter",
                "tab": "Tab", 
                "space": "Space",
                "escape": "Escape",
                "ctrl+enter": "Control+Enter"
            }
            
            key = keys_map.get(key_combination.lower(), key_combination)
            await self.page.keyboard.press(key)
            
            # Ждём изменений
            await asyncio.sleep(1)
            
            # Проверяем, изменился ли URL (признак успеха)
            new_url = self.page.url
            return f"Нажата клавиша {key}. Новый URL: {new_url}"
            
        except Exception as e:
            return f"Ошибка клавиши {key_combination}: {e}"
    
    async def scan_for_alternatives(self, element_type: str, context: str) -> str:
        """Сканирует страницу на альтернативные элементы"""
        try:
            alternatives = []
            
            if element_type == "button":
                # Ищем все возможные кнопки
                selectors = [
                    "button",
                    "[role='button']",
                    "input[type='submit']",
                    "input[type='button']",
                    "[onclick]",
                    "a[href*='submit']",
                    "a[href*='continue']",
                    "a[href*='next']"
                ]
                
                for selector in selectors:
                    try:
                        count = await self.page.locator(selector).count()
                        if count > 0:
                            # Получаем информацию о найденных элементах
                            elements = await self.page.locator(selector).all()
                            for i, elem in enumerate(elements[:3]):
                                try:
                                    text = await elem.text_content() or ""
                                    classes = await elem.get_attribute("class") or ""
                                    alternatives.append(f"{selector}[{i}]: '{text[:20]}' class='{classes[:20]}'")
                                except:
                                    pass
                    except:
                        pass
            
            elif element_type == "input":
                # Ищем поля ввода
                selectors = [
                    "input:not([type='hidden'])",
                    "textarea",
                    "select",
                    "[contenteditable='true']"
                ]
                
                for selector in selectors:
                    try:
                        count = await self.page.locator(selector).count()
                        if count > 0:
                            alternatives.append(f"{selector}: {count} элементов")
                    except:
                        pass
            
            return f"Альтернативы для {element_type}:\n" + "\n".join(alternatives)
            
        except Exception as e:
            return f"Ошибка сканирования альтернатив: {e}"
    
    async def wait_and_retry(self, seconds: float, check_selector: str = "") -> str:
        """Ждёт и проверяет появление элемента"""
        try:
            await asyncio.sleep(seconds)
            
            if check_selector:
                try:
                    count = await self.page.locator(check_selector).count()
                    return f"После ожидания {seconds}с селектор '{check_selector}': {count} элементов"
                except Exception as e:
                    return f"После ожидания {seconds}с ошибка проверки '{check_selector}': {e}"
            else:
                return f"Ожидание {seconds} секунд завершено"
                
        except Exception as e:
            return f"Ошибка ожидания: {e}"
    
    async def analyze_page_changes(self, previous_url: str = "") -> str:
        """Анализирует изменения на странице"""
        try:
            current_url = self.page.url
            title = await self.page.title()
            
            # Проверяем основные индикаторы изменений
            changes = []
            
            if previous_url and current_url != previous_url:
                changes.append(f"URL изменился: {previous_url} → {current_url}")
            
            # Ищем сообщения об ошибках
            error_selectors = [
                "[class*='error']",
                "[class*='invalid']", 
                "[class*='alert']",
                "[role='alert']"
            ]
            
            for selector in error_selectors:
                try:
                    count = await self.page.locator(selector).count()
                    if count > 0:
                        error_texts = await self.page.locator(selector).all_text_contents()
                        changes.append(f"Ошибки ({selector}): {error_texts[:3]}")
                except:
                    pass
            
            # Ищем индикаторы успеха
            success_selectors = [
                "[class*='success']",
                "[class*='complete']",
                "[class*='welcome']"
            ]
            
            for selector in success_selectors:
                try:
                    count = await self.page.locator(selector).count()
                    if count > 0:
                        success_texts = await self.page.locator(selector).all_text_contents()
                        changes.append(f"Успех ({selector}): {success_texts[:3]}")
                except:
                    pass
            
            result = f"Текущая страница: {current_url}\nЗаголовок: {title}\n"
            if changes:
                result += "Изменения:\n" + "\n".join(changes)
            else:
                result += "Изменений не обнаружено"
            
            return result
            
        except Exception as e:
            return f"Ошибка анализа изменений: {e}"
    
    async def try_form_submission(self) -> str:
        """Пробует отправить форму разными способами"""
        try:
            results = []
            
            # Способ 1: Найти и нажать submit кнопку
            submit_selectors = [
                "input[type='submit']",
                "button[type='submit']", 
                "button:has-text('Submit')",
                "button:has-text('Continue')",
                "button:has-text('Next')",
                "[role='button']:has-text('Submit')"
            ]
            
            for selector in submit_selectors:
                try:
                    count = await self.page.locator(selector).count()
                    if count > 0:
                        await self.page.locator(selector).first.click()
                        results.append(f"✅ Клик по {selector}")
                        await asyncio.sleep(1)
                        return f"Попытка отправки формы: {results[-1]}"
                except Exception as e:
                    results.append(f"❌ {selector}: {e}")
            
            # Способ 2: Enter в активном поле
            try:
                await self.page.keyboard.press("Enter")
                results.append("✅ Enter в активном поле")
                await asyncio.sleep(1)
            except Exception as e:
                results.append(f"❌ Enter: {e}")
            
            return "Попытки отправки формы:\n" + "\n".join(results)
            
        except Exception as e:
            return f"Ошибка отправки формы: {e}"
    
    async def get_page_state(self) -> str:
        """Получает текущее состояние страницы"""
        try:
            url = self.page.url
            title = await self.page.title()
            ready_state = await self.page.evaluate("document.readyState")
            
            # Считаем элементы
            buttons_count = await self.page.locator("button, [role='button']").count()
            inputs_count = await self.page.locator("input, textarea").count()
            forms_count = await self.page.locator("form").count()
            
            return f"""Состояние страницы:
URL: {url}
Заголовок: {title}
Готовность: {ready_state}
Кнопок: {buttons_count}
Полей: {inputs_count}
Форм: {forms_count}"""
            
        except Exception as e:
            return f"Ошибка получения состояния: {e}"

class ErrorRecoveryAgent(ReActAgent):
    """ReAct Agent для восстановления после ошибок"""
    
    def __init__(self, page, model):
        # Создаем toolkit для этого агента
        toolkit = ErrorRecoveryToolkit(page)
        
        # Сначала инициализируем родительский класс со всеми нужными параметрами
        super().__init__(
            name="ErrorRecovery",
            model=model,
            memory=InMemoryMemory(),
            toolkit=toolkit,
            formatter=None,  # Исправляем название параметра
            sys_prompt="""Ты - специалист по восстановлению после ошибок в веб-автоматизации.

ЗАДАЧА: Когда элемент не найден или действие не выполнено, найди альтернативное решение.

СТРАТЕГИЯ ReAct:
1. РАССУЖДЕНИЕ: Анализируй ошибку и контекст
2. ДЕЙСТВИЕ: Пробуй инструменты восстановления  
3. НАБЛЮДЕНИЕ: Оцени результат
4. Повторяй до успеха

ИНСТРУМЕНТЫ:
- try_keyboard_navigation(key) - клавиатура (enter, tab, space)
- scan_for_alternatives(type, context) - поиск альтернатив
- wait_and_retry(seconds, selector) - ожидание
- analyze_page_changes(prev_url) - анализ изменений
- try_form_submission() - отправка формы
- get_page_state() - состояние страницы

ТИПЫ ВОССТАНОВЛЕНИЯ:
1. КЛАВИАТУРА: Enter, Tab, Space для навигации
2. АЛЬТЕРНАТИВЫ: Поиск похожих элементов
3. ОЖИДАНИЕ: Время для загрузки
4. АНАЛИЗ: Понимание изменений страницы

ФОРМАТ ОТВЕТА (JSON):
{
    "action_taken": "описание_действия",
    "success": true/false,
    "next_steps": ["шаг1", "шаг2"],
    "confidence": 0.8
}"""
        )
        
        # Теперь можно устанавливать дополнительные атрибуты
        self.page = page
        self.toolkit = toolkit
    
    async def recover_from_error(self, error_context: Dict[str, Any]) -> RecoveryResult:
        """Восстановление после ошибки"""
        try:
            # Создаём сообщение для агента
            task_msg = Msg(
                name="user", 
                content=f"""ОШИБКА В ВЕБ-АВТОМАТИЗАЦИИ!

Контекст ошибки:
- Тип действия: {error_context.get('action_type', 'unknown')}
- Селектор: {error_context.get('selector', 'unknown')}  
- Описание: {error_context.get('description', 'unknown')}
- URL: {error_context.get('page_url', 'unknown')}
- Обязательное: {error_context.get('required', True)}

Найди способ восстановления! Используй инструменты для:
1. Анализа текущего состояния страницы
2. Поиска альтернативных решений
3. Попытки восстановления

Верни JSON план восстановления в формате:
{{
    "recovery_actions": [
        {{
            "action_type": "keyboard|alternative_selector|wait_retry|form_submit",
            "parameters": {{"key": "enter", "selector": "...", "seconds": 2}},
            "confidence": 0.8,
            "reasoning": "объяснение"
        }}
    ],
    "immediate_action": "keyboard_enter",
    "success_probability": 0.7
}}""",
                role="user"
            )
            
            # Агент анализирует и планирует восстановление
            response = await self(task_msg)
            
            # Выполняем предложенные действия
            return await self._execute_recovery_plan(response.content, error_context)
            
        except Exception as e:
            return RecoveryResult(
                success=False,
                action_taken=f"Ошибка агента восстановления: {e}",
                result_data={},
                next_suggestions=[]
            )
    
    async def _execute_recovery_plan(self, plan_content: str, error_context: Dict) -> RecoveryResult:
        """Выполняет план восстановления"""
        try:
            # Парсим план
            import re
            json_match = re.search(r'\{.*\}', plan_content, re.DOTALL)
            if not json_match:
                # Пробуем базовое восстановление
                return await self._basic_recovery(error_context)
            
            plan = json.loads(json_match.group())
            actions = plan.get('recovery_actions', [])
            
            for action in actions:
                action_type = action.get('action_type')
                parameters = action.get('parameters', {})
                
                if action_type == "keyboard":
                    key = parameters.get('key', 'enter')
                    result = await self.toolkit.try_keyboard_navigation(key)
                    
                    # Проверяем успех по изменению URL
                    await asyncio.sleep(1)
                    if "Новый URL" in result and self.page.url != error_context.get('page_url'):
                        return RecoveryResult(
                            success=True,
                            action_taken=f"Клавиша {key}",
                            result_data={"new_url": self.page.url},
                            next_suggestions=[]
                        )
                
                elif action_type == "form_submit":
                    result = await self.toolkit.try_form_submission()
                    if "✅" in result:
                        return RecoveryResult(
                            success=True,
                            action_taken="Отправка формы",
                            result_data={"method": "form_submit"},
                            next_suggestions=[]
                        )
                
                elif action_type == "wait_retry":
                    seconds = parameters.get('seconds', 2)
                    selector = parameters.get('selector', '')
                    result = await self.toolkit.wait_and_retry(seconds, selector)
                    
                    if selector and "элементов" in result and not "0 элементов" in result:
                        return RecoveryResult(
                            success=True,
                            action_taken=f"Ожидание {seconds}с",
                            result_data={"found_selector": selector},
                            next_suggestions=[]
                        )
            
            return RecoveryResult(
                success=False,
                action_taken="Все попытки восстановления неудачны",
                result_data={"plan": plan},
                next_suggestions=[]
            )
            
        except Exception as e:
            return await self._basic_recovery(error_context)
    
    async def _basic_recovery(self, error_context: Dict) -> RecoveryResult:
        """Базовое восстановление без AI"""
        try:
            # Простые действия восстановления
            original_url = error_context.get('page_url', '')
            
            # 1. Пробуем Enter
            await self.page.keyboard.press('Enter')
            await asyncio.sleep(2)
            if self.page.url != original_url:
                return RecoveryResult(
                    success=True,
                    action_taken="Enter",
                    result_data={"new_url": self.page.url},
                    next_suggestions=[]
                )
            
            # 2. Пробуем любую submit кнопку
            try:
                await self.page.locator("button[type='submit'], input[type='submit']").first.click()
                await asyncio.sleep(2)
                if self.page.url != original_url:
                    return RecoveryResult(
                        success=True,
                        action_taken="Submit button",
                        result_data={"new_url": self.page.url},
                        next_suggestions=[]
                    )
            except:
                pass
            
            return RecoveryResult(
                success=False,
                action_taken="Базовое восстановление неудачно",
                result_data={},
                next_suggestions=[]
            )
            
        except Exception as e:
            return RecoveryResult(
                success=False,
                action_taken=f"Ошибка базового восстановления: {e}",
                result_data={},
                next_suggestions=[]
            )
