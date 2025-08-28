#!/usr/bin/env python3
"""Тест импорта AgentScope и RegistrationOrchestrator"""

try:
    from agentscope.model import DashScopeChatModel
    print("✅ AgentScope импортируется успешно")
    AGENTSCOPE_AVAILABLE = True
except Exception as e:
    print(f"❌ AgentScope недоступен: {e}")
    AGENTSCOPE_AVAILABLE = False

try:
    from src.registration_orchestrator import RegistrationOrchestrator
    print("✅ RegistrationOrchestrator импортируется успешно")
    
    # Пробуем создать экземпляр
    orchestrator = RegistrationOrchestrator()
    print("✅ RegistrationOrchestrator создается успешно")
    
except Exception as e:
    print(f"❌ RegistrationOrchestrator ошибка: {e}")

print(f"\nИтог: AGENTSCOPE_AVAILABLE = {AGENTSCOPE_AVAILABLE}")
