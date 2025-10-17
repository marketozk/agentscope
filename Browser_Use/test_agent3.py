"""
РАБОТАЕТ!!!!!!!
🎯 Тест gemini-2.5-computer-use-preview-10-2025 через новый SDK google.genai
БЕЗ использования browser-use Agent - только прямое API и Playwright.

Что делает:
1. Запускает Playwright браузер
2. Использует Computer Use модель через google.genai.Client
3. Модель видит скриншоты и управляет браузером через tool_calls
4. Цикл: скриншот → модель → tool_call → выполнение → результат → новый скриншот
"""
import os
import json
import asyncio
import base64
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Новый SDK Google Generative AI (unified SDK)
from google import genai
from google.genai.types import (
    Tool, ComputerUse, 
    GenerateContentConfig,
    Content, Part, Blob,
    FunctionCall, FunctionResponse
)

# Playwright для управления браузером
from playwright.async_api import async_playwright


# ==================== ОБРАБОТЧИК TOOL CALLS ====================

async def execute_computer_use_action(page, function_call: FunctionCall, screen_width: int, screen_height: int) -> dict:
    """
    Выполняет действие Computer Use в браузере Playwright.
    
    Полная реализация всех действий из официальной документации:
    https://ai.google.dev/gemini-api/docs/computer-use
    
    Args:
        page: Playwright Page объект
        function_call: FunctionCall от модели
        screen_width: Ширина экрана в пикселях
        screen_height: Высота экрана в пикселях
    
    Returns:
        dict с результатом выполнения
    """
    action = function_call.name
    args = dict(function_call.args) if function_call.args else {}
    
    print(f"  🔧 Действие: {action}")
    print(f"     Аргументы: {json.dumps(args, indent=2, ensure_ascii=False)}")
    
    # Проверка safety_decision
    if 'safety_decision' in args:
        safety = args['safety_decision']
        if safety.get('decision') == 'require_confirmation':
            print(f"  ⚠️  Safety Warning: {safety.get('explanation', 'N/A')}")
            # В реальном приложении здесь нужен запрос подтверждения у пользователя
            # Для теста просто продолжаем (auto-approve)
            # ВАЖНО: Обязательно включить safety_acknowledgement И url
            return {
                "success": True, 
                "message": "Safety confirmation (auto-approved for testing)", 
                "safety_acknowledgement": "true",
                "url": page.url  # ОБЯЗАТЕЛЬНО для Computer Use!
            }
    
    try:
        # ==================== НАВИГАЦИЯ ====================
        
        if action == "open_web_browser":
            # Браузер уже открыт
            return {"success": True, "message": "Браузер уже открыт", "url": page.url}
        
        elif action == "navigate":
            url = args.get("url", "")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            return {"success": True, "message": f"Перешел на {url}", "url": page.url}
        
        elif action == "search":
            # Переход на главную страницу Google
            await page.goto("https://www.google.com", wait_until="networkidle", timeout=30000)
            return {"success": True, "message": "Открыл Google Search", "url": page.url}
        
        elif action == "go_back":
            await page.go_back(wait_until="networkidle")
            return {"success": True, "message": "Вернулся назад", "url": page.url}
        
        elif action == "go_forward":
            await page.go_forward(wait_until="networkidle")
            return {"success": True, "message": "Перешел вперед", "url": page.url}
        
        # ==================== КЛИКИ И НАВЕДЕНИЕ ====================
        
        elif action == "click_at":
            # Денормализация координат (0-999 → реальные пиксели)
            x = args.get("x", 0)
            y = args.get("y", 0)
            actual_x = int(x / 1000 * screen_width)
            actual_y = int(y / 1000 * screen_height)
            
            await page.mouse.click(actual_x, actual_y)
            await page.wait_for_load_state("networkidle", timeout=5000)
            
            return {"success": True, "message": f"Клик по ({x}, {y}) → ({actual_x}, {actual_y})px", "url": page.url}
        
        elif action == "hover_at":
            x = args.get("x", 0)
            y = args.get("y", 0)
            actual_x = int(x / 1000 * screen_width)
            actual_y = int(y / 1000 * screen_height)
            
            await page.mouse.move(actual_x, actual_y)
            await asyncio.sleep(0.5)  # Небольшая пауза для появления меню
            
            return {"success": True, "message": f"Навел курсор на ({x}, {y}) → ({actual_x}, {actual_y})px"}
        
        # ==================== ВВОД ТЕКСТА ====================
        
        elif action == "type_text_at":
            x = args.get("x", 0)
            y = args.get("y", 0)
            text = args.get("text", "")
            press_enter = args.get("press_enter", True)
            clear_before = args.get("clear_before_typing", True)
            
            actual_x = int(x / 1000 * screen_width)
            actual_y = int(y / 1000 * screen_height)
            
            # Клик по полю
            await page.mouse.click(actual_x, actual_y)
            await asyncio.sleep(0.3)
            
            # Очистка поля (если нужно)
            if clear_before:
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
            
            # Ввод текста
            await page.keyboard.type(text, delay=50)  # delay для естественности
            
            # Enter (если нужно)
            if press_enter:
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("networkidle", timeout=5000)
            
            return {"success": True, "message": f"Ввел текст '{text[:50]}...' at ({x}, {y})", "url": page.url}
        
        # ==================== КЛАВИАТУРНЫЕ ДЕЙСТВИЯ ====================
        
        elif action == "key_combination":
            keys = args.get("keys", "")
            await page.keyboard.press(keys)
            await asyncio.sleep(0.5)
            
            return {"success": True, "message": f"Нажал клавиши: {keys}"}
        
        # ==================== СКРОЛЛИНГ ====================
        
        elif action == "scroll_document":
            direction = args.get("direction", "down")
            scroll_amount = 500
            
            if direction == "down":
                await page.mouse.wheel(0, scroll_amount)
            elif direction == "up":
                await page.mouse.wheel(0, -scroll_amount)
            elif direction == "right":
                await page.mouse.wheel(scroll_amount, 0)
            elif direction == "left":
                await page.mouse.wheel(-scroll_amount, 0)
            
            await asyncio.sleep(0.5)
            return {"success": True, "message": f"Прокрутил страницу {direction}"}
        
        elif action == "scroll_at":
            x = args.get("x", 0)
            y = args.get("y", 0)
            direction = args.get("direction", "down")
            magnitude = args.get("magnitude", 800)
            
            actual_x = int(x / 1000 * screen_width)
            actual_y = int(y / 1000 * screen_height)
            actual_magnitude = int(magnitude / 1000 * screen_height)
            
            # Навести курсор на элемент
            await page.mouse.move(actual_x, actual_y)
            
            # Прокрутить
            if direction == "down":
                await page.mouse.wheel(0, actual_magnitude)
            elif direction == "up":
                await page.mouse.wheel(0, -actual_magnitude)
            elif direction == "right":
                await page.mouse.wheel(actual_magnitude, 0)
            elif direction == "left":
                await page.mouse.wheel(-actual_magnitude, 0)
            
            await asyncio.sleep(0.5)
            return {"success": True, "message": f"Прокрутил элемент at ({x}, {y}) {direction} на {magnitude}"}
        
        # ==================== DRAG & DROP ====================
        
        elif action == "drag_and_drop":
            x = args.get("x", 0)
            y = args.get("y", 0)
            dest_x = args.get("destination_x", 0)
            dest_y = args.get("destination_y", 0)
            
            start_x = int(x / 1000 * screen_width)
            start_y = int(y / 1000 * screen_height)
            end_x = int(dest_x / 1000 * screen_width)
            end_y = int(dest_y / 1000 * screen_height)
            
            # Перетаскивание
            await page.mouse.move(start_x, start_y)
            await page.mouse.down()
            await asyncio.sleep(0.2)
            await page.mouse.move(end_x, end_y, steps=10)
            await asyncio.sleep(0.2)
            await page.mouse.up()
            
            return {"success": True, "message": f"Перетащил из ({x}, {y}) в ({dest_x}, {dest_y})"}
        
        # ==================== ОЖИДАНИЕ ====================
        
        elif action == "wait_5_seconds":
            await asyncio.sleep(5)
            return {"success": True, "message": "Ждал 5 секунд"}
        
        # ==================== НЕИЗВЕСТНОЕ ДЕЙСТВИЕ ====================
        
        else:
            return {"success": False, "message": f"Неизвестное действие: {action}"}
    
    except Exception as e:
        error_msg = f"Ошибка выполнения {action}: {str(e)}"
        print(f"  ❌ {error_msg}")
        return {"success": False, "message": error_msg, "url": page.url}


