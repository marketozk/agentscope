"""
🤖 WhatsApp Screenshot Analyzer
Анализирует скриншот WhatsApp и предлагает план действий для написания сообщения в чат

Использует: Gemini 2.5 Computer Use модель для анализа UI и планирования действий
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

try:
    from google import genai as genai_new
    from google.genai import types as genai_types
except ImportError:
    print("❌ Ошибка: необходимо установить google-genai>=0.3.0")
    print("   pip install google-genai>=0.3.0")
    exit(1)


class WhatsAppAnalyzer:
    """Анализатор скриншотов WhatsApp с помощью Gemini Computer Use"""
    
    def __init__(self, api_key: str = None):
        """
        Инициализация анализатора
        
        Args:
            api_key: Google API ключ (если None, загружается из .env)
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
            raise ValueError("❌ GOOGLE_API_KEY не найден в .env файле")
        
        self.client = genai_new.Client(api_key=self.api_key)
        self.model_name = "models/gemini-2.5-computer-use-preview-10-2025"
        
        # Директории
        self.base_dir = Path(__file__).parent
        self.logs_dir = self.base_dir / "logs"
        self.results_dir = self.base_dir / "results"
        
        # Создаём директории
        self.logs_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        
        print("✅ WhatsApp Analyzer инициализирован")
        print(f"   📦 Модель: {self.model_name}")
        print(f"   📂 Логи: {self.logs_dir}")
        print(f"   📊 Результаты: {self.results_dir}")
    
    def load_image(self, image_path: str) -> str:
        """
        Загрузить изображение и конвертировать в base64
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            Base64 строка изображения
        """
        path = Path(image_path)
        
        if not path.exists():
            raise FileNotFoundError(f"❌ Файл не найден: {image_path}")
        
        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        print(f"✅ Изображение загружено: {path.name} ({path.stat().st_size / 1024:.1f} KB)")
        return image_data
    
    def build_analysis_prompt(self, target_chat: str) -> str:
        """
        Создать промпт для анализа скриншота WhatsApp
        
        Args:
            target_chat: Имя чата, в который нужно написать
            
        Returns:
            Текст промпта
        """
        prompt = f"""
🤖 ЗАДАЧА: Анализ интерфейса WhatsApp на Android

📱 КОНТЕКСТ:
- Перед тобой скриншот приложения WhatsApp на телефоне Android
- Разрешение экрана стандартное для мобильного устройства
- Интерфейс на русском языке

🎯 ЦЕЛЬ:
Написать сообщение в чат с именем: "{target_chat}"

📋 ЧТО НУЖНО СДЕЛАТЬ:

1. **АНАЛИЗ ТЕКУЩЕГО СОСТОЯНИЯ**
   - Определи, на каком экране мы находимся (список чатов, открытый чат, другое)
   - Виден ли чат "{target_chat}" на экране?
   - Если чат открыт - где находится поле ввода сообщения?
   - Есть ли поиск чатов? Где он находится?

2. **ОПРЕДЕЛЕНИЕ КООРДИНАТ**
   - Укажи примерные координаты (X, Y) для каждого важного элемента
   - Координаты в процентах от размера экрана (0-100%)
   - Например: "Поле поиска: X=50%, Y=15%"

3. **ПЛАН ДЕЙСТВИЙ**
   Составь пошаговый план действий для достижения цели:
   
   Шаг 1: [Действие]
      - Тип действия: click / type / scroll / etc.
      - Координаты: X=..%, Y=..%
      - Описание: что произойдет
   
   Шаг 2: [Действие]
      ...
   
   И так далее до достижения цели

4. **АЛЬТЕРНАТИВНЫЕ ВАРИАНТЫ**
   - Если есть несколько способов достичь цели - опиши их
   - Укажи самый быстрый и самый надежный путь

5. **ВОЗМОЖНЫЕ ПРОБЛЕМЫ**
   - Что может пойти не так?
   - Как проверить, что мы на правильном пути?

📊 ФОРМАТ ОТВЕТА:
Предоставь структурированный анализ с четкими координатами и описанием действий.
Используй эмодзи для наглядности.

🔍 ВАЖНО:
- Будь максимально конкретным с координатами
- Учитывай, что UI может иметь анимации и задержки
- Описывай действия так, чтобы их мог выполнить бот

Начни анализ!
"""
        return prompt.strip()
    
    def analyze_screenshot(
        self, 
        image_path: str, 
        target_chat: str,
        save_log: bool = True
    ) -> Dict[str, Any]:
        """
        Проанализировать скриншот WhatsApp
        
        Args:
            image_path: Путь к скриншоту
            target_chat: Имя чата, в который нужно написать
            save_log: Сохранять ли лог анализа
            
        Returns:
            Словарь с результатами анализа
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"\n{'='*60}")
        print(f"🚀 НАЧАЛО АНАЛИЗА")
        print(f"{'='*60}")
        print(f"📸 Скриншот: {Path(image_path).name}")
        print(f"💬 Целевой чат: {target_chat}")
        print(f"⏰ Время: {timestamp}")
        print(f"{'='*60}\n")
        
        # Загрузка изображения
        try:
            image_b64 = self.load_image(image_path)
        except Exception as e:
            print(f"❌ Ошибка загрузки изображения: {e}")
            return {"error": str(e), "status": "failed"}
        
        # Создание промпта
        prompt = self.build_analysis_prompt(target_chat)
        
        print("📝 Промпт создан")
        print(f"   Длина: {len(prompt)} символов")
        print(f"\n{'─'*60}")
        print("📋 ПРОМПТ:")
        print(f"{'─'*60}")
        print(prompt)
        print(f"{'─'*60}\n")
        
        # Computer Use модель с tool для анализа изображений
        # Конфигурация с Computer Use tool
        config = genai_types.GenerateContentConfig(
            tools=[
                genai_types.Tool(
                    computer_use=genai_types.ComputerUse(
                        environment=genai_types.Environment.ENVIRONMENT_BROWSER
                    )
                )
            ],
            temperature=0.3,
            max_output_tokens=4096,
        )
        
        # Создание запроса с изображением
        parts = [
            genai_types.Part.from_text(text=prompt),
            genai_types.Part.from_bytes(
                data=base64.b64decode(image_b64),
                mime_type="image/jpeg"
            )
        ]
        
        print("\n🧠 Отправка запроса модели...")
        print(f"   Модель: {self.model_name} (Computer Use)")
        
        try:
            # Вызов Computer Use модели
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=parts,
                config=config
            )
            
            # Извлечение ПОЛНОГО ответа
            print("\n" + "="*60)
            print("📥 ПОЛНЫЙ ОТВЕТ МОДЕЛИ")
            print("="*60)
            
            analysis_text = ""
            
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                print(f"\n🔍 Candidate finish_reason: {candidate.finish_reason}")
                
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    print(f"📦 Количество parts: {len(candidate.content.parts)}\n")
                    
                    for i, part in enumerate(candidate.content.parts, 1):
                        print(f"─── Part {i} ───")
                        
                        # Текстовая часть
                        if hasattr(part, 'text') and part.text:
                            print(f"📝 Text:")
                            print(part.text)
                            analysis_text += part.text + "\n"
                        
                        # Function call (tool call)
                        if hasattr(part, 'function_call') and part.function_call:
                            print(f"🔧 Function Call:")
                            if hasattr(part.function_call, 'name'):
                                print(f"   Name: {part.function_call.name}")
                                analysis_text += f"\n[Function Call: {part.function_call.name}]\n"
                            if hasattr(part.function_call, 'args'):
                                print(f"   Args: {dict(part.function_call.args)}")
                                analysis_text += f"Args: {dict(part.function_call.args)}\n"
                            else:
                                print(f"   Function Call: {part.function_call}")
                                analysis_text += f"\n[Function Call: {part.function_call}]\n"
                        
                        # Thought signature - не выводим (бинарные данные)
                        # if hasattr(part, 'thought_signature'):
                        #     print(f"💭 Thought Signature: [{len(part.thought_signature)} bytes]")
                        
                        # Executable code
                        if hasattr(part, 'executable_code'):
                            print(f"💻 Executable Code:")
                            print(part.executable_code)
                            analysis_text += f"\n[Executable Code]\n{part.executable_code}\n"
                        
                        # Code execution result
                        if hasattr(part, 'code_execution_result'):
                            print(f"✅ Code Execution Result:")
                            print(part.code_execution_result)
                            analysis_text += f"\n[Code Result]\n{part.code_execution_result}\n"
                        
                        print()
            
            # Используем собранный текст из parts
            # response.text может содержать warning'и от API, поэтому не выводим его
            if not analysis_text and hasattr(response, 'text'):
                analysis_text = response.text

            usage = getattr(response, "usage_metadata", None)
            if usage:
                print("\n📊 Usage (tokens):")
                prompt_tokens = getattr(usage, "prompt_token_count", None)
                completion_tokens = getattr(usage, "candidates_token_count", None)
                total_tokens = getattr(usage, "total_token_count", None)
                image_tokens = getattr(usage, "image_token_count", None)

                if prompt_tokens is not None:
                    print(f"   Prompt tokens: {prompt_tokens}")
                if completion_tokens is not None:
                    print(f"   Completion tokens: {completion_tokens}")
                if image_tokens is not None:
                    print(f"   Image tokens: {image_tokens}")
                if total_tokens is not None:
                    print(f"   Total tokens: {total_tokens}")

                result_usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "image_tokens": image_tokens,
                }
            else:
                result_usage = None

            print("="*60)
            
            if not analysis_text:
                analysis_text = str(response)
            
            print(f"\n✅ Анализ получен!")
            print(f"   Длина ответа: {len(analysis_text)} символов")
            
            # Формирование результата
            result = {
                "status": "success",
                "timestamp": timestamp,
                "image_path": str(Path(image_path).absolute()),
                "target_chat": target_chat,
                "model": self.model_name,
                "analysis": analysis_text,
                "prompt": prompt,
                "usage": result_usage
            }
            
            # Сохранение результата
            if save_log:
                self.save_result(result, timestamp)
            
            # Вывод анализа
            print(f"\n{'='*60}")
            print("📊 РЕЗУЛЬТАТ АНАЛИЗА")
            print(f"{'='*60}\n")
            print(analysis_text)
            print(f"\n{'='*60}\n")
            
            return result
            
        except Exception as e:
            print(f"\n❌ Ошибка при анализе: {e}")
            error_result = {
                "status": "error",
                "timestamp": timestamp,
                "error": str(e),
                "image_path": str(Path(image_path).absolute()),
                "target_chat": target_chat
            }
            
            if save_log:
                self.save_result(error_result, timestamp)
            
            return error_result
    
    def save_result(self, result: Dict[str, Any], timestamp: str):
        """
        Сохранить результат анализа в JSON файл
        
        Args:
            result: Результаты анализа
            timestamp: Временная метка
        """
        # Сохранение полного результата
        result_file = self.results_dir / f"analysis_{timestamp}.json"
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Результат сохранен: {result_file.name}")
        
        # Сохранение только текста анализа (для удобства чтения)
        if result.get("status") == "success":
            text_file = self.results_dir / f"analysis_{timestamp}.txt"
            
            with open(text_file, "w", encoding="utf-8") as f:
                f.write(f"WhatsApp Screenshot Analysis\n")
                f.write(f"{'='*60}\n\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Target Chat: {result['target_chat']}\n")
                f.write(f"Model: {result['model']}\n")
                f.write(f"\n{'='*60}\n\n")
                f.write(result['analysis'])
            
            print(f"📄 Текстовая версия: {text_file.name}")


def main():
    """Основная функция"""
    
    print("\n" + "="*60)
    print("🤖 WhatsApp Screenshot Analyzer")
    print("   Powered by Gemini 2.5 Computer Use")
    print("="*60 + "\n")
    
    # Инициализация анализатора
    try:
        analyzer = WhatsAppAnalyzer()
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        return
    
    # Параметры анализа
    # ВАЖНО: Положите ваш скриншот в папку screenshots/
    screenshot_path = "screenshots/whatsapp_main.jpg"  # Измените на имя вашего файла
    target_chat = "Т В"  # Имя чата из вашего скриншота
    
    # Проверка наличия файла
    full_path = Path(__file__).parent / screenshot_path
    
    if not full_path.exists():
        print(f"❌ Скриншот не найден: {full_path}")
        print(f"\n💡 Инструкция:")
        print(f"   1. Положите скриншот WhatsApp в папку: {full_path.parent}")
        print(f"   2. Переименуйте файл в: {Path(screenshot_path).name}")
        print(f"   3. Или измените переменную screenshot_path в коде")
        return
    
    # Запуск анализа
    result = analyzer.analyze_screenshot(
        image_path=str(full_path),
        target_chat=target_chat,
        save_log=True
    )
    
    # Итог
    if result.get("status") == "success":
        print("✅ Анализ завершен успешно!")
        print(f"📊 Результаты сохранены в: {analyzer.results_dir}")
    else:
        print("❌ Анализ завершился с ошибкой")
        if "error" in result:
            print(f"   Ошибка: {result['error']}")


if __name__ == "__main__":
    main()
