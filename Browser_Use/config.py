"""
Конфигурация и управление rate limits для Browser-Use + Gemini
"""

import os
import time
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv
from browser_use.llm.google import ChatGoogle
from langchain_openai import ChatOpenAI
from datetime import datetime, timedelta

# Загружаем переменные окружения
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


# ==================== КОНСТАНТЫ МОДЕЛЕЙ ====================

class ModelConfig:
    """Конфигурация моделей Gemini из JSON файла"""
    
    CONFIG_FILE = Path(__file__).parent / "models_config.json"
    
    @classmethod
    def load_from_json(cls):
        """Загрузить конфигурацию из JSON файла"""
        try:
            with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"❌ Файл {cls.CONFIG_FILE} не найден!\n"
                "Создайте models_config.json с конфигурацией моделей."
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ Ошибка парсинга JSON: {e}")
    
    @classmethod
    def get_enabled_model(cls):
        """Получить активную модель (с enabled: true)"""
        config_data = cls.load_from_json()
        models = config_data.get("models", {})
        
        enabled_models = {
            name: cfg for name, cfg in models.items() 
            if cfg.get("enabled", False)
        }
        
        if not enabled_models:
            raise ValueError(
                "❌ Ни одна модель не активирована!\n"
                "Установите enabled: true для нужной модели в models_config.json"
            )
        
        if len(enabled_models) > 1:
            print(f"⚠️  Найдено {len(enabled_models)} активных моделей, используется первая")
        
        # Возвращаем первую активную модель
        model_name = list(enabled_models.keys())[0]
        model_config = enabled_models[model_name]
        model_config["name"] = model_name  # Добавляем имя в конфиг
        
        return model_config
    
    @classmethod
    def get_config(cls, model_name: str = None):
        """
        Получить конфигурацию модели
        Если model_name не указан, возвращает активную модель
        """
        if model_name is None:
            return cls.get_enabled_model()
        
        config_data = cls.load_from_json()
        models = config_data.get("models", {})
        
        if model_name in models:
            config = models[model_name]
            config["name"] = model_name
            return config
        
        raise ValueError(f"❌ Модель '{model_name}' не найдена в конфиге")
    
    @classmethod
    def list_models(cls):
        """Вывести список всех доступных моделей"""
        try:
            config_data = cls.load_from_json()
            models = config_data.get("models", {})
            
            print("\n📋 ДОСТУПНЫЕ МОДЕЛИ GEMINI:")
            print("="*70)
            
            for name, config in models.items():
                enabled = "✅ АКТИВНА" if config.get("enabled") else "⚪ Выключена"
                print(f"\n🤖 {name} - {enabled}")
                print(f"   {config['description']}")
                print(f"   Rate: {config['requests_per_minute']} запросов/мин, {config['requests_per_day']} запросов/день")
                print(f"   Для: {config['recommended_for']}")
            
            print("="*70)
            print("\n💡 Совет: Установите 'enabled: true' в models_config.json для нужной модели")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")


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
        
        # Выбор активной модели из JSON конфига
        self.model_config = ModelConfig.get_enabled_model()
        
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
        provider = self.model_config.get("provider", "google")
        
        if provider == "google":
            return ChatGoogle(
                model=self.model_config["model_string"],
                temperature=0.2,
                api_key=self.api_key
            )
        elif provider == "deepseek":
            deepseek_key = os.getenv("DEEPSEEK_API_KEY")
            if not deepseek_key:
                raise ValueError("❌ DEEPSEEK_API_KEY не найден в .env файле!")
            
            return ChatOpenAI(
                model=self.model_config["model_string"],
                temperature=0.2,
                api_key=deepseek_key,
                base_url="https://api.deepseek.com"
            )
        else:
            raise ValueError(f"❌ Неизвестный провайдер: {provider}")
    
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
