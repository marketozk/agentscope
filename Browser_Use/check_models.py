from browser_use import llm as bu_llm
import inspect

print("Доступные модели в browser_use.llm:\n")

for attr in dir(bu_llm):
    if not attr.startswith('_') and 'gemini' in attr.lower():
        print(f"  - {attr}")

print("\n" + "="*60)
print("Проверка модуля google:\n")

if hasattr(bu_llm, 'google'):
    google_module = bu_llm.google
    print("Атрибуты в llm.google:")
    for attr in sorted(dir(google_module)):
        if not attr.startswith('_'):
            print(f"  - {attr}")
    
    # Проверяем наличие нужных моделей
    print("\n" + "="*60)
    print("Проверка конкретных моделей:\n")
    
    if hasattr(google_module, 'gemini_1_5_flash'):
        print("✅ llm.google.gemini_1_5_flash найдена")
        model = getattr(google_module, 'gemini_1_5_flash')
        print(f"   Тип: {type(model)}")
        if hasattr(model, 'model_name'):
            print(f"   Model name: {model.model_name}")
    
    if hasattr(google_module, 'gemini_2_5_flash'):
        print("✅ llm.google.gemini_2_5_flash найдена")
        model = getattr(google_module, 'gemini_2_5_flash')
        print(f"   Тип: {type(model)}")
        if hasattr(model, 'model_name'):
            print(f"   Model name: {model.model_name}")
    
    if hasattr(google_module, 'gemini_15_flash'):
        print("✅ llm.google.gemini_15_flash найдена")
    
    if hasattr(google_module, 'gemini_25_flash'):
        print("✅ llm.google.gemini_25_flash найдена")

