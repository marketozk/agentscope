"""
🤖 Автоматическое применение промпта самообучения к test_agent3_air.py
Отправляет промпт + код в GPT-5 Pro и сохраняет ответ
"""
import os
import json
import requests
from pathlib import Path
from datetime import datetime

# API ключ OpenAI
API_KEY = os.environ.get("OPENAI_API_KEY", "your-api-key-here")

def find_latest_prompt():
    """Находит последний созданный промпт"""
    current_dir = Path(__file__).parent
    prompt_files = list(current_dir.glob("optimized_prompt_self_learning_*.txt"))
    
    if not prompt_files:
        raise FileNotFoundError("Не найден файл с оптимизированным промптом")
    
    # Сортируем по времени создания (самый новый)
    latest = max(prompt_files, key=lambda p: p.stat().st_mtime)
    return latest


def read_prompt_file(prompt_path: Path) -> str:
    """Читает промпт из файла"""
    with open(prompt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Извлекаем только сам промпт (без заголовков и инструкций)
    # Ищем первую строку после заголовков
    lines = content.split('\n')
    start_idx = 0
    
    for i, line in enumerate(lines):
        if line.strip().startswith('Ты — эксперт') or line.strip().startswith('Задача:'):
            start_idx = i
            break
    
    # Ищем конец промпта (перед секцией "КАК ИСПОЛЬЗОВАТЬ")
    end_idx = len(lines)
    for i, line in enumerate(lines):
        if 'КАК ИСПОЛЬЗОВАТЬ' in line or '=' * 40 in line and i > start_idx + 10:
            end_idx = i
            break
    
    prompt = '\n'.join(lines[start_idx:end_idx]).strip()
    return prompt


def read_code_file(code_path: Path) -> str:
    """Читает код test_agent3_air.py"""
    with open(code_path, 'r', encoding='utf-8') as f:
        return f.read()


def compress_code(code: str) -> str:
    """Сжимает код: убирает пустые строки, лишние пробелы, длинные комментарии"""
    lines = code.split('\n')
    compressed = []
    
    for line in lines:
        # Пропускаем пустые строки
        if not line.strip():
            continue
        
        # Пропускаем длинные блоки комментариев (docstrings более 2 строк)
        if '"""' in line or "'''" in line:
            # Оставляем только короткие docstrings (первая строка)
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                compressed.append(line.split('"""')[0] + '"""..."""' if '"""' in line else line.split("'''")[0] + "'''...'''")
                continue
        
        # Сокращаем длинные комментарии
        if '#' in line:
            code_part = line.split('#')[0]
            comment = line.split('#')[1] if len(line.split('#')) > 1 else ''
            if len(comment) > 50:
                line = code_part + '# ' + comment[:47] + '...'
        
        compressed.append(line)
    
    return '\n'.join(compressed)


def send_to_gpt5_pro(prompt: str, code: str, max_tokens: int = 30000) -> dict:
    """
    Отправляет промпт и код в GPT-5 Pro
    
    Args:
        prompt: Оптимизированный промпт с задачей
        code: Исходный код test_agent3_air.py
        max_tokens: Максимальное количество токенов в ответе
        
    Returns:
        Ответ от GPT-5 Pro
    """
    # gpt-5-pro работает только через v1/responses!
    url = "https://api.openai.com/v1/responses"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Сжимаем код
    print("\n🗜️  Сжатие кода...")
    original_size = len(code)
    compressed_code = compress_code(code)
    compressed_size = len(compressed_code)
    saved = original_size - compressed_size
    print(f"   Исходный размер: {original_size} символов")
    print(f"   Сжатый размер: {compressed_size} символов")
    print(f"   Сэкономлено: {saved} символов ({saved*100//original_size}%)")
    
    # Формируем сообщение
    user_message = f"""{prompt}

---

Код test_agent3_air.py (сжатый):

```python
{compressed_code}
```

---

Предложи систему самообучения.
"""
    
    # Для v1/responses используется параметр 'input' вместо 'messages'
    payload = {
        "model": "gpt-5-pro",
        "input": [
            {
                "role": "user",
                "content": user_message
            }
        ]
    }
    
    print("\n📤 Отправка запроса в GPT-5 Pro...")
    print(f"   Длина промпта: {len(prompt)} символов")
    print(f"   Длина кода (сжатого): {compressed_size} символов")
    print(f"   Общий размер запроса: {len(user_message)} символов")
    print(f"   Максимум токенов ответа: {max_tokens}")
    print("   ⏳ Ожидание ответа (может занять 2-5 минут, таймаут отключен)...")
    
    # Убираем timeout - пусть ждет сколько нужно
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Ошибка API: {response.status_code} - {response.text}")


def save_response(response_data: dict, output_path: Path):
    """Сохраняет ответ GPT-5 в файл"""
    
    # Извлекаем текст ответа (для v1/responses ответ в 'output')
    if 'output' in response_data:
        answer = response_data['output']
        # Если ответ список - объединяем в строку
        if isinstance(answer, list):
            answer = '\n\n'.join(str(item) for item in answer)
    elif 'choices' in response_data and len(response_data['choices']) > 0:
        answer = response_data['choices'][0]['message']['content']
    else:
        answer = json.dumps(response_data, indent=2, ensure_ascii=False)
    
    # Сохраняем в файл
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("🧠 ОТВЕТ GPT-5 PRO: СИСТЕМА САМООБУЧЕНИЯ ДЛЯ test_agent3_air.py\n")
        f.write("=" * 80 + "\n")
        f.write(f"Создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Модель: gpt-5-pro\n")
        f.write("=" * 80 + "\n\n")
        f.write(answer)
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("СТАТИСТИКА:\n")
        f.write("=" * 80 + "\n")
        
        # Добавляем статистику использования
        if 'usage' in response_data:
            usage = response_data['usage']
            f.write(f"Входные токены: {usage.get('prompt_tokens', 'N/A')}\n")
            f.write(f"Выходные токены: {usage.get('completion_tokens', 'N/A')}\n")
            f.write(f"Всего токенов: {usage.get('total_tokens', 'N/A')}\n")
    
    print(f"\n💾 Ответ сохранен в: {output_path}")
    
    # Также сохраняем полный JSON ответ
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(response_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Полный JSON ответ: {json_path}")
    
    return answer


def main():
    """Основная функция"""
    
    print("\n" + "=" * 80)
    print("🤖 АВТОМАТИЧЕСКОЕ ПРИМЕНЕНИЕ САМООБУЧЕНИЯ К test_agent3_air.py")
    print("=" * 80)
    
    # Проверяем API ключ
    if API_KEY == "your-api-key-here" or not API_KEY:
        print("\n❌ ОШИБКА: Не установлен OPENAI_API_KEY")
        print("\nУстанови API ключ:")
        print("   Windows (PowerShell): $env:OPENAI_API_KEY='sk-...'")
        return
    
    print(f"\n✅ API ключ найден: {API_KEY[:10]}...{API_KEY[-4:]}")
    
    try:
        # Шаг 1: Находим последний промпт
        print("\n📝 Шаг 1: Поиск оптимизированного промпта...")
        prompt_path = find_latest_prompt()
        print(f"   ✅ Найден: {prompt_path.name}")
        
        # Шаг 2: Читаем промпт
        print("\n📖 Шаг 2: Чтение промпта...")
        prompt = read_prompt_file(prompt_path)
        print(f"   ✅ Промпт загружен ({len(prompt)} символов)")
        
        # Шаг 3: Читаем код
        print("\n📖 Шаг 3: Чтение test_agent3_air.py...")
        code_path = Path(__file__).parent / "test_agent3_air.py"
        
        if not code_path.exists():
            raise FileNotFoundError(f"Файл не найден: {code_path}")
        
        code = read_code_file(code_path)
        print(f"   ✅ Код загружен ({len(code)} символов, ~{len(code.split(chr(10)))} строк)")
        
        # Шаг 4: Отправляем в GPT-5 Pro
        print("\n🚀 Шаг 4: Отправка в GPT-5 Pro...")
        print("   ⏳ Это может занять 1-3 минуты...")
        
        # max_tokens=30000 - ждем ответ минимум минуту (rate limit)
        response = send_to_gpt5_pro(prompt, code, max_tokens=30000)
        
        print("\n   ✅ Ответ получен!")
        
        # Шаг 5: Сохраняем ответ
        print("\n💾 Шаг 5: Сохранение ответа...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(__file__).parent / f"gpt5_self_learning_solution_{timestamp}.txt"
        
        answer = save_response(response, output_path)
        
        # Финальный отчет
        print("\n" + "=" * 80)
        print("✅ ГОТОВО!")
        print("=" * 80)
        print(f"\n📄 Файл с решением: {output_path}")
        print(f"📄 JSON ответ: {output_path.with_suffix('.json')}")
        
        print("\n📊 Статистика:")
        if 'usage' in response:
            usage = response['usage']
            print(f"   Входные токены: {usage.get('prompt_tokens', 'N/A')}")
            print(f"   Выходные токены: {usage.get('completion_tokens', 'N/A')}")
            print(f"   Всего токенов: {usage.get('total_tokens', 'N/A')}")
        
        print("\n📋 ЧТО ДЕЛАТЬ ДАЛЬШЕ:")
        print(f"   1. Открой файл: {output_path.name}")
        print("   2. Изучи предложенную архитектуру самообучения")
        print("   3. Следуй инструкциям по интеграции в test_agent3_air.py")
        print("   4. Протестируй на 5-10 регистрациях")
        print("   5. Наблюдай как агент учится и улучшается!")
        
        # Превью ответа
        print("\n" + "=" * 80)
        print("📄 ПРЕВЬЮ ОТВЕТА GPT-5 PRO (первые 50 строк):")
        print("=" * 80)
        preview_lines = answer.split('\n')[:50]
        print('\n'.join(preview_lines))
        if len(answer.split('\n')) > 50:
            print("\n... (остальное в файле) ...")
        print("=" * 80)
        
    except FileNotFoundError as e:
        print(f"\n❌ Ошибка: {e}")
        print("\nУбедись что:")
        print("   1. Запущен create_self_learning_prompt.py")
        print("   2. Создан файл optimized_prompt_self_learning_*.txt")
        print("   3. Существует файл test_agent3_air.py в той же папке")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
