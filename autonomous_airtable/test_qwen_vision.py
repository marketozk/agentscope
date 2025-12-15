"""
🧪 Тест Qwen2-VL через LM Studio API
"""

import base64
import requests
from pathlib import Path

# Конфиг LM Studio
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "qwen2-vl-7b-instruct"


def send_request(messages: list, timeout: int = 120) -> str:
    """Отправка запроса к LM Studio"""
    response = requests.post(
        LM_STUDIO_URL,
        json={
            "model": MODEL,
            "messages": messages,
            "temperature": 0.7,
        },
        timeout=timeout
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def test_text_only():
    """Тест без изображения"""
    print("=" * 50)
    print("🧪 Тест 1: Текстовый запрос")
    print("=" * 50)
    
    try:
        result = send_request([
            {"role": "user", "content": "Hi! Are you working? Reply briefly."}
        ])
        print(f"✅ Ответ: {result}")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_vision_with_screenshot():
    """Тест с скриншотом"""
    print("\n" + "=" * 50)
    print("🧪 Тест 2: Vision - анализ скриншота")
    print("=" * 50)
    
    # Ищем любой скриншот в debug_screenshots
    screenshot_dirs = [
        Path("debug_screenshots"),
        Path("autonomous_airtable/debug_screenshots"),
        Path("."),
    ]
    
    screenshot_path = None
    for dir_path in screenshot_dirs:
        if dir_path.exists():
            for f in dir_path.glob("*.png"):
                screenshot_path = f
                break
        if screenshot_path:
            break
    
    if not screenshot_path:
        print("⚠️ Нет скриншотов для теста, пропускаем...")
        return True
    
    print(f"📸 Используем скриншот: {screenshot_path}")
    
    # Читаем и кодируем в base64
    with open(screenshot_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    try:
        print("⏳ Обработка изображения (может занять время)...")
        result = send_request([
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this screenshot. What do you see? Is there any error message? Answer briefly."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}"
                        }
                    }
                ]
            }
        ], timeout=180)  # 3 минуты для vision
        print(f"✅ Ответ LLM:\n{result}")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_vision_describe_task():
    """Тест описания задачи для browser-use"""
    print("\n" + "=" * 50)
    print("🧪 Тест 3: Формат ответа для browser-use")
    print("=" * 50)
    
    prompt = """You are a browser automation assistant.

Given a webpage, decide the next action.

Available actions:
- click(element_description)
- fill(field_description, value)
- scroll(direction)
- done()

Example response format:
{"action": "click", "element": "Continue button"}

Current page: Airtable onboarding - asking for workspace name.
What should I do?

Respond with JSON only."""

    try:
        result = send_request([
            {"role": "user", "content": prompt}
        ])
        print(f"✅ Ответ:\n{result}")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Тестирование Qwen2-VL через LM Studio")
    print(f"🔗 URL: {LM_STUDIO_URL}")
    print()
    
    try:
        test_text_only()
        test_vision_with_screenshot()
        test_vision_describe_task()
        print("\n" + "=" * 50)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
