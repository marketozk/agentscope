"""
Продолжение диалога с GPT-5 Pro (Responses API) по id предыдущего ответа

Использование (Windows CMD, из папки Browser_Use):
  1) По JSON файлу ответа:
     ..\.venv\Scripts\python.exe continue_gpt5_pro_chat.py --json "gpt5_self_learning_solution_20251019_021017.json" --question "Коротко резюмируй и дай чеклист внедрения"

  2) Непосредственно по id ответа:
     ..\.venv\Scripts\python.exe continue_gpt5_pro_chat.py --response-id "resp_01a6b1b8055245090068f41c4ca19081908c1dc2f34757b2b5" --question "Что оптимизировать в safe_screenshot?"

Параметры:
  --json <path>           Путь к сохраненному JSON ответу (как в gpt5_self_learning_solution_*.json)
  --response-id <id>      Идентификатор ответа (resp_...)
  --question <text>       Follow-up вопрос пользоватeля
  --model <name>          Модель (по умолчанию берется из JSON, иначе gpt-5-pro)
  --max-output-tokens N   Лимит токенов ответа (опционально)

Требуется переменная окружения OPENAI_API_KEY
"""

from __future__ import annotations
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
import time
import requests
from typing import Optional
import random

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
RESPONSES_URL = "https://api.openai.com/v1/responses"


def load_response_json(json_path: Path) -> dict:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_model_from_json(data: dict) -> Optional[str]:
    # Пытаемся вытащить точное имя модели из сохраненного ответа
    # Примеры: "gpt-5-pro" или "gpt-5-pro-2025-10-06"
    return data.get("model") or (data.get("response", {}) if False else None)


def extract_response_id(data: dict) -> Optional[str]:
    # Ищем id ответа на верхнем уровне
    # Пример: "id": "resp_..."
    return data.get("id")


def build_headers() -> dict:
    if not OPENAI_API_KEY:
        raise RuntimeError("Не найден OPENAI_API_KEY в переменных окружения")
    return {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }


def build_payload(question: str, model: str, previous_response_id: str, max_output_tokens: Optional[int] = None) -> dict:
    payload = {
        "model": model,
        "input": [
            {"role": "user", "content": question}
        ],
        "previous_response_id": previous_response_id,
        # Храним тред, чтобы можно было продолжать в будущем
        "store": True,
    }
    if max_output_tokens:
        # некоторые версии API принимают max_output_tokens либо max_output_tokens/max_completion_tokens
        payload["max_output_tokens"] = int(max_output_tokens)
    return payload


def send_followup(
    question: str,
    response_id: str,
    model: Optional[str],
    max_output_tokens: Optional[int],
    pre_wait: float = 0.0,
    attempts: int = 5,
    base_backoff: float = 8.0,
    max_backoff: float = 120.0,
):
    model_final = model or "gpt-5-pro"
    headers = build_headers()
    payload = build_payload(question=question, model=model_final, previous_response_id=response_id, max_output_tokens=max_output_tokens)

    print("\n📤 Отправка follow-up в тот же чат GPT-5 Pro...")
    print(f"   previous_response_id: {response_id}")
    print(f"   model: {model_final}")

    # Предварительная задержка (смягчить всплески)
    if pre_wait and pre_wait > 0:
        print(f"   ⏳ Предварительное ожидание перед запросом: {int(pre_wait)} сек...")
        time.sleep(pre_wait)

    # Расширенная стратегия повторов на 429/5xx с джиттером и уважением Retry-After
    last_error_text = None
    for i in range(1, attempts + 1):
        try:
            r = requests.post(RESPONSES_URL, headers=headers, json=payload)
        except requests.RequestException as e:
            last_error_text = str(e)
            if i < attempts:
                # Небольшой джиттер перед повтором сети
                sleep_s = min(base_backoff * (2 ** (i - 1)), max_backoff) + random.uniform(0, 1.5)
                print(f"⚠️  Сетевая ошибка: {e}. Повтор через {int(sleep_s)} сек (попытка {i}/{attempts})...")
                time.sleep(sleep_s)
                continue
            raise RuntimeError(f"Ошибка сети при обращении к API после {attempts} попыток: {last_error_text}")

        if r.status_code == 200:
            break
        # Обработка 429/5xx
        if r.status_code in (429, 500, 502, 503, 504) and i < attempts:
            retry_after = r.headers.get("retry-after")
            if retry_after:
                try:
                    wait_s = float(retry_after)
                except ValueError:
                    wait_s = None
            else:
                wait_s = None

            if wait_s is None:
                # Экспоненциальный бэкофф с джиттером
                wait_s = min(base_backoff * (2 ** (i - 1)), max_backoff) + random.uniform(0, 2.0)

            brief_text = r.text[:200].replace("\n", " ") if r.text else ""
            print(f"⚠️  {r.status_code} от API. Повтор через {int(wait_s)} сек (попытка {i}/{attempts})... Детали: {brief_text}")
            time.sleep(wait_s)
            continue

        # Иные ошибки — сразу пробрасываем
        raise RuntimeError(f"Ошибка API: {r.status_code} - {r.text}")

    data = r.json()
    return data


