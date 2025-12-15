"""
🤖 LocalLLMAnalyzer - анализ страниц через локальную LLM (LM Studio)

Использует OpenAI-совместимый API LM Studio для анализа:
- Текста страницы
- HTML элементов
- Сообщений об ошибках

Модель: gpt-oss 20B (текстовая, без vision)
Endpoint: http://127.0.0.1:1234/v1
"""

import asyncio
from typing import Optional, Dict, List
from enum import Enum
from dataclasses import dataclass
from playwright.async_api import Page

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class PageState(Enum):
    """Состояния страницы, определяемые LLM"""
    SUCCESS = "success"           # Регистрация успешна
    ERROR_EMAIL = "error_email"   # Ошибка email (невалидный/занят)
    ERROR_OTHER = "error_other"   # Другая ошибка
    CAPTCHA = "captcha"           # Требуется капча
    LOADING = "loading"           # Страница загружается
    FORM_READY = "form_ready"     # Форма готова к заполнению
    ONBOARDING = "onboarding"     # Шаг онбординга
    UNKNOWN = "unknown"           # Неизвестное состояние


@dataclass
class LLMAnalysisResult:
    """Результат анализа страницы через LLM"""
    state: PageState
    confidence: float  # 0.0 - 1.0
    message: str
    raw_response: str
    suggested_action: Optional[str] = None


class LocalLLMAnalyzer:
    """
    Анализатор страниц через локальную LLM (LM Studio).
    
    Использование:
        analyzer = LocalLLMAnalyzer()
        if analyzer.is_available():
            result = await analyzer.analyze_page(page)
            if result.state == PageState.ERROR_EMAIL:
                print(f"Ошибка email: {result.message}")
    """
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:1234/v1",
        model: str = "gpt-oss-20b",  # имя модели в LM Studio
        api_key: str = "lm-studio",  # LM Studio не проверяет ключ
        timeout: float = 30.0,
    ):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[OpenAI] = None
        self._available: Optional[bool] = None
    
    def _init_client(self) -> bool:
        """Инициализация клиента OpenAI"""
        if not HAS_OPENAI:
            print("⚠️ OpenAI библиотека не установлена: pip install openai")
            return False
        
        try:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout,
            )
            return True
        except Exception as e:
            print(f"⚠️ Ошибка инициализации OpenAI клиента: {e}")
            return False
    
    def is_available(self) -> bool:
        """Проверить доступность LM Studio"""
        if self._available is not None:
            return self._available
        
        if not self._init_client():
            self._available = False
            return False
        
        try:
            # Пробуем простой запрос
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            self._available = True
            print(f"✅ LM Studio доступен: {self.base_url}")
            return True
        except Exception as e:
            print(f"⚠️ LM Studio недоступен: {e}")
            self._available = False
            return False
    
    async def analyze_page(self, page: Page) -> LLMAnalysisResult:
        """
        Анализировать страницу через LLM.
        
        Извлекает текст и ключевые элементы страницы,
        отправляет в LLM для классификации состояния.
        """
        if not self._client:
            if not self._init_client():
                return LLMAnalysisResult(
                    state=PageState.UNKNOWN,
                    confidence=0.0,
                    message="LLM клиент не инициализирован",
                    raw_response="",
                )
        
        # Извлекаем контекст страницы
        page_context = await self._extract_page_context(page)
        
        # Формируем промпт
        prompt = self._build_analysis_prompt(page_context)
        
        # Отправляем в LLM
        try:
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a web page state analyzer. Respond ONLY with a JSON object."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.1,  # Низкая температура для детерминизма
            )
            
            raw = response.choices[0].message.content.strip()
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
        
        # Извлекаем структурированные данные через JS
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
                    
                    // Видимый текст (первые 2000 символов)
                    result.visible_text = document.body.innerText.substring(0, 2000);
                    
                    // Сообщения об ошибках
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
                    
                    // Сообщения об успехе
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
                    
                    // Кнопки
                    document.querySelectorAll('button:not([hidden])').forEach(btn => {
                        const text = btn.innerText.trim();
                        if (text) result.buttons.push(text.substring(0, 50));
                    });
                    
                    // Поля ввода
                    document.querySelectorAll('input:not([type="hidden"])').forEach(inp => {
                        result.inputs.push({
                            type: inp.type,
                            name: inp.name,
                            placeholder: inp.placeholder,
                        });
                    });
                    
                    // Дедупликация
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
    
    def _build_analysis_prompt(self, context: Dict) -> str:
        """Построить промпт для анализа"""
        prompt = f"""Analyze this web page state and classify it.

URL: {context.get('url', 'unknown')}
Title: {context.get('title', 'unknown')}

Error messages found: {context.get('error_messages', [])}
Success messages found: {context.get('success_messages', [])}
Buttons visible: {context.get('buttons', [])}
Input fields: {len(context.get('inputs', []))} fields

Page text (excerpt):
{context.get('visible_text', '')[:1000]}

---

Classify the page state as ONE of:
- SUCCESS: Registration completed successfully
- ERROR_EMAIL: Email validation error (invalid, already exists, domain rejected)
- ERROR_OTHER: Other error occurred
- CAPTCHA: Captcha/robot verification required
- LOADING: Page is still loading
- FORM_READY: Registration form is ready to fill
- ONBOARDING: Post-registration onboarding step
- UNKNOWN: Cannot determine state

Respond with JSON only:
{{"state": "STATE_NAME", "confidence": 0.0-1.0, "message": "brief explanation", "action": "suggested next action or null"}}
"""
        return prompt
    
    def _parse_llm_response(self, raw: str) -> LLMAnalysisResult:
        """Парсинг ответа LLM"""
        import json
        import re
        
        # Пробуем извлечь JSON из ответа
        try:
            # Ищем JSON в ответе
            json_match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                state_str = data.get("state", "UNKNOWN").upper()
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
                )
        except Exception as e:
            print(f"⚠️ Ошибка парсинга JSON: {e}")
        
        # Fallback: пробуем найти ключевые слова
        raw_lower = raw.lower()
        
        if "success" in raw_lower:
            state = PageState.SUCCESS
        elif "error_email" in raw_lower or "email" in raw_lower and "error" in raw_lower:
            state = PageState.ERROR_EMAIL
        elif "captcha" in raw_lower:
            state = PageState.CAPTCHA
        elif "loading" in raw_lower:
            state = PageState.LOADING
        elif "form_ready" in raw_lower or "form" in raw_lower:
            state = PageState.FORM_READY
        elif "onboarding" in raw_lower:
            state = PageState.ONBOARDING
        else:
            state = PageState.UNKNOWN
        
        return LLMAnalysisResult(
            state=state,
            confidence=0.3,  # Низкая уверенность при fallback
            message="Parsed from keywords",
            raw_response=raw,
        )


