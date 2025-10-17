"""
Тестовый скрипт для проверки автоматической активации Code Execution Tool
"""

import json
from pathlib import Path

# Симуляция проверки модели
def check_model_requires_code_execution(model_string: str) -> bool:
    """Проверяет, требует ли модель Code Execution Tool"""
    return "computer-use" in model_string.lower()


def test_model_detection():
    """Тест определения моделей"""
    
    print("\n" + "="*70)
    print("🧪 ТЕСТ: Определение моделей требующих Code Execution Tool")
    print("="*70)
    
    # Загружаем конфиг моделей
    config_file = Path(__file__).parent / "models_config.json"
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    models = config_data.get("models", {})
    
    print("\n📋 ПРОВЕРКА ВСЕХ МОДЕЛЕЙ:\n")
    
    for model_name, model_config in models.items():
        model_string = model_config.get("model_string", "")
        enabled = model_config.get("enabled", False)
        requires_tool = check_model_requires_code_execution(model_string)
        
        status = "✅ ВКЛЮЧЕНА" if enabled else "⚪ Выключена"
        tool_status = "🔧 Требует Code Execution Tool" if requires_tool else "✅ Стандартная"
        
        print(f"🤖 {model_name}")
        print(f"   Статус: {status}")
        print(f"   Model String: {model_string}")
        print(f"   Тип: {tool_status}")
        
        if enabled and requires_tool:
            print(f"   ⚠️  ВНИМАНИЕ: Эта модель включена и требует специальной инициализации!")
        
        print()
    
    print("="*70)
    
    # Находим активную модель
    active_models = [
        (name, cfg) for name, cfg in models.items() 
        if cfg.get("enabled", False)
    ]
    
    if active_models:
        model_name, model_config = active_models[0]
        model_string = model_config.get("model_string", "")
        
        print(f"\n✅ АКТИВНАЯ МОДЕЛЬ: {model_name}")
        print(f"   Model String: {model_string}")
        
        if check_model_requires_code_execution(model_string):
            print(f"\n💡 Инициализация с Code Execution Tool:")
            print(f"""
   import google.generativeai as genai
   from google.generativeai.types import Tool
   
   genai.configure(api_key=api_key)
   code_execution_tool = Tool.from_code_execution()
   
   llm = genai.GenerativeModel(
       "{model_string}",
       tools=[code_execution_tool]
   )
            """)
        else:
            print(f"\n✅ Стандартная инициализация:")
            print(f"""
   from browser_use.llm.google import ChatGoogle
   
   llm = ChatGoogle(
       model="{model_string}",
       temperature=0.2,
       api_key=api_key
   )
            """)
    else:
        print("\n⚠️  Ни одна модель не активирована в конфиге!")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    test_model_detection()