# ==================== ОСНОВНОЙ ЦИКЛ АГЕНТА ====================

async def run_computer_use_agent(task: str, max_steps: int = 20):
    """
    Запускает агента с Computer Use моделью.
    
    Args:
        task: Задача для агента (текстовый промпт)
        max_steps: Максимальное количество шагов
    """
    # Загружаем API ключ
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("❌ GOOGLE_API_KEY не найден в .env файле")
    
    print("=" * 70)
    print("🚀 Запуск Computer Use агента")
    print("=" * 70)
    print(f"📋 Задача: {task}")
    print(f"⚙️  Модель: gemini-2.5-computer-use-preview-10-2025")
    print(f"🔄 Максимум шагов: {max_steps}")
    print("=" * 70)
    
    # Инициализируем клиент Google Generative AI
    client = genai.Client(api_key=api_key)
    model_name = "gemini-2.5-computer-use-preview-10-2025"
    
    # Конфигурация с Computer Use tool
    config = GenerateContentConfig(
        tools=[
            Tool(
                computer_use=ComputerUse(
                    environment=genai.types.Environment.ENVIRONMENT_BROWSER
                )
            )
        ],
        temperature=0.3,
        max_output_tokens=4096,
    )
    
    # Размеры экрана (рекомендуется 1440x900 по документации)
    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 900
    
    # Запускаем браузер Playwright
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,  # Видим что происходит
        args=['--start-maximized']
    )
    context = await browser.new_context(
        viewport={'width': SCREEN_WIDTH, 'height': SCREEN_HEIGHT},
        locale='ru-RU',
        timezone_id='Europe/Moscow'
    )
    page = await context.new_page()
    
    # Начальная страница
    await page.goto("about:blank")
    
    # История диалога
    history = []
    
    # Первый промпт с задачей
    initial_prompt = f"""
Ты - автономный агент для управления браузером. Твоя задача:

{task}

У тебя есть доступ к Computer Use tool для взаимодействия с браузером.
Доступные действия: navigate, click, type, scroll, press_key, wait, get_text.

Планируй свои действия, выполняй их последовательно и сообщай о результате.
Когда задача выполнена, опиши итог и завершай работу.
"""
    
    print(f"\n💬 Начальный промпт отправлен...")
    
    try:
        step = 0
        
        # Первый запрос: задача + начальный скриншот
        screenshot_bytes = await page.screenshot(type="png", full_page=False)
        history = [
            Content(
                role="user",
                parts=[
                    Part.from_text(text=initial_prompt),
                    Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes))
                ]
            )
        ]
        
        while step < max_steps:
            step += 1
            print(f"\n{'=' * 70}")
            print(f"🔄 ШАГ {step}/{max_steps}")
            print(f"{'=' * 70}")
            
            # Запрос к модели с текущей историей
            print("🧠 Модель анализирует...")
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=history,
                config=config
            )
            
            # Обрабатываем ответ
            if not response.candidates or not response.candidates[0].content.parts:
                print("⚠️  Модель не вернула ответ")
                break
            
            # Получаем ответ модели
            model_content = response.candidates[0].content
            
            # Проверяем все parts в ответе
            has_tool_calls = False
            has_text = False
            tool_responses = []
            
            for part in model_content.parts:
                # Текстовый вывод от модели
                if hasattr(part, 'text') and part.text:
                    has_text = True
                    print(f"\n💭 Мысль модели:")
                    print(f"   {part.text[:500]}...")
                
                # Tool call (действие)
                if hasattr(part, 'function_call') and part.function_call:
                    has_tool_calls = True
                    
                    # Выполняем действие с передачей размеров экрана
                    result = await execute_computer_use_action(
                        page, 
                        part.function_call,
                        SCREEN_WIDTH,
                        SCREEN_HEIGHT
                    )
                    
                    print(f"  ✅ Результат: {result.get('message', result)}")
                    
                    # Сохраняем результат для добавления в историю
                    tool_responses.append(
                        Part.from_function_response(
                            name=part.function_call.name,
                            response=result
                        )
                    )
                    
                    # Небольшая пауза между действиями
                    await asyncio.sleep(1)
            
            # Добавляем в историю ответ модели
            history.append(model_content)
            
            # Если были tool_calls, добавляем их результаты + новый скриншот
            if tool_responses:
                # ВАЖНО: После выполнения действий делаем новый скриншот
                screenshot_bytes = await page.screenshot(type="png", full_page=False)
                
                # Добавляем function_response + скриншот в один user turn
                history.append(
                    Content(
                        role="user",
                        parts=tool_responses + [
                            Part(inline_data=Blob(mime_type="image/png", data=screenshot_bytes))
                        ]
                    )
                )
            
            # Если есть текст но нет tool_calls - задача завершена
            if has_text and not has_tool_calls:
                print("\n" + "=" * 70)
                print("✅ ЗАДАЧА ЗАВЕРШЕНА")
                print("=" * 70)
                print(f"\n📄 Финальный ответ модели:")
                for part in model_content.parts:
                    if hasattr(part, 'text') and part.text:
                        print(part.text)
                break
            
            # Если нет ни текста, ни tool_calls
            if not has_text and not has_tool_calls:
                print("\n⚠️  Модель не вернула ни текста, ни действий")
                break
        
        else:
            print(f"\n⏱️  Достигнут лимит шагов ({max_steps})")
        
        # Сохраняем финальный скриншот
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = Path("logs") / f"computer_use_final_{timestamp}.png"
        screenshot_path.parent.mkdir(exist_ok=True)
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"\n📸 Финальный скриншот: {screenshot_path}")
        
        # Держим браузер открытым для проверки
        print("\n💤 Браузер остается открытым. Нажмите Ctrl+C для завершения...")
        await asyncio.sleep(3600)  # 1 час
    
    except KeyboardInterrupt:
        print("\n\n👋 Остановлено пользователем")
    
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Закрываем браузер...")
        await browser.close()
        await playwright.stop()
        print("✅ Готово")


# ==================== ЗАПУСК ====================

async def main():
    """Главная функция"""
    
    # Задача для агента
    task = """
Открой сайт yandex.ru и найди информацию о курсе доллара к рублю.
Когда найдешь курс, сообщи мне текущее значение.
"""
    
    await run_computer_use_agent(task, max_steps=15)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Завершено")
    except RuntimeError as e:
        # Игнорируем "Event loop is closed" в Windows
        if "Event loop is closed" not in str(e):
            raise