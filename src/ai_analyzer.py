"""
AI анализатор страниц с использованием Gemini
"""
import google.generativeai as genai
from typing import Dict, Any, List
import json
import base64
from PIL import Image
import io
import logging
import asyncio
import time
from datetime import datetime, timedelta
from .rate_limits import get_rate_limit_config
from .quota_manager import QuotaManager, FallbackAnalyzer

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """Анализатор страниц с помощью Gemini AI"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        # Используем актуальные модели Gemini 1.5
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.text_model = genai.GenerativeModel('gemini-1.5-flash')
        self.logger = logger
        
        # Quota manager и fallback analyzer
        self.quota_manager = QuotaManager()
        self.fallback_analyzer = FallbackAnalyzer()
        
        # Rate limiting из конфигурации
        config = get_rate_limit_config("gemini")
        self.last_request_time = 0
        self.min_delay_between_requests = config.get("min_delay_between_requests", 10.0)
        self.request_count = 0
        self.requests_per_minute = config.get("requests_per_minute", 3)
        self.minute_start = time.time()
        self.max_retries = config.get("max_retries", 3)
        self.base_retry_delay = config.get("base_retry_delay", 10)
        
    async def _rate_limit_wait(self):
        """Ждет между запросами для соблюдения rate limits"""
        current_time = time.time()
        
        # Проверяем лимит запросов в минуту
        if current_time - self.minute_start >= 60:
            self.request_count = 0
            self.minute_start = current_time
        
        if self.request_count >= self.requests_per_minute:
            wait_time = 60 - (current_time - self.minute_start)
            if wait_time > 0:
                self.logger.info(f"Rate limit: ожидание {wait_time:.1f} секунд")
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.minute_start = time.time()
        
        # Минимальная задержка между запросами
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay_between_requests:
            wait_time = self.min_delay_between_requests - time_since_last
            self.logger.info(f"Задержка между запросами: {wait_time:.1f} секунд")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
    async def analyze_page(self, screenshot: bytes, page_text: str, page_html: str) -> Dict[str, Any]:
        """Анализирует страницу и возвращает структурированные данные"""
        
        # Соблюдаем rate limits
        await self._rate_limit_wait()
        
        # Преобразуем скриншот для Gemini
        image = Image.open(io.BytesIO(screenshot))
        
        prompt = """
        Проанализируй эту веб-страницу и определи:
        
        1. Тип страницы (registration_form, login, email_verification, success, etc.)
        2. Все поля ввода с их назначением
        3. Кнопки и их действия
        4. Наличие капчи
        
        Текст страницы:
        {text}
        
        Верни JSON:
        {{
            "page_type": "тип",
            "has_form": true/false,
            "fields": [
                {{
                    "selector": "селектор",
                    "type": "тип",
                    "label": "название",
                    "required": true/false
                }}
            ],
            "buttons": [
                {{
                    "selector": "селектор",
                    "text": "текст",
                    "action": "действие"
                }}
            ],
            "has_captcha": true/false
        }}
        """.format(text=page_text[:1000])
        
        # Retry механизм при rate limit ошибках
        for attempt in range(self.max_retries):
            try:
                response = self.model.generate_content([prompt, image])
                json_text = response.text.strip()
                
                # Очистка от markdown
                if '```' in json_text:
                    json_text = json_text.split('```')[1]
                    if json_text.startswith('json'):
                        json_text = json_text[4:]
                
                return json.loads(json_text.strip())
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    # Rate limit exceeded - ждем дольше
                    retry_delay = self.base_retry_delay * (2 ** attempt)  # Экспоненциальная задержка
                    self.logger.warning(f"Rate limit exceeded, попытка {attempt + 1}/{self.max_retries}, ожидание {retry_delay} секунд")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                
                self.logger.error(f"Ошибка ИИ анализа (попытка {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    # Последняя попытка неудачна - используем fallback
                    return self._fallback_analysis(page_html, page_text)
        
        # Если все попытки неудачны
        return self._fallback_analysis(page_html, page_text)
    
    def _fallback_analysis(self, page_html: str, page_text: str) -> Dict[str, Any]:
        """Базовый анализ без ИИ"""
        import re
        
        # Простой поиск форм и полей
        has_form = '<form' in page_html.lower()
        has_input = '<input' in page_html.lower()
        has_button = '<button' in page_html.lower() or 'type="submit"' in page_html.lower()
        
        # Определяем тип страницы по ключевым словам
        page_type = "unknown"
        if any(word in page_text.lower() for word in ['register', 'registration', 'sign up', 'регистр']):
            page_type = "registration_form"
        elif any(word in page_text.lower() for word in ['login', 'sign in', 'вход']):
            page_type = "login"
        elif any(word in page_text.lower() for word in ['verify', 'confirm', 'подтвержд']):
            page_type = "email_verification"
        
        return {
            "page_type": page_type,
            "has_form": has_form,
            "fields": [],
            "buttons": [],
            "has_captcha": False,
            "analysis_method": "fallback"
        }

class ActionPlanner:
    """Планировщик действий на основе анализа страницы"""
    
    def __init__(self, ai_analyzer: GeminiAnalyzer):
        self.ai_analyzer = ai_analyzer
        
    async def plan_actions(self, page_analysis: Dict, context: Dict) -> List[Dict]:
        """Планирует последовательность действий"""
        actions = []
        
        # Если есть форма с полями
        if page_analysis.get('has_form') and page_analysis.get('fields'):
            # Определяем какие данные нужны
            for field in page_analysis['fields']:
                if field.get('required'):
                    actions.append({
                        'type': 'request_user_input',
                        'field': field
                    })
                    actions.append({
                        'type': 'fill_field',
                        'selector': field['selector'],
                        'field_info': field
                    })
            
            # Добавляем клик по кнопке
            submit_buttons = [
                btn for btn in page_analysis.get('buttons', [])
                if 'submit' in btn.get('action', '').lower()
            ]
            if submit_buttons:
                actions.append({
                    'type': 'click_button',
                    'selector': submit_buttons[0]['selector']
                })
        
        return actions