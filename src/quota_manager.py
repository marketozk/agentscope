"""
Менеджер квот для экономного использования API
"""
import json
import time
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class QuotaManager:
    """Управление квотами и кэшированием для API"""
    
    def __init__(self, cache_file: str = "api_cache.json"):
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.daily_requests = 0
        self.last_reset = datetime.now().date()
        
    def _load_cache(self) -> Dict[str, Any]:
        """Загрузить кэш из файла"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"responses": {}, "counters": {"daily_requests": 0, "last_reset": None}}
    
    def _save_cache(self):
        """Сохранить кэш в файл"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения кэша: {e}")
    
    def _get_cache_key(self, content: str, prompt: str) -> str:
        """Создать ключ кэша на основе контента и промпта"""
        combined = f"{content[:500]}:{prompt}"  # Первые 500 символов контента + промпт
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get_cached_response(self, content: str, prompt: str) -> Optional[Dict[str, Any]]:
        """Получить кэшированный ответ"""
        cache_key = self._get_cache_key(content, prompt)
        cached = self.cache["responses"].get(cache_key)
        
        if cached:
            # Проверить, не устарел ли кэш (TTL = 1 час)
            cached_time = datetime.fromisoformat(cached["timestamp"])
            if datetime.now() - cached_time < timedelta(hours=1):
                logger.info("Используется кэшированный ответ")
                return cached["response"]
            else:
                # Удалить устаревший кэш
                del self.cache["responses"][cache_key]
        
        return None
    
    def save_response(self, content: str, prompt: str, response: Dict[str, Any]):
        """Сохранить ответ в кэш"""
        cache_key = self._get_cache_key(content, prompt)
        self.cache["responses"][cache_key] = {
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
        self._save_cache()
    
    def can_make_request(self) -> bool:
        """Проверить, можно ли сделать запрос с учетом дневных лимитов"""
        current_date = datetime.now().date()
        
        # Сброс счетчика в новый день
        if self.last_reset != current_date:
            self.daily_requests = 0
            self.last_reset = current_date
            self.cache["counters"] = {
                "daily_requests": 0,
                "last_reset": current_date.isoformat()
            }
        
        # Проверить дневной лимит
        return self.daily_requests < 30  # Консервативный лимит
    
    def increment_request_count(self):
        """Увеличить счетчик запросов"""
        self.daily_requests += 1
        self.cache["counters"]["daily_requests"] = self.daily_requests
        self._save_cache()
    
    def wait_for_quota_reset(self) -> int:
        """Время до сброса квот в секундах"""
        now = datetime.now()
        tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        return int((tomorrow - now).total_seconds())

class FallbackAnalyzer:
    """Запасной анализатор для случаев превышения квоты"""
    
    def __init__(self):
        self.logger = logger
    
    def analyze_simple_registration_form(self, content: str) -> Dict[str, Any]:
        """Простой анализ формы регистрации без AI"""
        actions = []
        
        # Поиск полей формы
        common_inputs = [
            ('email', ['email', 'e-mail', 'mail']),
            ('password', ['password', 'pass', 'pwd']),
            ('username', ['username', 'user', 'login']),
            ('name', ['name', 'firstname', 'lastname']),
            ('submit', ['submit', 'register', 'signup', 'sign up'])
        ]
        
        content_lower = content.lower()
        
        for field_type, keywords in common_inputs:
            for keyword in keywords:
                if keyword in content_lower:
                    if field_type == 'submit':
                        actions.append({
                            'action': 'click',
                            'selector': f'input[type="submit"], button[type="submit"], button:contains("{keyword}")',
                            'description': f'Нажать кнопку {keyword}'
                        })
                    else:
                        actions.append({
                            'action': 'input',
                            'selector': f'input[name*="{keyword}"], input[id*="{keyword}"]',
                            'value': f'test_{field_type}@example.com' if field_type == 'email' else f'test_{field_type}',
                            'description': f'Заполнить поле {field_type}'
                        })
                    break
        
        return {
            'success': True,
            'actions': actions,
            'confidence': 'low',
            'method': 'fallback'
        }
