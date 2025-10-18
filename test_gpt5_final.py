"""
ФИНАЛЬНАЯ РАБОЧАЯ ВЕРСИЯ - Тесты всех GPT-5 моделей
"""
import requests
import json
import os

# API ключ (из переменных окружения)
API_KEY = os.environ.get("OPENAI_API_KEY", "your-api-key-here")

def test_gpt5_pro_via_responses_correct():
    """Тестирование GPT-5 Pro через v1/responses с правильным параметром 'input'"""
    print("=" * 60)
    print("ТЕСТ GPT-5 PRO ЧЕРЕЗ V1/RESPONSES (ПРАВИЛЬНЫЙ)")
    print("=" * 60)
    
    url = "https://api.openai.com/v1/responses"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Используем 'input' вместо 'messages' для Responses API
    payload = {
        "model": "gpt-5-pro",
        "input": [
            {
                "role": "user",
                "content": "Привет! Какая ты модель? Расскажи о своих возможностях в 2-3 предложениях."
            }
        ]
    }
    
    try:
        print("\n📤 Отправка запроса к gpt-5-pro...")
        print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}\n")
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Успешный ответ!\n")
            print("📥 ОТВЕТ МОДЕЛИ:")
            print("-" * 60)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("-" * 60)
            
            # Попытка извлечь текст ответа
            if 'output' in data:
                print("\n💬 Текст ответа:")
                print(data['output'])
            
            return True
        else:
            print(f"✗ Ошибка {response.status_code}")
            print(f"Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Исключение: {e}")
        return False

def test_gpt5_chat_latest():
    """Тестирование gpt-5-chat-latest (РАБОТАЕТ!)"""
    print("\n" + "=" * 60)
    print("ТЕСТ GPT-5-CHAT-LATEST ✓")
    print("=" * 60)
    
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-5-chat-latest",
        "messages": [
            {
                "role": "system",
                "content": "Ты полезный AI-ассистент. Отвечай точно и информативно."
            },
            {
                "role": "user",
                "content": "Реши задачу: У Маши было 5 яблок, она отдала 2 Пете. Петя съел половину своих яблок. Сколько яблок осталось у Пети?"
            }
        ],
        "max_completion_tokens": 200,
        "temperature": 0.7
    }
    
    try:
        print("\n📤 Отправка математической задачи...")
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Успешный ответ!\n")
            print("📥 ОТВЕТ МОДЕЛИ:")
            print("-" * 60)
            answer = data['choices'][0]['message']['content']
            print(answer)
            print("-" * 60)
            
            print(f"\n📊 СТАТИСТИКА:")
            print(f"  • Модель: {data.get('model', 'N/A')}")
            print(f"  • Токенов: {data['usage']['total_tokens']}")
            print(f"  • Причина остановки: {data['choices'][0]['finish_reason']}")
            return True
        else:
            print(f"✗ Ошибка {response.status_code}")
            print(f"Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Исключение: {e}")
        return False

def test_gpt5():
    """Тестирование базовой gpt-5 (РАБОТАЕТ!)"""
    print("\n" + "=" * 60)
    print("ТЕСТ GPT-5 (БАЗОВАЯ) ✓")
    print("=" * 60)
    
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-5",
        "messages": [
            {
                "role": "user",
                "content": "Напиши короткий Python код для вычисления факториала числа 5"
            }
        ],
        "max_completion_tokens": 300
    }
    
    try:
        print("\n📤 Запрос на генерацию кода...")
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Успешный ответ!\n")
            print("📥 ОТВЕТ МОДЕЛИ:")
            print("-" * 60)
            answer = data['choices'][0]['message']['content']
            print(answer)
            print("-" * 60)
            
            print(f"\n📊 СТАТИСТИКА:")
            print(f"  • Модель: {data.get('model', 'N/A')}")
            print(f"  • Токенов: {data['usage']['total_tokens']}")
            return True
        else:
            print(f"✗ Ошибка {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Исключение: {e}")
        return False

def test_gpt5_mini():
    """Тестирование gpt-5-mini"""
    print("\n" + "=" * 60)
    print("ТЕСТ GPT-5-MINI")
    print("=" * 60)
    
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-5-mini",
        "messages": [
            {
                "role": "user",
                "content": "Какая столица Франции? Ответь одним словом."
            }
        ],
        "max_completion_tokens": 50
    }
    
    try:
        print("\n📤 Простой вопрос для mini модели...")
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Успешный ответ!\n")
            print(f"📥 Ответ: {data['choices'][0]['message']['content']}")
            print(f"📊 Модель: {data.get('model', 'N/A')}")
            return True
        else:
            print(f"✗ Ошибка {response.status_code}")
            print(f"Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Исключение: {e}")
        return False