# === Быстрые функции для использования ===

_default_analyzer: Optional[LocalLLMAnalyzer] = None

def get_analyzer() -> LocalLLMAnalyzer:
    """Получить singleton анализатор"""
    global _default_analyzer
    if _default_analyzer is None:
        _default_analyzer = LocalLLMAnalyzer()
    return _default_analyzer


async def analyze_with_llm(page: Page) -> Optional[LLMAnalysisResult]:
    """
    Быстрый анализ страницы через локальную LLM.
    
    Возвращает None если LM Studio недоступен.
    """
    analyzer = get_analyzer()
    if not analyzer.is_available():
        return None
    return await analyzer.analyze_page(page)


async def is_email_error_llm(page: Page) -> bool:
    """Проверка: есть ли ошибка email (через LLM)"""
    result = await analyze_with_llm(page)
    if result and result.state == PageState.ERROR_EMAIL:
        return True
    return False


# === Тест ===
if __name__ == "__main__":
    print("🧪 Тест LocalLLMAnalyzer")
    
    analyzer = LocalLLMAnalyzer()
    
    if analyzer.is_available():
        print("✅ LM Studio доступен!")
        print(f"   Модель: {analyzer.model}")
        print(f"   URL: {analyzer.base_url}")
    else:
        print("❌ LM Studio недоступен")
        print("   Убедитесь что LM Studio запущен и модель загружена")
