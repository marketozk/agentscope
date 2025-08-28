"""
Интеллектуальный агент регистрации с AgentScope ReAct архитектурой
ТОЛЬКО НОВАЯ АРХИТЕКТУРА - БЕЗ СТАРОГО КОДА
"""
import asyncio
import os
from playwright.async_api import async_playwright
import google.generativeai as genai
from PIL import Image
import io
import json
from dotenv import load_dotenv
import random
import string
from datetime import datetime, timedelta

# Импортируем новых AgentScope агентов
try:
    from agentscope.model import DashScopeChatModel
    from agentscope.memory import InMemoryMemory
    from src.element_finder_agent import ElementFinderAgent, ElementSearchResult
    from src.error_recovery_agent import ErrorRecoveryAgent, RecoveryResult
    from src.form_filler_agent import FormFillerAgent, FormFillResult
    from src.checkbox_agent import CheckboxAgent, CheckboxActionResult
    from src.page_analyzer_agent import PageAnalyzerAgent, PageAnalysis
    from src.registration_orchestrator import RegistrationOrchestrator
    AGENTSCOPE_AVAILABLE = True
    print("✅ AgentScope модули загружены успешно")
except ImportError as e:
    AGENTSCOPE_AVAILABLE = False
    print(f"❌ AgentScope недоступен: {e}")
    raise RuntimeError("КРИТИЧЕСКАЯ ОШИБКА: AgentScope обязателен для новой архитектуры!")

# Остальные импорты
from src.temp_mail_agent import TempMailAgent
from src.email_verification_agent import EmailVerificationAgent

# Загружаем переменные окружения
load_dotenv()

class IntelligentRegistrationAgent:
    def __init__(self, gemini_api_key: str):
        """Простой координирующий агент"""
        
        # Настройка Gemini для генерации данных
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Генерируем пользовательские данные
        self.context = {}
        
        # Инициализируем только AgentScope агентов
        if not AGENTSCOPE_AVAILABLE:
            raise RuntimeError("❌ AgentScope обязателен для новой архитектуры!")
        
        # Создаём RegistrationOrchestrator - центральный координатор
        try:
            config = {
                "gemini_api_key": gemini_api_key,
                "headless_mode": False,
                "timeout": 30000,
                "retry_attempts": 3
            }
            # Orchestrator работает самостоятельно, без вложенности
            self.registration_orchestrator = RegistrationOrchestrator(config=config)
            print("✅ RegistrationOrchestrator инициализирован")
        except Exception as e:
            print(f"❌ Ошибка инициализации RegistrationOrchestrator: {e}")
            raise

    async def register_with_orchestrator(self, referral_link: str):
        """
        ЕДИНСТВЕННЫЙ метод регистрации через RegistrationOrchestrator
        Обеспечивает централизованную координацию агентов
        """
        print("\n🎭 РЕГИСТРАЦИЯ ТОЛЬКО ЧЕРЕЗ АГЕНТЫ")
        print("=" * 60)
        
        # Проверяем, что AgentScope доступен
        if not AGENTSCOPE_AVAILABLE:
            raise RuntimeError("❌ AgentScope недоступен! Новая архитектура требует AgentScope.")
        
        if not self.registration_orchestrator:
            raise RuntimeError("❌ RegistrationOrchestrator не инициализирован!")
        
        try:
            # Генерируем пользовательские данные
            await self.generate_user_data()
            
            # Передаем URL и пользовательские данные в оркестратор
            user_data = {
                "registration_url": referral_link,
                "user_context": self.context.copy()
            }
            
            print("🎯 Запуск процесса через RegistrationOrchestrator...")
            result = await self.registration_orchestrator.start_registration(
                registration_url=referral_link,
                user_data=self.context
            )
            
            # result - это объект RegistrationResult, не dict
            if result and result.success:
                print("\n🎉 РЕГИСТРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
                print(f"📧 Email: {self.context.get('email', 'неизвестно')}")
                print(f"🔗 URL: {referral_link}")
                print(f"✅ Аккаунт создан: {result.account_created}")
                print(f"✅ Email подтвержден: {result.email_verified}")
                return True
            else:
                error_msg = "Неизвестная ошибка"
                if result and result.errors:
                    error_msg = "; ".join(result.errors)
                print(f"\n❌ Регистрация не удалась: {error_msg}")
                return False
                
        except Exception as e:
            print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА в регистрации: {e}")
            return False

    async def generate_user_data(self):
        """Генерирует реалистичные данные пользователя"""
        print("👤 Генерация данных пользователя...")
        
        # Генерируем уникальные данные
        timestamp = int(datetime.now().timestamp())
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        
        # Базовые данные
        first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
        
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        username = f"{first_name.lower()}{last_name.lower()}{random_suffix}"
        
        self.context = {
            'email': f"{username}@tempmail.com",
            'password': f"SecurePass{timestamp}!",
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'full_name': f"{first_name} {last_name}",
            'phone': f"+1555{random.randint(1000000, 9999999)}",
            'birth_date': f"{random.randint(1990, 2000)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            'company': f"{random.choice(['TechCorp', 'InnovateLab', 'DigitalSoft', 'CloudTech'])}",
            'website': f"https://www.{username}-portfolio.com",
            'country': "United States",
            'city': random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]),
            'zip_code': f"{random.randint(10000, 99999)}",
            'address': f"{random.randint(1, 999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm'])} Street",
            'gender': random.choice(["Male", "Female", "Other"]),
        }
        
        print(f"✅ Данные сгенерированы для: {self.context['full_name']} ({self.context['email']})")


async def main():
    """Главная функция - ТОЛЬКО агентский подход"""
    print("🚀 Запуск системы умной регистрации с AgentScope агентами...")
    
    # Проверяем AgentScope
    if not AGENTSCOPE_AVAILABLE:
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: AgentScope недоступен!")
        print("📦 Установите AgentScope: pip install agentscope")
        return
    
    agent = IntelligentRegistrationAgent(
        gemini_api_key=os.getenv("GEMINI_API_KEY")
    )
    
    referral_link = "https://airtable.com/invite/r/ovoAP1zR"
    print(f"🔗 Используем реферальную ссылку: {referral_link}")
    
    # 🎭 ИСПОЛЬЗУЕМ ТОЛЬКО НОВЫЙ МЕТОД С ORCHESTRATOR!
    print("🎯 Запуск ТОЛЬКО через RegistrationOrchestrator...")
    success = await agent.register_with_orchestrator(referral_link)
    
    if success:
        print("🎉 МИССИЯ ВЫПОЛНЕНА!")
    else:
        print("❌ МИССИЯ ПРОВАЛЕНА!")

if __name__ == "__main__":
    asyncio.run(main())
