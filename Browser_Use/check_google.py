from browser_use.llm import google

print("Все атрибуты в llm.google:\n")
for attr in sorted(dir(google)):
    if not attr.startswith('_'):
        obj = getattr(google, attr)
        print(f"  {attr}: {type(obj).__name__}")

print("\n" + "="*60)

# Пробуем найти модели
if hasattr(google, 'gemini_15_flash'):
    print("✅ gemini_15_flash найдена")
    print(f"   {google.gemini_15_flash}")

if hasattr(google, 'gemini_1_5_flash'):
    print("✅ gemini_1_5_flash найдена")
    print(f"   {google.gemini_1_5_flash}")
