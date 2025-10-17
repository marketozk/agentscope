"""
🎯 БЫСТРЫЙ FIX: Переход с computer-use на gemini-2.0-flash-exp

Файл для правки: Browser_Use/config.py
"""

# ❌ БЫЛО (НЕ РАБОТАЕТ):
def get_llm():
    model = "gemini-2.5-computer-use-preview-10-2025"
    
    computer_use_config = {
        "tools": [{
            "computer_use": {
                "environment": "ENVIRONMENT_BROWSER"
            }
        }]
    }
    
    llm = ChatGoogle(
        model=model,
        api_key=os.getenv("GOOGLE_API_KEY"),
        config=computer_use_config,
        supports_structured_output=False,  # Не помогает!
    )
    return llm


# ✅ ДОЛЖНО БЫТЬ (РАБОТАЕТ):
def get_llm():
    model = "gemini-2.0-flash-exp"  # Обычная модель с JSON mode
    
    llm = ChatGoogle(
        model=model,
        api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.7,
        # Никакого config с computer_use не нужно!
    )
    return llm


# 🔥 ЕЩЁ ЛУЧШЕ - С RATE LIMITING:
def get_llm():
    config = get_app_config()
    
    if "computer-use" in config.model_name.lower():
        # Автоматически заменяем на совместимую модель
        print("⚠️ Computer-use модель несовместима с browser-use")
        print("✅ Автоматически используем gemini-2.0-flash-exp")
        model = "gemini-2.0-flash-exp"
    else:
        model = config.model_name
    
    llm = ChatGoogle(
        model=model,
        api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.7,
    )
    
    # Оборачиваем в rate limiter
    return RateLimitedLLM(llm)
