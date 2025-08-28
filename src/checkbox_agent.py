"""
Checkbox Agent с ReAct парадигмой
Интеллектуальная работа с чекбоксами, радиокнопками и переключателями
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit
from agentscope.message import Msg
from pydantic import BaseModel

class CheckboxInfo(BaseModel):
    """Информация о чекбоксе"""
    selector: str
    checkbox_type: str  # checkbox, radio, toggle, switch
    label: str
    checked: bool
    required: bool
    group_name: Optional[str]  # для радиокнопок
    semantic_meaning: str  # terms, privacy, marketing, newsletter, etc.
    confidence: float

class CheckboxActionResult(BaseModel):
    """Результат действия с чекбоксом"""
    success: bool
    action_taken: str  # checked, unchecked, skipped
    checkbox_selector: str
    reasoning: str
    group_state: Optional[Dict[str, bool]]  # для радиогрупп

class CheckboxToolkit(Toolkit):
    """Инструменты для работы с чекбоксами"""
    
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.register_tool_function(self.find_all_checkboxes)
        self.register_tool_function(self.analyze_checkbox_semantics)
        self.register_tool_function(self.get_checkbox_state)
        self.register_tool_function(self.toggle_checkbox_safely)
        self.register_tool_function(self.find_radio_groups)
        self.register_tool_function(self.analyze_checkbox_labels)
    
    async def find_all_checkboxes(self) -> str:
        """Находит все чекбоксы и переключатели на странице"""
        try:
            # Поиск различных типов переключателей
            selectors = [
                'input[type="checkbox"]',
                'input[type="radio"]',
                '[role="checkbox"]',
                '[role="radio"]',
                '[role="switch"]',
                '.checkbox',
                '.radio',
                '.switch',
                '.toggle'
            ]
            
            all_checkboxes = []
            
            for selector in selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    
                    for i, element in enumerate(elements):
                        try:
                            checkbox_info = {
                                "index": len(all_checkboxes),
                                "selector": f"{selector}:nth-child({i+1})",
                                "type": await element.get_attribute("type") or "checkbox",
                                "name": await element.get_attribute("name") or "",
                                "id": await element.get_attribute("id") or "",
                                "value": await element.get_attribute("value") or "",
                                "checked": await element.is_checked(),
                                "visible": await element.is_visible(),
                                "enabled": await element.is_enabled(),
                                "required": await element.get_attribute("required") is not None,
                                "class": await element.get_attribute("class") or "",
                                "aria_label": await element.get_attribute("aria-label") or "",
                                "data_attributes": {}
                            }
                            
                            # Получаем data-* атрибуты
                            try:
                                data_attrs = await element.evaluate("""
                                    el => {
                                        const attrs = {};
                                        for (let attr of el.attributes) {
                                            if (attr.name.startsWith('data-')) {
                                                attrs[attr.name] = attr.value;
                                            }
                                        }
                                        return attrs;
                                    }
                                """)
                                checkbox_info["data_attributes"] = data_attrs
                            except:
                                pass
                            
                            # Поиск связанного label
                            label_text = ""
                            if checkbox_info["id"]:
                                try:
                                    label = await self.page.locator(f'label[for="{checkbox_info["id"]}"]').first
                                    if label:
                                        label_text = await label.text_content() or ""
                                except:
                                    pass
                            
                            if not label_text:
                                try:
                                    # Поиск label-родителя
                                    parent_label = await element.locator('xpath=./ancestor::label[1]').first
                                    if parent_label:
                                        label_text = await parent_label.text_content() or ""
                                except:
                                    pass
                            
                            if not label_text:
                                try:
                                    # Поиск текста рядом с чекбоксом
                                    next_text = await element.locator('xpath=./following-sibling::text()[1]').first
                                    if next_text:
                                        label_text = await next_text.text_content() or ""
                                except:
                                    pass
                            
                            checkbox_info["label"] = label_text.strip()
                            
                            if checkbox_info["visible"] and checkbox_info["enabled"]:
                                all_checkboxes.append(checkbox_info)
                                
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    continue
            
            return json.dumps(all_checkboxes, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка поиска чекбоксов: {str(e)}"
    
    async def analyze_checkbox_semantics(self) -> str:
        """Анализирует семантическое значение чекбоксов"""
        try:
            checkboxes_data = await self.find_all_checkboxes()
            checkboxes = json.loads(checkboxes_data)
            
            semantic_analysis = []
            
            for checkbox in checkboxes:
                combined_text = f"{checkbox['label']} {checkbox['name']} {checkbox['aria_label']} {checkbox['class']}".lower()
                
                # Определяем семантику
                semantic_type = "unknown"
                confidence = 0.5
                action_recommendation = "skip"
                
                # Terms of Service / Privacy Policy - соглашаемся
                if any(keyword in combined_text for keyword in ['term', 'service', 'privacy', 'policy', 'agreement', 'consent', 'accept']):
                    semantic_type = "terms_privacy"
                    confidence = 0.9
                    action_recommendation = "check"
                
                # Marketing / Newsletter - отказываемся
                elif any(keyword in combined_text for keyword in ['marketing', 'newsletter', 'promo', 'offer', 'advertisement', 'spam', 'email']):
                    semantic_type = "marketing"
                    confidence = 0.8
                    action_recommendation = "uncheck"
                
                # Remember me / Keep logged in - соглашаемся
                elif any(keyword in combined_text for keyword in ['remember', 'keep', 'stay', 'logged', 'sign']):
                    semantic_type = "remember_me"
                    confidence = 0.8
                    action_recommendation = "check"
                
                # Age verification - соглашаемся
                elif any(keyword in combined_text for keyword in ['age', 'over', 'adult', '18', '21', 'old']):
                    semantic_type = "age_verification"
                    confidence = 0.9
                    action_recommendation = "check"
                
                # Required checkboxes - соглашаемся
                elif checkbox['required']:
                    semantic_type = "required"
                    confidence = 1.0
                    action_recommendation = "check"
                
                # Optional features - пропускаем
                elif any(keyword in combined_text for keyword in ['optional', 'feature', 'beta', 'trial']):
                    semantic_type = "optional_feature"
                    confidence = 0.7
                    action_recommendation = "skip"
                
                semantic_analysis.append({
                    "checkbox": checkbox,
                    "semantic_type": semantic_type,
                    "confidence": confidence,
                    "action_recommendation": action_recommendation,
                    "analysis_text": combined_text[:100]
                })
            
            return json.dumps(semantic_analysis, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка семантического анализа: {str(e)}"
    
    async def get_checkbox_state(self, selector: str) -> str:
        """Получает текущее состояние чекбокса"""
        try:
            element = await self.page.locator(selector).first
            if not element:
                return json.dumps({"error": "Элемент не найден"})
            
            state = {
                "exists": True,
                "visible": await element.is_visible(),
                "enabled": await element.is_enabled(),
                "checked": await element.is_checked(),
                "required": await element.get_attribute("required") is not None,
                "type": await element.get_attribute("type") or "checkbox"
            }
            
            return json.dumps(state, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({"error": f"Ошибка получения состояния: {str(e)}"})
    
    async def toggle_checkbox_safely(self, selector: str, target_state: bool) -> str:
        """Безопасно переключает чекбокс в нужное состояние"""
        try:
            element = await self.page.locator(selector).first
            if not element:
                return json.dumps({"success": False, "error": "Элемент не найден"})
            
            # Проверяем доступность
            if not await element.is_visible():
                return json.dumps({"success": False, "error": "Элемент не видим"})
            
            if not await element.is_enabled():
                return json.dumps({"success": False, "error": "Элемент недоступен"})
            
            # Получаем текущее состояние
            current_state = await element.is_checked()
            
            # Если уже в нужном состоянии
            if current_state == target_state:
                return json.dumps({
                    "success": True,
                    "action": "no_action_needed",
                    "current_state": current_state,
                    "target_state": target_state
                })
            
            # Прокручиваем к элементу
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(0.2)
            
            # Имитируем человеческое поведение
            box = await element.bounding_box()
            if box:
                # Движение мыши к чекбоксу
                import random
                x = box['x'] + box['width'] / 2 + random.uniform(-2, 2)
                y = box['y'] + box['height'] / 2 + random.uniform(-2, 2)
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.2))
            
            # Кликаем
            await element.click()
            await asyncio.sleep(0.1)
            
            # Проверяем результат
            new_state = await element.is_checked()
            success = new_state == target_state
            
            return json.dumps({
                "success": success,
                "action": "clicked",
                "previous_state": current_state,
                "current_state": new_state,
                "target_state": target_state
            })
            
        except Exception as e:
            return json.dumps({"success": False, "error": f"Ошибка переключения: {str(e)}"})
    
    async def find_radio_groups(self) -> str:
        """Находит и группирует радиокнопки"""
        try:
            radio_buttons = await self.page.locator('input[type="radio"]').all()
            groups = {}
            
            for radio in radio_buttons:
                try:
                    name = await radio.get_attribute("name")
                    if not name:
                        continue
                    
                    if name not in groups:
                        groups[name] = []
                    
                    radio_info = {
                        "value": await radio.get_attribute("value") or "",
                        "id": await radio.get_attribute("id") or "",
                        "checked": await radio.is_checked(),
                        "visible": await radio.is_visible(),
                        "enabled": await radio.is_enabled()
                    }
                    
                    # Поиск label
                    label_text = ""
                    radio_id = radio_info["id"]
                    if radio_id:
                        try:
                            label = await self.page.locator(f'label[for="{radio_id}"]').first
                            if label:
                                label_text = await label.text_content() or ""
                        except:
                            pass
                    
                    radio_info["label"] = label_text.strip()
                    
                    if radio_info["visible"] and radio_info["enabled"]:
                        groups[name].append(radio_info)
                        
                except Exception as e:
                    continue
            
            return json.dumps(groups, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка поиска радиогрупп: {str(e)}"
    
    async def analyze_checkbox_labels(self) -> str:
        """Анализирует тексты label для лучшего понимания"""
        try:
            checkboxes_data = await self.find_all_checkboxes()
            checkboxes = json.loads(checkboxes_data)
            
            label_analysis = []
            
            for checkbox in checkboxes:
                label = checkbox.get("label", "")
                if not label:
                    continue
                
                # Анализ тональности и намерения
                label_lower = label.lower()
                
                analysis = {
                    "original_label": label,
                    "length": len(label),
                    "word_count": len(label.split()),
                    "contains_url": "http" in label_lower or "www." in label_lower,
                    "contains_legal": any(word in label_lower for word in ['term', 'condition', 'privacy', 'policy', 'legal']),
                    "contains_marketing": any(word in label_lower for word in ['newsletter', 'email', 'promo', 'offer', 'marketing']),
                    "contains_agreement": any(word in label_lower for word in ['agree', 'accept', 'consent', 'acknowledge']),
                    "urgency_words": any(word in label_lower for word in ['must', 'required', 'mandatory', 'necessary']),
                    "positive_words": any(word in label_lower for word in ['benefit', 'free', 'bonus', 'special', 'exclusive']),
                    "negative_words": any(word in label_lower for word in ['spam', 'unwanted', 'third-party', 'share']),
                    "checkbox_index": checkbox["index"]
                }
                
                label_analysis.append(analysis)
            
            return json.dumps(label_analysis, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка анализа labels: {str(e)}"

class CheckboxAgent(ReActAgent):
    """Интеллектуальный агент для работы с чекбоксами"""
    
    def __init__(self, page, model):
        super().__init__(
            name="CheckboxAgent",
            memory=InMemoryMemory(),
            model=model,
            tools=CheckboxToolkit(page)
        )
        self.page = page
    
    async def process_all_checkboxes(self, user_preferences: Dict[str, bool] = None) -> List[CheckboxActionResult]:
        """Обрабатывает все чекбоксы на странице согласно правилам"""
        
        default_preferences = {
            "accept_terms": True,      # Соглашаемся с условиями
            "accept_privacy": True,    # Соглашаемся с приватностью
            "marketing_emails": False, # Отказываемся от маркетинга
            "newsletters": False,      # Отказываемся от рассылок
            "remember_me": True,       # Запоминать вход
            "age_verification": True,  # Подтверждаем возраст
            "optional_features": False # Отказываемся от опций
        }
        
        preferences = {**default_preferences, **(user_preferences or {})}
        
        # Системное сообщение для ReAct агента
        system_msg = Msg(
            role="system",
            content=f"""Ты - эксперт по работе с чекбоксами и формами регистрации.
            
            Твоя задача:
            1. Найти все чекбоксы на странице
            2. Проанализировать их семантическое значение
            3. Принять решение о том, какие отмечать/снимать
            4. Выполнить действия согласно предпочтениям пользователя
            
            Предпочтения пользователя:
            {json.dumps(preferences, indent=2, ensure_ascii=False)}
            
            Правила принятия решений:
            - ОБЯЗАТЕЛЬНЫЕ чекбоксы (required) - ВСЕГДА отмечать
            - Terms of Service, Privacy Policy - отмечать если accept_terms=True
            - Marketing, Newsletter - отмечать только если соответствующее предпочтение=True
            - Remember me - отмечать если remember_me=True
            - Age verification - отмечать если age_verification=True
            - Непонятные чекбоксы - НЕ отмечать (безопасность)
            
            Действуй аккуратно и объясняй каждое решение."""
        )
        
        task_msg = Msg(
            role="user",
            content="Проанализируй все чекбоксы на странице и обработай их согласно правилам и предпочтениям пользователя."
        )
        
        # Запускаем ReAct процесс
        response = await self.call([system_msg, task_msg])
        
        # Получаем финальное состояние всех чекбоксов
        try:
            checkboxes_data = await self.tools.find_all_checkboxes()
            checkboxes = json.loads(checkboxes_data)
            
            results = []
            for checkbox in checkboxes:
                result = CheckboxActionResult(
                    success=True,
                    action_taken="processed",
                    checkbox_selector=checkbox["selector"],
                    reasoning=f"Обработан в рамках общего анализа: {checkbox['label'][:50]}",
                    group_state=None
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            return [CheckboxActionResult(
                success=False,
                action_taken="error",
                checkbox_selector="unknown",
                reasoning=f"Ошибка обработки чекбоксов: {str(e)}",
                group_state=None
            )]
    
    async def handle_specific_checkbox(self, selector: str, action: str, reasoning: str = "") -> CheckboxActionResult:
        """Обрабатывает конкретный чекбокс"""
        try:
            target_state = action.lower() in ["check", "true", "on", "yes"]
            
            result_data = await self.tools.toggle_checkbox_safely(selector, target_state)
            result = json.loads(result_data)
            
            return CheckboxActionResult(
                success=result.get("success", False),
                action_taken=result.get("action", "unknown"),
                checkbox_selector=selector,
                reasoning=reasoning or f"Выполнено действие: {action}",
                group_state=None
            )
            
        except Exception as e:
            return CheckboxActionResult(
                success=False,
                action_taken="error",
                checkbox_selector=selector,
                reasoning=f"Ошибка: {str(e)}",
                group_state=None
            )
