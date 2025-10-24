"""
ФИНАЛЬНАЯ РАБОЧАЯ ВЕРСИЯ - Отправка промпта в GPT-5 Pro
"""
import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из родительской папки
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# API ключ из .env файла
API_KEY = os.environ.get("OPENAI_API_KEY", "your-api-key-here")

print(f"🔑 API ключ загружен: {API_KEY[:10]}...{API_KEY[-10:] if len(API_KEY) > 20 else ''}")

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

def send_prompt_to_gpt5_pro(prompt_text):
    """Отправка промпта в GPT-5 Pro и сохранение результата"""
    print("=" * 60)
    print("ОТПРАВКА В GPT-5 PRO")
    print("=" * 60)
    
    url = "https://api.openai.com/v1/responses"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-5-pro",
        "input": [
            {
                "role": "user",
                "content": prompt_text
            }
        ]
    }
    
    try:
        print("\n📤 Отправка запроса к gpt-5-pro...")
        print(f"📏 Длина промпта: {len(prompt_text)} символов\n")
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Получен успешный ответ!\n")
            
            # Сохраняем полный JSON ответ
            timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"gpt5_pro_response_{timestamp}.json"
            
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Полный ответ сохранен в: {json_filename}")
            
            # Извлекаем и сохраняем текст ответа
            output_text = None
            if 'output' in data and isinstance(data['output'], list):
                # Ищем сообщение ассистента в output
                for item in data['output']:
                    if item.get('type') == 'message' and item.get('role') == 'assistant':
                        content = item.get('content', [])
                        if content and isinstance(content, list):
                            for c in content:
                                if c.get('type') == 'output_text':
                                    output_text = c.get('text', '')
                                    break
                    if output_text:
                        break
            
            if output_text:
                txt_filename = f"gpt5_pro_analysis_{timestamp}.txt"
                
                with open(txt_filename, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                
                print(f"📄 Текст анализа сохранен в: {txt_filename}")
                print("\n" + "=" * 60)
                print("💬 АНАЛИЗ ОТ GPT-5 PRO:")
                print("=" * 60)
                print(output_text[:1000] + "..." if len(output_text) > 1000 else output_text)
                print("=" * 60)
            else:
                print("⚠️ Не удалось извлечь текст из ответа")
            
            return True
        else:
            print(f"✗ Ошибка {response.status_code}")
            print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            return False
            
    except Exception as e:
        print(f"✗ Исключение: {e}")
        return False

def main():
    """Основная функция - отправка промпта в GPT-5 Pro"""
    print("\n" + "🎯" * 30)
    print("  ОТПРАВКА ЗАПРОСА В GPT-5 PRO")
    print("🎯" * 30)
    
    # Читаем промпт из файла
    prompt_file = "0_prompt.txt"
    
    if not os.path.exists(prompt_file):
        print(f"\n❌ ОШИБКА: Файл {prompt_file} не найден!")
        return
    
    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt_text = f.read()
    
    print(f"\n📄 Прочитан промпт из {prompt_file}")
    print(f"📏 Длина промпта: {len(prompt_text)} символов")
    
    # Отправляем запрос
    print("\n" + "🚀" * 30)
    print("  ЗАПУСК АНАЛИЗА")
    print("🚀" * 30)
    
    success = send_prompt_to_gpt5_pro(prompt_text)
    
    if success:
        print("\n✅ Анализ завершен успешно!")
        print("� Результаты сохранены в файл")
    else:
        print("\n❌ Ошибка при выполнении анализа")
        print("💡 Проверьте API ключ в файле .env")

if __name__ == "__main__":
    main()