def test_o1_pro_correct():
    """Тестирование o1-pro через v1/responses с правильным параметром"""
    print("\n" + "=" * 60)
    print("ТЕСТ O1-PRO ЧЕРЕЗ V1/RESPONSES (ПРАВИЛЬНЫЙ)")
    print("=" * 60)
    
    url = "https://api.openai.com/v1/responses"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "o1-pro",
        "input": [
            {
                "role": "user",
                "content": "Реши логическую задачу: У меня есть 3 коробки. В первой 2 шара, во второй в 3 раза больше, чем в первой. В третьей на 1 меньше, чем во второй. Сколько всего шаров?"
            }
        ]
    }
    
    try:
        print("\n📤 Отправка логической задачи к o1-pro...")
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Успешный ответ!\n")
            print("📥 ОТВЕТ МОДЕЛИ:")
            print("-" * 60)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("-" * 60)
            return True
        else:
            print(f"✗ Ошибка {response.status_code}")
            print(f"Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Исключение: {e}")
        return False

def demo_creative_writing():
    """Демонстрация креативных возможностей GPT-5-chat-latest"""
    print("\n" + "=" * 60)
    print("🎨 ДЕМО: КРЕАТИВНОЕ ПИСЬМО (GPT-5-CHAT-LATEST)")
    print("=" * 60)
    
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-5-chat-latest",
        "messages": [
            {
                "role": "user",
                "content": "Напиши короткое хайку о программировании на Python"
            }
        ],
        "max_completion_tokens": 100,
        "temperature": 0.9  # Высокая креативность
    }
    
    try:
        print("\n📤 Запрос на креативное письмо...")
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Хайку создано!\n")
            print("📝 ХАЙКУ:")
            print("-" * 60)
            print(data['choices'][0]['message']['content'])
            print("-" * 60)
            return True
        else:
            print(f"✗ Ошибка {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Исключение: {e}")
        return False

def main():
    """Основная функция"""
    print("\n" + "🎯" * 30)
    print("  ПОЛНОЕ ТЕСТИРОВАНИЕ GPT-5 МОДЕЛЕЙ")
    print("🎯" * 30)
    
    results = []
    
    # Тесты рабочих моделей
    print("\n" + "✅" * 30)
    print("  ГАРАНТИРОВАННО РАБОЧИЕ МОДЕЛИ")
    print("✅" * 30)
    
    results.append(("GPT-5 (базовая)", test_gpt5()))
    results.append(("GPT-5-chat-latest", test_gpt5_chat_latest()))
    
    # Тесты мини-модели
    results.append(("GPT-5-mini", test_gpt5_mini()))
    
    # Тесты с новым API
    print("\n" + "🔬" * 30)
    print("  ТЕСТИРОВАНИЕ RESPONSES API")
    print("🔬" * 30)
    
    results.append(("GPT-5 Pro (v1/responses)", test_gpt5_pro_via_responses_correct()))
    results.append(("O1-Pro (v1/responses)", test_o1_pro_correct()))
    
    # Креативная демонстрация
    results.append(("Креативное письмо", demo_creative_writing()))
    
    # Итоговая таблица
    print("\n" + "=" * 60)
    print("📊 ИТОГОВАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
    print("=" * 60)
    
    success_count = 0
    for name, success in results:
        status = "✅ РАБОТАЕТ" if success else "❌ НЕ РАБОТАЕТ"
        print(f"{status:15} | {name}")
        if success:
            success_count += 1
    
    print("=" * 60)
    print(f"✅ Успешно: {success_count}/{len(results)}")
    print(f"❌ Неудачно: {len(results) - success_count}/{len(results)}")
    print("=" * 60)
    
    if success_count > 0:
        print("\n🎉 GPT-5 модели доступны и работают!")
        print("\n💡 РЕКОМЕНДАЦИЯ:")
        print("   Используй 'gpt-5-chat-latest' для чат-приложений")
        print("   Используй 'gpt-5' для базовых задач")
        print("   Используй 'gpt-5-mini' для быстрых простых запросов")

if __name__ == "__main__":
    main()
