"""
Form Filler Agent с ReAct парадигмой
Интеллектуальное заполнение форм с автоопределением типов полей
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit
from agentscope.message import Msg
from pydantic import BaseModel

class FormFieldInfo(BaseModel):
    """Информация о поле формы"""
    selector: str
    field_type: str  # email, password, text, number, tel, etc.
    label: str
    placeholder: str
    required: bool
    validation_pattern: Optional[str]
    confidence: float

class FormFillResult(BaseModel):
    """Результат заполнения формы"""
    success: bool
    filled_fields: List[str]
    skipped_fields: List[str]
    validation_errors: List[str]
    reasoning: str
    next_action: Optional[str]

class FormAnalysisToolkit(Toolkit):
    """Инструменты для анализа и заполнения форм"""
    
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.register_tool_function(self.analyze_form_structure)
        self.register_tool_function(self.identify_field_types)
        self.register_tool_function(self.validate_field_data)
        self.register_tool_function(self.fill_field_smartly)
        self.register_tool_function(self.check_form_submission)
        self.register_tool_function(self.get_form_validation_state)
    
    async def analyze_form_structure(self) -> str:
        """Анализирует структуру всех форм на странице"""
        try:
            # Найти все формы
            forms = await self.page.locator('form').count()
            
            # Найти все поля ввода
            inputs = await self.page.locator('input, textarea, select').all()
            
            form_analysis = {
                "forms_count": forms,
                "total_fields": len(inputs),
                "fields": []
            }
            
            for input_elem in inputs:
                try:
                    field_info = {
                        "tag": await input_elem.evaluate("el => el.tagName.toLowerCase()"),
                        "type": await input_elem.get_attribute("type") or "text",
                        "name": await input_elem.get_attribute("name") or "",
                        "id": await input_elem.get_attribute("id") or "",
                        "placeholder": await input_elem.get_attribute("placeholder") or "",
                        "required": await input_elem.get_attribute("required") is not None,
                        "class": await input_elem.get_attribute("class") or "",
                        "aria_label": await input_elem.get_attribute("aria-label") or "",
                        "visible": await input_elem.is_visible(),
                        "enabled": await input_elem.is_enabled()
                    }
                    
                    # Поиск связанного label
                    label_text = ""
                    if field_info["id"]:
                        try:
                            label = await self.page.locator(f'label[for="{field_info["id"]}"]').first
                            if label:
                                label_text = await label.text_content() or ""
                        except:
                            pass
                    
                    if not label_text:
                        try:
                            # Поиск label-родителя или соседа
                            parent_label = await input_elem.locator('xpath=./ancestor::label[1]').first
                            if parent_label:
                                label_text = await parent_label.text_content() or ""
                        except:
                            pass
                    
                    field_info["label"] = label_text.strip()
                    form_analysis["fields"].append(field_info)
                    
                except Exception as e:
                    continue
            
            return json.dumps(form_analysis, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка анализа формы: {str(e)}"
    
    async def identify_field_types(self) -> str:
        """Определяет типы полей на основе семантики"""
        try:
            inputs = await self.page.locator('input, textarea, select').all()
            field_types = []
            
            for i, input_elem in enumerate(inputs):
                try:
                    field_type = await input_elem.get_attribute("type") or "text"
                    name = await input_elem.get_attribute("name") or ""
                    placeholder = await input_elem.get_attribute("placeholder") or ""
                    aria_label = await input_elem.get_attribute("aria-label") or ""
                    class_name = await input_elem.get_attribute("class") or ""
                    
                    # Семантический анализ
                    combined_text = f"{name} {placeholder} {aria_label} {class_name}".lower()
                    
                    semantic_type = "unknown"
                    confidence = 0.5
                    
                    # Email поля
                    if any(keyword in combined_text for keyword in ['email', 'mail', 'e-mail']):
                        semantic_type = "email"
                        confidence = 0.9
                    # Пароль
                    elif any(keyword in combined_text for keyword in ['password', 'pass', 'pwd']):
                        semantic_type = "password"
                        confidence = 0.9
                    # Имя
                    elif any(keyword in combined_text for keyword in ['name', 'first', 'last', 'full']):
                        semantic_type = "name"
                        confidence = 0.8
                    # Телефон
                    elif any(keyword in combined_text for keyword in ['phone', 'tel', 'mobile', 'number']):
                        semantic_type = "phone"
                        confidence = 0.8
                    # Компания
                    elif any(keyword in combined_text for keyword in ['company', 'organization', 'business']):
                        semantic_type = "company"
                        confidence = 0.8
                    # Сайт
                    elif any(keyword in combined_text for keyword in ['website', 'url', 'site', 'domain']):
                        semantic_type = "website"
                        confidence = 0.8
                    # Дата рождения
                    elif any(keyword in combined_text for keyword in ['birth', 'born', 'date', 'birthday']):
                        semantic_type = "birth_date"
                        confidence = 0.8
                    # Username
                    elif any(keyword in combined_text for keyword in ['username', 'user', 'login']):
                        semantic_type = "username"
                        confidence = 0.8
                    
                    field_types.append({
                        "index": i,
                        "html_type": field_type,
                        "semantic_type": semantic_type,
                        "confidence": confidence,
                        "analysis": combined_text[:50]
                    })
                    
                except Exception as e:
                    continue
            
            return json.dumps(field_types, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка определения типов: {str(e)}"
    
    async def validate_field_data(self, field_selector: str, data_value: str) -> str:
        """Валидирует данные для конкретного поля"""
        try:
            element = await self.page.locator(field_selector).first
            if not element:
                return "Поле не найдено"
            
            field_type = await element.get_attribute("type") or "text"
            pattern = await element.get_attribute("pattern")
            required = await element.get_attribute("required") is not None
            maxlength = await element.get_attribute("maxlength")
            minlength = await element.get_attribute("minlength")
            
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            # Проверка обязательности
            if required and not data_value:
                validation_result["valid"] = False
                validation_result["errors"].append("Поле обязательно для заполнения")
            
            # Проверка длины
            if maxlength and len(data_value) > int(maxlength):
                validation_result["valid"] = False
                validation_result["errors"].append(f"Превышена максимальная длина {maxlength}")
            
            if minlength and len(data_value) < int(minlength):
                validation_result["valid"] = False
                validation_result["errors"].append(f"Минимальная длина {minlength}")
            
            # Проверка типа
            if field_type == "email" and "@" not in data_value:
                validation_result["valid"] = False
                validation_result["errors"].append("Неверный формат email")
            
            # Проверка паттерна
            if pattern:
                import re
                if not re.match(pattern, data_value):
                    validation_result["valid"] = False
                    validation_result["errors"].append("Не соответствует требуемому формату")
            
            return json.dumps(validation_result, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка валидации: {str(e)}"
    
    async def fill_field_smartly(self, field_selector: str, value: str, typing_speed: str = "normal") -> str:
        """Умно заполняет поле с человекоподобным поведением"""
        try:
            element = await self.page.locator(field_selector).first
            if not element:
                return "Поле не найдено"
            
            # Проверяем видимость и доступность
            if not await element.is_visible():
                return "Поле не видимо"
            
            if not await element.is_enabled():
                return "Поле недоступно"
            
            # Прокручиваем к элементу
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(0.2)
            
            # Кликаем на поле
            await element.click()
            await asyncio.sleep(0.1)
            
            # Очищаем поле
            await element.fill("")
            await asyncio.sleep(0.1)
            
            # Определяем скорость набора
            if typing_speed == "fast":
                delay_range = (30, 80)
            elif typing_speed == "slow":
                delay_range = (100, 200)
            else:  # normal
                delay_range = (50, 120)
            
            # Печатаем символ за символом
            import random
            for char in value:
                await element.type(char, delay=random.randint(*delay_range))
                # Случайные паузы
                if random.random() < 0.1:
                    await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Проверяем результат
            current_value = await element.input_value()
            success = current_value == value
            
            return json.dumps({
                "success": success,
                "expected": value,
                "actual": current_value,
                "message": "Поле заполнено успешно" if success else "Значение не совпадает"
            }, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка заполнения: {str(e)}"
    
    async def check_form_submission(self) -> str:
        """Проверяет готовность формы к отправке"""
        try:
            # Найти кнопки отправки
            submit_buttons = await self.page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Continue"), button:has-text("Next")').all()
            
            # Проверить валидность формы
            form_validity = await self.page.evaluate("""
                () => {
                    const forms = document.querySelectorAll('form');
                    let validity = [];
                    
                    forms.forEach((form, index) => {
                        const inputs = form.querySelectorAll('input, textarea, select');
                        let invalid_fields = [];
                        
                        inputs.forEach(input => {
                            if (!input.checkValidity()) {
                                invalid_fields.push({
                                    name: input.name || input.id || input.type,
                                    error: input.validationMessage
                                });
                            }
                        });
                        
                        validity.push({
                            form_index: index,
                            valid: invalid_fields.length === 0,
                            invalid_fields: invalid_fields
                        });
                    });
                    
                    return validity;
                }
            """)
            
            result = {
                "submit_buttons_count": len(submit_buttons),
                "forms_validity": form_validity,
                "ready_to_submit": all(f["valid"] for f in form_validity) and len(submit_buttons) > 0
            }
            
            return json.dumps(result, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка проверки формы: {str(e)}"
    
    async def get_form_validation_state(self) -> str:
        """Получает состояние валидации всех полей"""
        try:
            validation_state = await self.page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input, textarea, select');
                    let states = [];
                    
                    inputs.forEach((input, index) => {
                        states.push({
                            index: index,
                            name: input.name || input.id || `field_${index}`,
                            type: input.type,
                            valid: input.checkValidity(),
                            value_length: (input.value || '').length,
                            required: input.required,
                            validation_message: input.validationMessage || '',
                            custom_validity: input.dataset.customValidity || ''
                        });
                    });
                    
                    return states;
                }
            """)
            
            return json.dumps(validation_state, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Ошибка получения состояния: {str(e)}"

class FormFillerAgent(ReActAgent):
    """Интеллектуальный агент для заполнения форм"""
    
    def __init__(self, page, model):
        super().__init__(
            name="FormFillerAgent",
            memory=InMemoryMemory(),
            model=model,
            tools=FormAnalysisToolkit(page)
        )
        self.page = page
    
    async def analyze_and_fill_form(self, user_data: Dict[str, str]) -> FormFillResult:
        """Анализирует форму и заполняет её умно"""
        
        # Системное сообщение для ReAct агента
        system_msg = Msg(
            role="system",
            content=f"""Ты - эксперт по заполнению веб-форм. 
            
            Твоя задача:
            1. Проанализировать структуру формы на странице
            2. Определить типы полей семантически  
            3. Сопоставить поля с доступными данными пользователя
            4. Заполнить поля в правильном порядке
            5. Проверить валидность заполнения
            
            Доступные данные пользователя:
            {json.dumps(user_data, indent=2, ensure_ascii=False)}
            
            Правила заполнения:
            - Заполняй только ВИДИМЫЕ и ДОСТУПНЫЕ поля
            - Используй ТОЧНОЕ соответствие типов полей и данных
            - НЕ заполняй поля, для которых нет подходящих данных
            - ОБЯЗАТЕЛЬНЫЕ поля имеют приоритет
            - Проверяй валидацию после каждого поля
            
            Сначала проанализируй форму, затем действуй пошагово."""
        )
        
        # Задача для агента
        task_msg = Msg(
            role="user", 
            content="Проанализируй форму на странице и заполни её доступными данными пользователя. Действуй пошагово и объясняй свои решения."
        )
        
        # Запускаем ReAct процесс
        response = await self.call([system_msg, task_msg])
        
        # Парсим результат
        try:
            # Получаем финальное состояние формы
            validation_state = await self.tools.get_form_validation_state()
            form_state = json.loads(validation_state)
            
            filled_fields = [f["name"] for f in form_state if f["value_length"] > 0]
            invalid_fields = [f["name"] for f in form_state if not f["valid"] and f["required"]]
            
            return FormFillResult(
                success=len(invalid_fields) == 0,
                filled_fields=filled_fields,
                skipped_fields=[],
                validation_errors=invalid_fields,
                reasoning=response.content if response else "Нет ответа от агента",
                next_action="form_ready" if len(invalid_fields) == 0 else "validation_errors"
            )
            
        except Exception as e:
            return FormFillResult(
                success=False,
                filled_fields=[],
                skipped_fields=[],
                validation_errors=[str(e)],
                reasoning=f"Ошибка обработки результата: {e}",
                next_action="error"
            )
    
    async def fill_specific_field(self, field_info: FormFieldInfo, value: str) -> bool:
        """Заполняет конкретное поле"""
        try:
            # Валидируем данные
            validation_result = await self.tools.validate_field_data(field_info.selector, value)
            validation = json.loads(validation_result)
            
            if not validation["valid"]:
                print(f"Валидация не прошла: {validation['errors']}")
                return False
            
            # Заполняем поле
            fill_result = await self.tools.fill_field_smartly(field_info.selector, value)
            fill_data = json.loads(fill_result)
            
            return fill_data["success"]
            
        except Exception as e:
            print(f"Ошибка заполнения поля {field_info.selector}: {e}")
            return False
