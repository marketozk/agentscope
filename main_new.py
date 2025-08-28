"""
Простой запускатель системы автоматической регистрации
Вся логика и мощность теперь в RegistrationOrchestrator
"""
import asyncio
import os
from dotenv import load_dotenv

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
    exit(1)

# Загружаем переменные окружения
load_dotenv()

async def main():
    """Простой запускатель - вся мощность в RegistrationOrchestrator"""
    print("🚀 Запуск системы умной регистрации с AgentScope агентами...")
    
    # Проверяем AgentScope
    if not AGENTSCOPE_AVAILABLE:
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: AgentScope недоступен!")
        print("📦 Установите AgentScope: pip install agentscope")
        return False
    
    # Создаём конфигурацию
    config = {
        "gemini_api_key": os.getenv("GEMINI_API_KEY"),
        "headless_mode": False,
        "timeout": 30000,
        "retry_attempts": 3,
        "max_steps": 25,
        "screenshot_on_error": True
    }
    
    if not config["gemini_api_key"]:
        print("❌ Gemini API ключ не найден в переменных окружения!")
        return False
    
    # Создаём ЕДИНСТВЕННЫЙ координатор системы
    orchestrator = RegistrationOrchestrator(config=config)
    
    referral_link = "https://airtable.com/invite/r/ovoAP1zR"
    print(f"🔗 Используем реферальную ссылку: {referral_link}")
    
    # Вся мощность системы теперь в orchestrator
    print("🎯 Запуск ВСЕЙ МОЩНОСТИ через RegistrationOrchestrator...")
    result = await orchestrator.start_registration(
        registration_url=referral_link,
        user_data={}  # Orchestrator сам сгенерирует данные
    )
    
    # Показываем результат
    if result and result.success:
        print("\n🎉 МИССИЯ ВЫПОЛНЕНА!")
        print(f"✅ Аккаунт создан: {result.account_created}")
        print(f"✅ Email подтвержден: {result.email_verified}")
        if result.credentials:
            print(f"📧 Email: {result.credentials.get('email', 'неизвестно')}")
        return True
    else:
        error_msg = "Неизвестная ошибка"
        if result and result.errors:
            error_msg = "; ".join(result.errors)
        print(f"\n❌ МИССИЯ ПРОВАЛЕНА: {error_msg}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
