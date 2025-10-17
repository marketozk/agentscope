import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Предполагается, что используется альфа/внутренняя версия google.genai с Computer Use
from google import genai as genai_new
from google.genai import types as genai_types

from playwright.async_api import async_playwright


async def execute_tool_call(page, tool_call):
    """Выполняет команду, полученную от модели, в браузере."""
    if not hasattr(tool_call, 'function_call') or not tool_call.function_call:
        return {"output": json.dumps({"status": "ERROR", "message": "Не является вызовом функции."})}

    command = tool_call.function_call.name
    args = dict(tool_call.function_call.args)

    print(f"  ▶️ Выполнение: {command} с аргументами {args}")

    try:
        if command == "navigate_to":
            url = args.get("url", "").strip()
            if not url:
                return {"output": json.dumps({"status": "ERROR", "message": "URL не указан"})}
            await page.goto(url)
        elif command == "type":
            element_id = args.get("element_id")
            text = args.get("text", "")
            if not element_id:
                return {"output": json.dumps({"status": "ERROR", "message": "element_id не указан"})}
            await page.locator(f'[data-testid="{element_id}"]').fill(text)
        elif command == "click":
            element_id = args.get("element_id")
            if not element_id:
                return {"output": json.dumps({"status": "ERROR", "message": "element_id не указан"})}
            await page.locator(f'[data-testid="{element_id}"]').click()
        elif command == "open_web_browser":
            url = args.get("url", "https://www.google.com").strip()  # Убраны лишние пробелы
            await page.goto(url)
        else:
            return {"output": json.dumps({"status": "ERROR", "message": f"Неизвестная команда '{command}'"})}

        # Ждём стабилизации страницы
        await page.wait_for_load_state("networkidle")

        # Возвращаем результат в формате, ожидаемом Computer Use: {"output": "..."}
        return {"output": json.dumps({
            "status": "SUCCESS",
            "url": page.url
        })}

    except Exception as e:
        print(f"  ❌ Ошибка выполнения команды: {e}")
        return {"output": json.dumps({
            "status": "ERROR",
            "message": str(e),
            "url": page.url
        })}


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

    prompt = "Открой сайт yandex.ru и найди 'курс доллара'"
    print(f"🚀 Начало задачи: {prompt}\n")

    # История диалога: начинается с user
    history = [genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])]

    try:
        for step in range(10):
            print(f"🧠 Шаг {step + 1}: модель анализирует страницу...")

            # Ждём загрузки DOM перед скриншотом
            await page.wait_for_load_state("domcontentloaded")
            screenshot = await page.screenshot(type="png")

            image_part = genai_types.Part(
                inline_data=genai_types.Blob(mime_type="image/png", data=screenshot)
            )

            # Текущий запрос: история + новый скриншот от пользователя
            current_request_contents = history + [
                genai_types.Content(role="user", parts=[image_part])
            ]

            # Генерация ответа
            resp = client.models.generate_content(
                model=model_name,
                contents=current_request_contents,
                config=config,
            )

            # Проверка наличия кандидатов
            if not resp.candidates:
                print("\n[ОШИБКА] Модель не вернула кандидатов.")
                break

            candidate = resp.candidates[0]
            if not candidate.content or not candidate.content.parts:
                print("\n[ОШШИБКА] Пустой ответ от модели.")
                break

            part = candidate.content.parts[0]

            # Случай 1: модель вызывает функцию (инструмент)
            if hasattr(part, 'function_call') and part.function_call:
                # Устанавливаем роль "model" явно
                model_content = candidate.content
                model_content.role = "model"
                history.append(model_content)

                # Выполняем команду
                tool_result = await execute_tool_call(page, part)

                # Формируем ответ инструмента
                tool_response_part = genai_types.Part.from_function_response(
                    name=part.function_call.name,
                    response=tool_result  # уже содержит {"output": "..."}
                )
                history.append(genai_types.Content(role="tool", parts=[tool_response_part]))

            # Случай 2: модель даёт финальный текстовый ответ
            elif hasattr(part, 'text') and part.text.strip():
                model_content = candidate.content
                model_content.role = "model"
                history.append(model_content)

                print("\n✅ Задача выполнена! Финальный ответ:")
                print(part.text.strip())
                break

            else:
                print("\n[ОШИБКА] Неожиданный формат ответа от модели.")
                print(f"Ответ: {resp}")
                break

        else:
            print("\n[ПРЕДУПРЕЖДЕНИЕ] Достигнут лимит в 10 шагов. Цикл остановлен.")

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