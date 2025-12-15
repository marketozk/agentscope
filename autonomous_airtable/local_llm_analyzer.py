"""
🤖 LocalLLMAnalyzer - анализ страниц через локальную LLM (LM Studio)

Использует OpenAI-совместимый API LM Studio для анализа:
- Скриншотов страниц (vision)
- Текста страницы
- HTML элементов
- Сообщений об ошибках

Модель: Qwen2-VL-7B-Instruct (vision-модель)
Endpoint: http://127.0.0.1:1234/v1
"""

import asyncio
import base64
import json
import re
import requests
from typing import Optional, Dict, List, Tuple
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

try:
    from playwright.async_api import Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    Page = None


class PageState(Enum):
    """Состояния страницы, определяемые LLM"""
    SUCCESS = "success"           # Регистрация успешна
    ERROR_EMAIL = "error_email"   # Ошибка email (невалидный/занят)
    ERROR_OTHER = "error_other"   # Другая ошибка
    CAPTCHA = "captcha"           # Требуется капча
    LOADING = "loading"           # Страница загружается
    FORM_READY = "form_ready"     # Форма готова к заполнению
    ONBOARDING = "onboarding"     # Шаг онбординга
    EMAIL_CONFIRM = "email_confirm"  # Страница подтверждения email
    UNKNOWN = "unknown"           # Неизвестное состояние


@dataclass
class LLMAnalysisResult:
    """Результат анализа страницы через LLM"""
    state: PageState
    confidence: float  # 0.0 - 1.0
    message: str
    raw_response: str
    suggested_action: Optional[str] = None
    next_element: Optional[str] = None  # Элемент для клика/заполнения


@dataclass
class OnboardingAction:
    """Действие для онбординга"""
    action_type: str  # "click", "fill", "scroll", "done", "wait"
    element: Optional[str] = None  # Описание элемента
    value: Optional[str] = None  # Значение для заполнения
    confidence: float = 0.5


