"""
Тест нового SDK google.genai с моделью gemini-2.5-computer-use-preview-10-2025.
Цель: убедиться, что запрос проходит без 400 INVALID_ARGUMENT и SDK отвечает.

Минимальный пример: отправляем простой текстовый запрос с включенным инструментом Computer Use.
Мы НЕ используем browser-use.Agent здесь, чтобы изолировать проверку SDK/модели.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Новый SDK
from google import genai as genai_new
from google.genai import types as genai_types


def main():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY не найден в .env")

    client = genai_new.Client(api_key=api_key)

    model = "gemini-2.5-computer-use-preview-10-2025"

    # Инструмент Computer Use с браузерной средой
    tool = genai_types.Tool(
        computer_use=genai_types.ComputerUse(
            environment=genai_types.Environment.ENVIRONMENT_BROWSER
        )
    )

    # Конфиг без response_mime_type
    config = genai_types.GenerateContentConfig(
        tools=[tool],
        temperature=0.2,
        max_output_tokens=2048,
    )

    # Простой запрос без навигации, чтобы получить текст и проверить, что ответ доступен
    prompt = (
        "Reply with a single short sentence: 'Computer-use model is reachable.' "
        "Do not call any tools."
    )

    print("🚀 Отправка тестового запроса в модель", model)
    resp = client.models.generate_content(
        model=model,
        contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])],
        config=config,
    )

    # Вывод
    print("✅ Ответ получен\n")
    print("response.text:", repr(resp.text))

    # -------------------------------
    # Детальный разбор parts/кандидатов
    # -------------------------------
    def _shorten(val, max_len=800):
        if isinstance(val, str) and len(val) > max_len:
            return val[:max_len] + f"… [truncated {len(val)-max_len} chars]"
        return val

    def to_jsonable(obj, _depth=0):
        if _depth > 6:
            return repr(obj)
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj if not isinstance(obj, str) else _shorten(obj)
        if isinstance(obj, (list, tuple)):
            return [to_jsonable(x, _depth + 1) for x in obj]
        if isinstance(obj, dict):
            return {str(k): to_jsonable(v, _depth + 1) for k, v in obj.items()}
        # Популярные варианты сериализации у SDK
        for m in ("to_dict", "model_dump", "dict"):
            fn = getattr(obj, m, None)
            if callable(fn):
                try:
                    return to_jsonable(fn(), _depth + 1)
                except Exception:
                    pass
        # Падаем обратно на __dict__
        if hasattr(obj, "__dict__"):
            data = {}
            for k, v in obj.__dict__.items():
                if not k.startswith("_"):
                    data[k] = to_jsonable(v, _depth + 1)
            return data
        return repr(obj)

    # Сводка по кандидатам и частям
    try:
        for i, cand in enumerate(getattr(resp, "candidates", []) or []):
            finish = getattr(cand, "finish_reason", None)
            print(f"\n— Candidate {i}: finish_reason={finish}")
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) if content else None
            if not parts:
                print("   (no parts)")
                continue
            for j, part in enumerate(parts):
                ptype = getattr(part, "type", None)
                print(f"   Part {j}: type={ptype}")
                # Попробуем показать ключевые поля part
                # частые поля: text, executable_code, code_execution_result, function_call, tool_call, computer_use, json
                for key in (
                    "text",
                    "function_call",
                    "tool_call",
                    "computer_use",
                    "executable_code",
                    "code_execution_result",
                    "json",
                ):
                    if hasattr(part, key):
                        try:
                            val = getattr(part, key)
                            printable = to_jsonable(val)
                            # укоротим шумные поля
                            if isinstance(printable, dict):
                                preview = json.dumps(printable, ensure_ascii=False)[:600]
                                print(f"      {key}: {preview}{'…' if len(preview)==600 else ''}")
                            else:
                                print(f"      {key}: {_shorten(str(printable), 600)}")
                        except Exception as e:
                            print(f"      {key}: <error: {e}>")
    except Exception as e:
        print("[warn] Ошибка при разборе parts:", e)

    # Полный дамп ответа в JSON-файл для анализа (в том числе мысли/действия)
    try:
        dump_dir = Path(__file__).parent / "logs"
        dump_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dump_path = dump_dir / f"test_agent_full_response_{ts}.json"
        with dump_path.open("w", encoding="utf-8") as f:
            json.dump(to_jsonable(resp), f, ensure_ascii=False, indent=2)
        print(f"\n📝 Полный ответ сохранён: {dump_path}")
    except Exception as e:
        print("[warn] Не удалось сохранить полный ответ:", e)


if __name__ == "__main__":
    main()