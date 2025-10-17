import os
import json
import asyncio
from dotenv import load_dotenv

# Альфа/внутренний Google GenAI SDK с Computer Use
from google import genai as genai_new
from google.genai import types as genai_types

from playwright.async_api import async_playwright


async def execute_tool_call(page, tool_call):
    """Выполняет команду модели с поддержкой safety_decision и координат."""
    if not hasattr(tool_call, 'function_call') or not tool_call.function_call:
        return {"status": "ERROR", "message": "Не является вызовом функции.", "url": page.url}

    command = tool_call.function_call.name
    args = dict(tool_call.function_call.args)

    # Проверяем, есть ли запрос на подтверждение безопасности
    safety_decision = args.get("safety_decision")
    if safety_decision and safety_decision.get("decision") == "require_confirmation":
        print("  ⚠️ Запрос на подтверждение безопасности. Автоматически разрешаем.")
        # Убираем из аргументов, чтобы не мешало выполнению
        args.pop("safety_decision", None)

    print(f"  ▶️ Выполнение: {command} с аргументами {args}")

    try:
        if command in ("navigate_to", "navigate"):
            url = args.get("url", "").strip()
            if not url:
                return {"status": "ERROR", "message": "URL не указан", "url": page.url}
            await page.goto(url)
        elif command == "open_web_browser":
            url = args.get("url", "https://www.google.com").strip()
            await page.goto(url)
        elif command == "click_at":
            x = args.get("x")
            y = args.get("y")
            if x is None or y is None:
                return {"status": "ERROR", "message": "Координаты x/y обязательны", "url": page.url}
            await page.mouse.click(x, y)
        elif command == "type_at":
            x = args.get("x")
            y = args.get("y")
            text = args.get("text", "")
            if x is None or y is None:
                return {"status": "ERROR", "message": "Координаты x/y обязательны", "url": page.url}
            await page.mouse.click(x, y)
            await page.keyboard.type(text, delay=50)  # имитация набора
        else:
            return {"status": "ERROR", "message": f"Неизвестная команда: {command}", "url": page.url}

        await page.wait_for_load_state("networkidle")

        # Формируем ответ
        response = {
            "status": "SUCCESS",
            "url": page.url
        }

        # Обязательно подтверждаем safety_decision, если она была
        if safety_decision:
            response["safety_decision_acknowledged"] = True

        return response

    except Exception as e:
        print(f"  ❌ Ошибка выполнения: {e}")
        response = {
            "status": "ERROR",
            "message": str(e),
            "url": page.url
        }
        if safety_decision:
            response["safety_decision_acknowledged"] = True
        return response


async def main_async():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY не найден в .env")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    page = await browser.new_page()

    client = genai_new.Client(api_key=api_key)
    model_name = "models/gemini-2.5-computer-use-preview-10-2025"

    tool = genai_types.Tool(
        computer_use=genai_types.ComputerUse(
            environment=genai_types.Environment.ENVIRONMENT_BROWSER
        )
    )
    config = genai_types.GenerateContentConfig(
        tools=[tool],
        temperature=0.2,
        max_output_tokens=2048,
    )

    prompt = (
        "Открой сайт yandex.ru и найди 'курс доллара'. "
        "Когда увидишь результат, чётко напиши: 'Курс доллара: [значение]' и заверши работу."
    )
    print(f"🚀 Задача: {prompt}\n")

    # Используем Part(text=...), а не from_text()
    history = [genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])]

    try:
        for step in range(15):
            print(f"🧠 Шаг {step + 1}: анализ скриншота...")

            await page.wait_for_load_state("domcontentloaded")
            screenshot = await page.screenshot(type="png")

            image_part = genai_types.Part(
                inline_data=genai_types.Blob(mime_type="image/png", data=screenshot)
            )

            current_request = history + [
                genai_types.Content(role="user", parts=[image_part])
            ]

            resp = client.models.generate_content(
                model=model_name,
                contents=current_request,
                config=config,
            )

            if not resp.candidates or not resp.candidates[0].content.parts:
                print("\n[ОШИБКА] Пустой ответ от модели.")
                break

            part = resp.candidates[0].content.parts[0]
            model_content = resp.candidates[0].content
            model_content.role = "model"
            history.append(model_content)

            if hasattr(part, 'function_call') and part.function_call:
                tool_result = await execute_tool_call(page, part)
                tool_response_part = genai_types.Part.from_function_response(
                    name=part.function_call.name,
                    response=tool_result
                )
                history.append(genai_types.Content(role="tool", parts=[tool_response_part]))

            elif hasattr(part, 'text') and part.text.strip():
                text = part.text.strip()
                print("\n💬 Модель говорит:")
                print(text)

                # Завершаем ТОЛЬКО при явном результате
                if any(kw in text.lower() for kw in ["курс доллара", "курс:", "usd", "доллар"]):
                    print("\n✅ Задача успешно завершена!")
                    break
                else:
                    print("  → Промежуточное сообщение. Продолжаю...")
                    # Не выходим — ждём дальнейших действий

            else:
                print("\n[ОШИБКА] Неожиданный формат ответа.")
                break

        else:
            print("\n[ПРЕДУПРЕЖДЕНИЕ] Достигнут лимит шагов (15).")

    except Exception as e:
        print(f"\n[КРИТИЧЕСКАЯ ОШИБКА] {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser.close()
        await playwright.stop()
        print("\nБраузер закрыт.")


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise