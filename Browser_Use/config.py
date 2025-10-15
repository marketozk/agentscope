"""
Конфигурация и управление rate limits для Browser-Use + Gemini
"""

import os
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from browser_use.llm.google import ChatGoogle
from datetime import datetime, timedelta

# Загружаем переменные окружения
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


# ==================== КОНСТАНТЫ МОДЕЛЕЙ ====================

class ModelConfig:
    """Конфигурация моделей Gemini"""
    
    # Все доступные модели
    MODELS = {
        "gemini-2.5-flash": {
            "name": "gemini-2.5-flash",
            "model_string": "gemini-2.5-flash",
            "requests_per_minute": 10,
            "requests_per_day": 1500,
            "description": "Новейшая 2.5 модель, работает стабильно",
            "recommended_for": "production, рекомендуется"
        },
        "gemini-2.0-flash-exp": {
            "name": "gemini-2.0-flash-exp",
            "model_string": "gemini-2.0-flash-exp",
            "requests_per_minute": 15,
            "requests_per_day": 1500,
            "description": "Экспериментальная 2.0 модель",
            "recommended_for": "тестирование"
        },
        "gemini-flash-latest": {
            "name": "gemini-flash-latest",
            "model_string": "gemini-flash-latest",
            "requests_per_minute": 15,
            "requests_per_day": 1500,
            "description": "Последняя стабильная версия",
            "recommended_for": "автообновление"
        },
        "gemini-2.5-pro": {
            "name": "gemini-2.5-pro",
            "model_string": "gemini-2.5-pro",
            "requests_per_minute": 5,
            "requests_per_day": 500,
            "description": "Продвинутая модель для сложных задач",
            "recommended_for": "сложные задачи"
        }
    }
    
    @classmethod
    def get_config(cls, model_name: str = "gemini-2.5-flash"):
        """
        Получить конфигурацию модели по имени
        
        Args:
            model_name: Имя модели из доступных вариантов
        
        Returns:
            dict: Конфигурация модели
        """
        if model_name in cls.MODELS:
            return cls.MODELS[model_name]
        
        # Если модель не найдена, возвращаем gemini-2.5-flash по умолчанию
        print(f"⚠️  Модель '{model_name}' не найдена, используется gemini-2.5-flash")
        return cls.MODELS["gemini-2.5-flash"]
    
    @classmethod
    def list_models(cls):
        """Вывести список всех доступных моделей"""
        print("\n📋 ДОСТУПНЫЕ МОДЕЛИ GEMINI:")
        print("="*70)
        for key, config in cls.MODELS.items():
            print(f"\n🤖 {key}")
            print(f"   {config['description']}")
            print(f"   Rate: {config['requests_per_minute']} запросов/мин, {config['requests_per_day']} запросов/день")
            print(f"   Для: {config['recommended_for']}")
        print("="*70)


# ==================== RATE LIMITER ====================

class RateLimiter:
    """Управление rate limits для API запросов"""
    
    def __init__(self, requests_per_minute: int, requests_per_day: int):
        self.requests_per_minute = requests_per_minute
        self.requests_per_day = requests_per_day
        
        # История запросов
        self.minute_requests = []
        self.day_requests = []
        
        # Статистика
        self.total_requests = 0
        self.blocked_requests = 0
        
    def _cleanup_old_requests(self):
        """Удаление старых записей из истории"""
        now = datetime.now()
        
        # Очистка минутного окна
        minute_ago = now - timedelta(minutes=1)
        self.minute_requests = [t for t in self.minute_requests if t > minute_ago]
        
        # Очистка дневного окна
        day_ago = now - timedelta(days=1)
        self.day_requests = [t for t in self.day_requests if t > day_ago]
    
    def can_make_request(self) -> tuple[bool, str]:
        """
        Проверка возможности выполнения запроса
        Returns: (можно_выполнить, причина_отказа)
        """
        self._cleanup_old_requests()
        
        # Проверка минутного лимита
        if len(self.minute_requests) >= self.requests_per_minute:
            wait_time = 60 - (datetime.now() - self.minute_requests[0]).seconds
            return False, f"Превышен лимит {self.requests_per_minute} запросов/мин. Подождите {wait_time}с"
        
        # Проверка дневного лимита
        if len(self.day_requests) >= self.requests_per_day:
            oldest = self.day_requests[0]
            wait_time = (oldest + timedelta(days=1) - datetime.now()).seconds
            wait_hours = wait_time // 3600
            return False, f"Превышен дневной лимит {self.requests_per_day} запросов. Подождите {wait_hours}ч"
        
        return True, ""
    
    def register_request(self):
        """Регистрация выполненного запроса"""
        now = datetime.now()
        self.minute_requests.append(now)
        self.day_requests.append(now)
        self.total_requests += 1
    
    async def wait_if_needed(self) -> bool:
        """
        Ожидание если нужно соблюсти rate limit
        Returns: True если запрос можно выполнить, False если достигнут дневной лимит
        """
        can_request, reason = self.can_make_request()
        
        if can_request:
            return True
        
        # Если это дневной лимит - не ждём
        if "дневной лимит" in reason:
            print(f"⛔ {reason}")
            self.blocked_requests += 1
            return False
        
        # Если минутный лимит - ждём
        if "лимит" in reason and "запросов/мин" in reason:
            # Извлекаем время ожидания
            wait_seconds = int(reason.split("Подождите ")[1].split("с")[0])
            print(f"⏳ {reason}")
            print(f"⏰ Ожидание {wait_seconds} секунд...")
            await asyncio.sleep(wait_seconds + 1)  # +1 для надёжности
            return True
        
        return False
    
    def get_stats(self) -> dict:
        """Получить статистику использования"""
        self._cleanup_old_requests()
        return {
            "total_requests": self.total_requests,
            "blocked_requests": self.blocked_requests,
            "minute_remaining": self.requests_per_minute - len(self.minute_requests),
            "day_remaining": self.requests_per_day - len(self.day_requests),
            "minute_used": len(self.minute_requests),
            "day_used": len(self.day_requests)
        }
    
    def print_stats(self):
        """Вывести статистику в консоль"""
        stats = self.get_stats()
        print("\n" + "="*60)
        print("📊 СТАТИСТИКА ИСПОЛЬЗОВАНИЯ API")
        print("="*60)
        print(f"Всего запросов: {stats['total_requests']}")
        print(f"Заблокировано: {stats['blocked_requests']}")
        print(f"\nТекущая минута: {stats['minute_used']}/{self.requests_per_minute} "
              f"(осталось: {stats['minute_remaining']})")
        print(f"Текущий день: {stats['day_used']}/{self.requests_per_day} "
              f"(осталось: {stats['day_remaining']})")
        print("="*60)