def extract_output_text(data: dict) -> str:
    # Универсальная попытка извлечь основной текст
    # Вариант 1: некоторые реализации добавляют 'output_text'
    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()

    # Вариант 2: обойти массив 'output' и достать текстовые блоки из message.content
    out = data.get("output")
    texts: list[str] = []
    if isinstance(out, list):
        for item in out:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message":
                # В новых ответах message.content — массив блоков
                for block in item.get("content", []) or []:
                    # Ищем блоки типа output_text/text
                    if isinstance(block, dict):
                        if block.get("type") in ("output_text", "text"):
                            t = block.get("text")
                            if isinstance(t, str):
                                texts.append(t)
    if texts:
        return "\n\n".join(texts).strip()

    # Фоллбэк: raw JSON
    return json.dumps(data, ensure_ascii=False, indent=2)


def save_followup(data: dict, base_dir: Path) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = base_dir / f"gpt5_followup_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # Дополнительно сохраним извлеченный текст
    txt = extract_output_text(data)
    txt_path = base_dir / f"gpt5_followup_{ts}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"\n💾 Follow-up сохранен:\n   JSON: {json_path}\n   TEXT: {txt_path}")
    return json_path


def main():
    parser = argparse.ArgumentParser(description="Продолжить диалог с GPT-5 Pro через previous_response_id (Responses API)")
    parser.add_argument("--json", dest="json_path", help="Путь к ранее сохраненному JSON ответу (gpt5_self_learning_solution_*.json)")
    parser.add_argument("--response-id", dest="response_id", help="ID ответа (resp_...)")
    parser.add_argument("--question", required=False, help="Follow-up вопрос для GPT-5 Pro")
    parser.add_argument("--question-file", dest="question_file", required=False, help="Путь к файлу с текстом вопроса (альтернатива --question)")
    parser.add_argument("--model", dest="model", help="Имя модели (по умолчанию из JSON или gpt-5-pro)")
    parser.add_argument("--max-output-tokens", dest="max_output_tokens", type=int, default=None, help="Лимит токенов ответа")
    parser.add_argument("--out", dest="out_dir", default="logs", help="Папка для сохранения follow-up (по умолчанию logs)")
    parser.add_argument("--pre-wait", dest="pre_wait", type=float, default=0.0, help="Предварительная задержка перед первым запросом (сек)")
    parser.add_argument("--retries", dest="retries", type=int, default=5, help="Количество попыток при 429/5xx")

    args = parser.parse_args()

    if not OPENAI_API_KEY:
        raise SystemExit("❌ OPENAI_API_KEY не задан. Установите переменную окружения и повторите.")

    response_id: Optional[str] = args.response_id
    model: Optional[str] = args.model
    question: Optional[str] = args.question

    # Разрешаем загрузку вопроса из файла, если указан --question-file
    if args.question_file:
        qpath = Path(args.question_file)
        if not qpath.exists():
            raise SystemExit(f"Файл вопроса не найден: {qpath}")
        question = qpath.read_text(encoding="utf-8", errors="ignore")

    if not question or not question.strip():
        raise SystemExit("Нужно указать --question или --question-file с непустым содержимым")

    original_max_output_tokens: Optional[int] = None

    if not response_id:
        if not args.json_path:
            raise SystemExit("Нужно указать --json <file> или --response-id <id>")
        # Грузим JSON и извлекаем id + модель
        json_file = Path(args.json_path)
        if not json_file.exists():
            raise SystemExit(f"Файл не найден: {json_file}")
        data = load_response_json(json_file)
        response_id = extract_response_id(data)
        if not response_id:
            raise SystemExit("Не удалось извлечь id из JSON (ожидали поле 'id')")
        if not model:
            model = extract_model_from_json(data) or "gpt-5-pro"
        # Используем те же параметры токенов, если они присутствуют в исходном JSON
        try:
            original_max_output_tokens = data.get("max_output_tokens")
            if isinstance(original_max_output_tokens, str):
                original_max_output_tokens = int(original_max_output_tokens)
            if not isinstance(original_max_output_tokens, int):
                original_max_output_tokens = None
        except Exception:
            original_max_output_tokens = None
    else:
        if not model:
            model = "gpt-5-pro"

    # Отправляем follow-up
    # Если пользователь не задал лимит, но он был в исходном JSON — применим его; иначе не передаём вовсе
    effective_max_tokens = args.max_output_tokens if args.max_output_tokens is not None else original_max_output_tokens
    data = send_followup(
        question=question,
        response_id=response_id,
        model=model,
        max_output_tokens=effective_max_tokens,
        pre_wait=float(args.pre_wait or 0.0),
        attempts=int(args.retries or 5),
    )

    # Сохраняем
    out_dir = Path(args.out_dir)
    save_followup(data, out_dir)

    # Печатаем краткий ответ в консоль
    print("\n📥 Ответ GPT-5 Pro (кратко):\n" + "-" * 80)
    print(extract_output_text(data)[:4000])
    print("\n" + "-" * 80)


if __name__ == "__main__":
    main()
