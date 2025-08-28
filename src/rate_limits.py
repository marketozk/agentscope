"""
Настройки rate limits для различных API
"""

# Gemini API Rate Limits
GEMINI_RATE_LIMITS = {
    # Лимиты для gemini-1.5-flash
    "min_delay_between_requests": 4.0,   # секунды между запросами (15 RPM = 4 сек)
    "requests_per_minute": 15,           # максимум запросов в минуту для flash
    "requests_per_day": 1500,           # дневной лимит для flash модели
    
    # Retry настройки
    "max_retries": 3,                  # максимум попыток
    "base_retry_delay": 10,            # базовая задержка для retry (секунды)
    "exponential_backoff": True,       # использовать экспоненциальную задержку
    
    # Кэш настройки
    "cache_ttl": 300,                  # время жизни кэша (секунды)
    "enable_cache": True,              # включить кэширование
}

# temp-mail.io Rate Limits
TEMP_MAIL_RATE_LIMITS = {
    "min_delay_between_requests": 1.0,
    "requests_per_minute": 30,
    "max_retries": 2,
    "base_retry_delay": 5,
}

def get_rate_limit_config(service: str) -> dict:
    """Получить конфигурацию rate limits для сервиса"""
    configs = {
        "gemini": GEMINI_RATE_LIMITS,
        "temp_mail": TEMP_MAIL_RATE_LIMITS,
    }
    return configs.get(service, {})