# ==================== КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ ====================

class AppConfig:
    """Основная конфигурация приложения"""
    
    def __init__(self):
        # API ключ
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "❌ GOOGLE_API_KEY не найден в .env файле!\n"
                "Создайте файл .env на основе .env.example"
            )
        
        # Выбор модели из переменной окружения
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.model_config = ModelConfig.get_config(model_name)
        
        # Rate limiter
        self.rate_limiter = RateLimiter(
            requests_per_minute=self.model_config["requests_per_minute"],
            requests_per_day=self.model_config["requests_per_day"]
        )
        
        # Профиль браузера
        self.profile_path = Path(__file__).parent / "profile_data"
        self.profile_path.mkdir(exist_ok=True)
        
        # Установка API ключа в окружение
        os.environ.setdefault("GOOGLE_API_KEY", self.api_key)
    
    def get_llm(self):
        """Получить LLM модель"""
        return ChatGoogle(
            model=self.model_config["model_string"],
            temperature=0.2,
            api_key=self.api_key
        )
    
    def print_config(self):
        """Вывести текущую конфигурацию"""
        print("\n" + "="*60)
        print("⚙️  КОНФИГУРАЦИЯ")
        print("="*60)
        print(f"🤖 Модель: {self.model_config['name']}")
        print(f"📝 Описание: {self.model_config['description']}")
        print(f"⚡ Rate Limits:")
        print(f"   - {self.model_config['requests_per_minute']} запросов/минуту")
        print(f"   - {self.model_config['requests_per_day']} запросов/день")
        print(f"💡 Рекомендовано для: {self.model_config['recommended_for']}")
        print(f"📁 Профиль браузера: {self.profile_path}")
        print("="*60)


# ==================== ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ====================

_app_config = None

def get_app_config() -> AppConfig:
    """Получить глобальный экземпляр конфигурации (singleton)"""
    global _app_config
    if _app_config is None:
        _app_config = AppConfig()
    return _app_config


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_llm():
    """Получить LLM с учётом конфигурации"""
    config = get_app_config()
    return config.get_llm()


def get_profile_path():
    """Получить путь к профилю браузера"""
    config = get_app_config()
    return config.profile_path


def get_rate_limiter() -> RateLimiter:
    """Получить rate limiter"""
    config = get_app_config()
    return config.rate_limiter


async def wait_for_rate_limit() -> bool:
    """
    Подождать если нужно для соблюдения rate limit
    Returns: True если можно продолжить, False если достигнут дневной лимит
    """
    rate_limiter = get_rate_limiter()
    return await rate_limiter.wait_if_needed()


def register_api_request():
    """Зарегистрировать выполненный API запрос"""
    rate_limiter = get_rate_limiter()
    rate_limiter.register_request()


def print_api_stats():
    """Вывести статистику использования API"""
    rate_limiter = get_rate_limiter()
    rate_limiter.print_stats()


# ==================== ДЕМОНСТРАЦИЯ ====================

if __name__ == "__main__":
    """Тестирование конфигурации"""
    
    import sys
    
    # Проверяем аргументы
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        ModelConfig.list_models()
        exit(0)
    
    print("\n🧪 ТЕСТИРОВАНИЕ КОНФИГУРАЦИИ\n")
    
    try:
        # Инициализация
        config = get_app_config()
        config.print_config()
        
        # Тест rate limiter
        print("\n🧪 Тест Rate Limiter:")
        rate_limiter = get_rate_limiter()
        
        # Симуляция запросов
        for i in range(5):
            can_request, reason = rate_limiter.can_make_request()
            if can_request:
                print(f"✅ Запрос {i+1}: Разрешён")
                rate_limiter.register_request()
            else:
                print(f"⛔ Запрос {i+1}: {reason}")
        
        # Статистика
        rate_limiter.print_stats()
        
        print("\n💡 Совет: Используйте 'python config.py --list' для списка всех моделей")
        
    except ValueError as e:
        print(f"\n❌ Ошибка: {e}")
        print("\nСоздайте файл .env на основе .env.example")