class LocalLLMAnalyzer:
    """
    Анализатор страниц через локальную LLM (LM Studio) с поддержкой Vision.
    
    Использование:
        analyzer = LocalLLMAnalyzer()
        if analyzer.is_available():
            result = await analyzer.analyze_page_vision(page)
            if result.state == PageState.ONBOARDING:
                action = await analyzer.get_onboarding_action(page)
    """
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:1234/v1",
        model: str = "qwen2-vl-7b-instruct",
        timeout: float = 180.0,  # Vision требует больше времени
    ):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.chat_url = f"{base_url}/chat/completions"
        self._available: Optional[bool] = None
    
    def _send_request(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        timeout: Optional[float] = None,
    ) -> str:
        """Отправка запроса к LM Studio через requests"""
        response = requests.post(
            self.chat_url,
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            },
            timeout=timeout or self.timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    def is_available(self) -> bool:
        """Проверить доступность LM Studio"""
        if self._available is not None:
            return self._available
        
        try:
            result = self._send_request(
                [{"role": "user", "content": "ping"}],
                timeout=10.0,
            )
            self._available = True
            print(f"✅ LM Studio доступен: {self.base_url}")
            print(f"   Модель: {self.model}")
            return True
        except Exception as e:
            print(f"⚠️ LM Studio недоступен: {e}")
            self._available = False
            return False
    
    async def take_screenshot_base64(self, page: Page) -> str:
        """Сделать скриншот и вернуть в base64"""
        screenshot_bytes = await page.screenshot(type="png")
        return base64.b64encode(screenshot_bytes).decode()
    
    async def analyze_page_vision(
        self,
        page: Page,
        custom_prompt: Optional[str] = None,
    ) -> LLMAnalysisResult:
        """
        Анализировать страницу через Vision LLM.
        
        Делает скриншот и отправляет в LLM для классификации.
        """
        # Получаем скриншот
        try:
            image_base64 = await self.take_screenshot_base64(page)
        except Exception as e:
            return LLMAnalysisResult(
                state=PageState.UNKNOWN,
                confidence=0.0,
                message=f"Ошибка скриншота: {e}",
                raw_response="",
            )
        
        # Получаем URL для контекста
        url = page.url
        
        # Формируем промпт
        if custom_prompt:
            prompt_text = custom_prompt
        else:
            prompt_text = f"""Analyze this webpage screenshot.

Current URL: {url}

Classify the page state as ONE of:
- SUCCESS: Registration completed successfully, welcome message shown
- ERROR_EMAIL: Email validation error (invalid email, already exists, domain rejected)
- ERROR_OTHER: Other error message is displayed
- CAPTCHA: Captcha or robot verification is shown
- LOADING: Page is still loading (spinner, skeleton)
- FORM_READY: Registration/signup form is ready to fill
- ONBOARDING: Post-registration onboarding step (asking for name, workspace, etc.)
- EMAIL_CONFIRM: Email confirmation page or "check your email" message
- UNKNOWN: Cannot determine state

Look for:
- Error messages (red text, alerts)
- Success indicators (green checkmarks, welcome messages)
- Form fields and buttons
- Loading spinners
- Captcha challenges

Respond with JSON only:
{{"state": "STATE_NAME", "confidence": 0.9, "message": "what you see", "action": "suggested action or null", "element": "element to interact with or null"}}"""
        
        # Отправляем в LLM
        try:
            raw = await asyncio.to_thread(
                self._send_request,
                [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,  # Низкая температура для стабильности
            )
            
            return self._parse_llm_response(raw)
            
        except Exception as e:
            return LLMAnalysisResult(
                state=PageState.UNKNOWN,
                confidence=0.0,
                message=f"Ошибка LLM: {e}",
                raw_response="",
            )
    
    async def get_onboarding_action(
        self,
        page: Page,
        context: str = "",
    ) -> OnboardingAction:
        """
        Определить следующее действие для онбординга через Vision.
        
        Args:
            page: Страница Playwright
            context: Дополнительный контекст (например, имя workspace)
        
        Returns:
            OnboardingAction с типом действия и параметрами
        """
        try:
            image_base64 = await self.take_screenshot_base64(page)
        except Exception as e:
            return OnboardingAction(
                action_type="wait",
                confidence=0.0,
            )
        
        prompt = f"""You are a browser automation assistant completing Airtable onboarding.

{f"Context: {context}" if context else ""}

Look at this screenshot and decide the next action to complete onboarding.

Available actions:
- click: Click on a button or link
- fill: Fill a text field with a value
- scroll: Scroll the page (up/down)
- done: Onboarding is complete
- wait: Wait for page to load

Rules:
1. If you see a "Continue", "Next", "Get Started", "Skip" button - click it
2. If you see a text field asking for workspace name - fill it with "My Workspace"
3. If you see a text field asking for name - fill it with "John Doe"
4. If you see "Welcome" or dashboard - onboarding is done
5. If page is loading - wait

Respond with JSON only:
{{"action": "click|fill|scroll|done|wait", "element": "element description or null", "value": "value for fill or null", "confidence": 0.9}}"""
        
        try:
            raw = await asyncio.to_thread(
                self._send_request,
                [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
            )
            
            return self._parse_onboarding_action(raw)
            
        except Exception as e:
            print(f"⚠️ Ошибка get_onboarding_action: {e}")
            return OnboardingAction(action_type="wait", confidence=0.0)
    
    async def analyze_page_text(self, page: Page) -> LLMAnalysisResult:
        """
        Анализировать страницу через текст (без vision).
        Более быстрый вариант для простых случаев.
        """
        # Извлекаем контекст страницы
        context = await self._extract_page_context(page)
        
        # Формируем промпт
        prompt = self._build_text_analysis_prompt(context)
        
        try:
            raw = await asyncio.to_thread(
                self._send_request,
                [
                    {
                        "role": "system",
                        "content": "You are a web page state analyzer. Respond ONLY with JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
            )
            
            return self._parse_llm_response(raw)
            
        except Exception as e:
            return LLMAnalysisResult(
                state=PageState.UNKNOWN,
                confidence=0.0,
                message=f"Ошибка LLM: {e}",
                raw_response="",
            )
    
    async def _extract_page_context(self, page: Page) -> Dict:
        """Извлечь контекст страницы для анализа"""
        context = {
            "url": page.url,
            "title": "",
            "visible_text": "",
            "error_messages": [],
            "success_messages": [],
            "buttons": [],
            "inputs": [],
        }
        
        try:
            context["title"] = await page.title()
        except:
            pass
        
        try:
            data = await page.evaluate("""
                () => {
                    const result = {
                        visible_text: '',
                        error_messages: [],
                        success_messages: [],
                        buttons: [],
                        inputs: [],
                    };
                    
                    result.visible_text = document.body.innerText.substring(0, 2000);
                    
                    const errorSelectors = [
                        '[role="alert"]',
                        '.error', '.errors', '.alert-error', '.alert-danger',
                        '[class*="error" i]', '[class*="invalid" i]',
                    ];
                    for (const sel of errorSelectors) {
                        document.querySelectorAll(sel).forEach(el => {
                            const text = el.innerText.trim();
                            if (text && text.length > 3 && text.length < 200) {
                                result.error_messages.push(text);
                            }
                        });
                    }
                    
                    const successSelectors = [
                        '.success', '.alert-success', '[class*="success" i]',
                    ];
                    for (const sel of successSelectors) {
                        document.querySelectorAll(sel).forEach(el => {
                            const text = el.innerText.trim();
                            if (text && text.length > 3 && text.length < 200) {
                                result.success_messages.push(text);
                            }
                        });
                    }
                    
                    document.querySelectorAll('button:not([hidden])').forEach(btn => {
                        const text = btn.innerText.trim();
                        if (text) result.buttons.push(text.substring(0, 50));
                    });
                    
                    document.querySelectorAll('input:not([type="hidden"])').forEach(inp => {
                        result.inputs.push({
                            type: inp.type,
                            name: inp.name,
                            placeholder: inp.placeholder,
                        });
                    });
                    
                    result.error_messages = [...new Set(result.error_messages)].slice(0, 5);
                    result.success_messages = [...new Set(result.success_messages)].slice(0, 5);
                    result.buttons = [...new Set(result.buttons)].slice(0, 10);
                    
                    return result;
                }
            """)
            
            context.update(data)
        except Exception as e:
            print(f"⚠️ Ошибка извлечения контекста: {e}")
        
        return context
    
    def _build_text_analysis_prompt(self, context: Dict) -> str:
        """Построить промпт для текстового анализа"""
        return f"""Analyze this web page state and classify it.

URL: {context.get('url', 'unknown')}
Title: {context.get('title', 'unknown')}

Error messages found: {context.get('error_messages', [])}
Success messages found: {context.get('success_messages', [])}
Buttons visible: {context.get('buttons', [])}
Input fields: {len(context.get('inputs', []))} fields

Page text (excerpt):
{context.get('visible_text', '')[:1000]}

---

Classify as ONE of: SUCCESS, ERROR_EMAIL, ERROR_OTHER, CAPTCHA, LOADING, FORM_READY, ONBOARDING, EMAIL_CONFIRM, UNKNOWN

Respond with JSON only:
{{"state": "STATE_NAME", "confidence": 0.9, "message": "explanation", "action": "suggested action or null"}}"""
    
    def _parse_llm_response(self, raw: str) -> LLMAnalysisResult:
        """Парсинг ответа LLM в LLMAnalysisResult"""
        try:
            # Ищем JSON в ответе
            json_match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                state_str = data.get("state", "UNKNOWN").upper().replace(" ", "_")
                try:
                    state = PageState[state_str]
                except KeyError:
                    state = PageState.UNKNOWN
                
                return LLMAnalysisResult(
                    state=state,
                    confidence=float(data.get("confidence", 0.5)),
                    message=data.get("message", ""),
                    raw_response=raw,
                    suggested_action=data.get("action"),
                    next_element=data.get("element"),
                )
        except Exception as e:
            print(f"⚠️ Ошибка парсинга JSON: {e}")
        
        # Fallback: ищем ключевые слова
        raw_lower = raw.lower()
        
        if "success" in raw_lower and "error" not in raw_lower:
            state = PageState.SUCCESS
        elif "error_email" in raw_lower or ("email" in raw_lower and "error" in raw_lower):
            state = PageState.ERROR_EMAIL
        elif "captcha" in raw_lower:
            state = PageState.CAPTCHA
        elif "loading" in raw_lower:
            state = PageState.LOADING
        elif "form_ready" in raw_lower or ("form" in raw_lower and "ready" in raw_lower):
            state = PageState.FORM_READY
        elif "onboarding" in raw_lower:
            state = PageState.ONBOARDING
        elif "email_confirm" in raw_lower or "check your email" in raw_lower:
            state = PageState.EMAIL_CONFIRM
        else:
            state = PageState.UNKNOWN
        
        return LLMAnalysisResult(
            state=state,
            confidence=0.3,
            message="Parsed from keywords",
            raw_response=raw,
        )
    
    def _parse_onboarding_action(self, raw: str) -> OnboardingAction:
        """Парсинг ответа для действия онбординга"""
        try:
            json_match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                return OnboardingAction(
                    action_type=data.get("action", "wait"),
                    element=data.get("element"),
                    value=data.get("value"),
                    confidence=float(data.get("confidence", 0.5)),
                )
        except Exception as e:
            print(f"⚠️ Ошибка парсинга action: {e}")
        
        # Fallback
        raw_lower = raw.lower()
        if "click" in raw_lower:
            return OnboardingAction(action_type="click", confidence=0.3)
        elif "fill" in raw_lower:
            return OnboardingAction(action_type="fill", confidence=0.3)
        elif "done" in raw_lower:
            return OnboardingAction(action_type="done", confidence=0.3)
        
        return OnboardingAction(action_type="wait", confidence=0.1)


# === Глобальные функции для удобства ===

_default_analyzer: Optional[LocalLLMAnalyzer] = None


def get_analyzer() -> LocalLLMAnalyzer:
    """Получить singleton анализатор"""
    global _default_analyzer
    if _default_analyzer is None:
        _default_analyzer = LocalLLMAnalyzer()
    return _default_analyzer


async def analyze_with_vision(page: Page) -> Optional[LLMAnalysisResult]:
    """
    Анализ страницы через Vision LLM.
    
    Возвращает None если LM Studio недоступен.
    """
    analyzer = get_analyzer()
    if not analyzer.is_available():
        return None
    return await analyzer.analyze_page_vision(page)


async def get_next_onboarding_action(page: Page) -> Optional[OnboardingAction]:
    """
    Получить следующее действие для онбординга.
    
    Возвращает None если LM Studio недоступен.
    """
    analyzer = get_analyzer()
    if not analyzer.is_available():
        return None
    return await analyzer.get_onboarding_action(page)


# === Тест ===
if __name__ == "__main__":
    print("🧪 Тест LocalLLMAnalyzer с Vision")
    print("=" * 50)
    
    analyzer = LocalLLMAnalyzer()
    
    if analyzer.is_available():
        print("✅ LM Studio доступен!")
        print(f"   Модель: {analyzer.model}")
        print(f"   URL: {analyzer.base_url}")
        print("\n   Готов к анализу страниц через Vision!")
    else:
        print("❌ LM Studio недоступен")
        print("   Убедитесь что:")
        print("   1. LM Studio запущен")
        print("   2. Загружена модель qwen2-vl-7b-instruct")
        print("   3. Включен Local Server")
