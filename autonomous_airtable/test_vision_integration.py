"""
🧪 Тест интеграции Vision Onboarding Agent

Тестирует:
1. Подключение к LM Studio
2. Анализ скриншота через Vision LLM
3. VisionOnboardingAgent (mock-тест)
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from local_llm_analyzer import LocalLLMAnalyzer, get_analyzer, PageState
from vision_onboarding_agent import VisionOnboardingAgent, OnboardingResult


async def test_llm_connection():
    """Тест 1: Подключение к LM Studio"""
    print("\n" + "=" * 60)
    print("🧪 Тест 1: Подключение к LM Studio")
    print("=" * 60)
    
    analyzer = get_analyzer()
    
    if analyzer.is_available():
        print("✅ LM Studio доступен!")
        print(f"   URL: {analyzer.base_url}")
        print(f"   Model: {analyzer.model}")
        return True
    else:
        print("❌ LM Studio недоступен!")
        print("   Убедитесь что:")
        print("   1. LM Studio запущен")
        print("   2. Загружена модель qwen2-vl-7b-instruct")
        print("   3. Local Server включен (порт 1234)")
        return False


async def test_text_analysis():
    """Тест 2: Текстовый анализ"""
    print("\n" + "=" * 60)
    print("🧪 Тест 2: Текстовый запрос к LLM")
    print("=" * 60)
    
    analyzer = get_analyzer()
    
    if not analyzer.is_available():
        print("⚠️ Пропуск - LM Studio недоступен")
        return False
    
    try:
        response = analyzer._send_request([
            {"role": "user", "content": "What is 2+2? Answer with just the number."}
        ], timeout=30)
        
        print(f"✅ Ответ LLM: {response}")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def test_vision_analysis_file():
    """Тест 3: Vision анализ существующего скриншота"""
    print("\n" + "=" * 60)
    print("🧪 Тест 3: Vision анализ скриншота")
    print("=" * 60)
    
    analyzer = get_analyzer()
    
    if not analyzer.is_available():
        print("⚠️ Пропуск - LM Studio недоступен")
        return False
    
    # Ищем скриншот для теста
    screenshot_paths = [
        Path("debug_screenshots/after_click_email.png"),
        Path("../debug_screenshots/after_click_email.png"),
        Path("debug_screenshots/onboarding_step_1.png"),
    ]
    
    screenshot_path = None
    for p in screenshot_paths:
        if p.exists():
            screenshot_path = p
            break
    
    if not screenshot_path:
        print("⚠️ Скриншот не найден, пропуск теста vision")
        return True  # Не ошибка, просто нет файла
    
    print(f"   📸 Используем: {screenshot_path}")
    
    import base64
    with open(screenshot_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode()
    
    prompt = """Analyze this screenshot. What do you see?
Is this a:
- Login/signup page
- Email inbox
- Onboarding step
- Dashboard
- Error page

Answer briefly in 1-2 sentences."""

    try:
        response = analyzer._send_request([
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ]
            }
        ], timeout=120)
        
        print(f"✅ Vision анализ: {response[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Ошибка Vision: {e}")
        return False


async def test_onboarding_action_format():
    """Тест 4: Формат действий для онбординга"""
    print("\n" + "=" * 60)
    print("🧪 Тест 4: Формат OnboardingAction")
    print("=" * 60)
    
    analyzer = get_analyzer()
    
    if not analyzer.is_available():
        print("⚠️ Пропуск - LM Studio недоступен")
        return False
    
    prompt = """You are a browser automation assistant completing Airtable onboarding.

Current page: Airtable asking for workspace name with a text field and "Continue" button.

Available actions:
- click: Click on a button or link
- fill: Fill a text field with a value
- done: Onboarding is complete

Respond with JSON only:
{"action": "click|fill|done", "element": "element description or null", "value": "value for fill or null", "confidence": 0.9}"""

    try:
        response = analyzer._send_request([
            {"role": "user", "content": prompt}
        ], timeout=30)
        
        print(f"✅ Ответ LLM: {response}")
        
        # Пробуем распарсить
        import json
        import re
        json_match = re.search(r'\{[^{}]*\}', response)
        if json_match:
            data = json.loads(json_match.group())
            print(f"   ✅ Распарсено: action={data.get('action')}, element={data.get('element')}")
            return True
        else:
            print(f"   ⚠️ JSON не найден в ответе")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def test_vision_onboarding_agent_init():
    """Тест 5: Инициализация VisionOnboardingAgent"""
    print("\n" + "=" * 60)
    print("🧪 Тест 5: VisionOnboardingAgent инициализация")
    print("=" * 60)
    
    try:
        agent = VisionOnboardingAgent(
            max_steps=20,
            timeout_seconds=300,
            workspace_name="Test Workspace",
            user_name="Test User",
        )
        
        print("✅ VisionOnboardingAgent создан!")
        print(f"   max_steps: {agent.max_steps}")
        print(f"   timeout: {agent.timeout_seconds}s")
        print(f"   workspace: {agent.workspace_name}")
        print(f"   user: {agent.user_name}")
        
        # Проверяем доступность LLM через агента
        analyzer = agent._get_analyzer()
        if analyzer.is_available():
            print("   ✅ LLM доступен через агента")
        else:
            print("   ⚠️ LLM недоступен")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def main():
    """Запуск всех тестов"""
    print("\n" + "🚀" * 20)
    print("   ТЕСТ ИНТЕГРАЦИИ VISION ONBOARDING")
    print("🚀" * 20)
    
    results = {
        "LLM Connection": await test_llm_connection(),
        "Text Analysis": await test_text_analysis(),
        "Vision Analysis": await test_vision_analysis_file(),
        "Action Format": await test_onboarding_action_format(),
        "Agent Init": await test_vision_onboarding_agent_init(),
    }
    
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ТЕСТОВ")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"   Прошло: {passed}/{len(results)}")
    
    if failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("   Система готова к использованию.")
    else:
        print(f"\n⚠️ {failed} тестов не прошли.")
        print("   Проверьте что LM Studio запущен и модель загружена.")
    
    return failed == 0


if __name__ == "__main__":
    asyncio.run(main())
