from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

from ua_news_bot.sources.suspilne import SuspilneSource


def build_prompt(title: str, summary: str, language: str) -> str:
    return f"""
Ты работаешь как строгий редактор новостного Telegram-канала Smart News.

Твоя задача:
сделать из RSS-новости короткий, понятный и красиво оформленный пост для Telegram.

Правила:
- Язык: {language}
- Не добавляй новых фактов
- Не меняй даты, цифры, имена, географию
- Не добавляй ссылки
- Не пиши пояснений
- Не обрезай слова посередине
- Старайся писать просто и легко для чтения

Формат:
- Первая строка: <b>короткий заголовок</b>
- Потом 1–3 коротких абзаца
- Можно использовать:
  - <b>...</b>
  - <i>...</i>
  - <u>...</u>
  - <blockquote>...</blockquote>

Важно:
- Не добавляй строку "Джерело:"
- Верни только готовый HTML-текст поста

Оригинальный заголовок:
{title}

Оригинальный RSS-текст:
{summary}
""".strip()


def call_gemini_rest(prompt: str, api_keys: list[str], model: str) -> str:
    last_error: str | None = None

    for key in api_keys:
        key = key.strip()
        if not key:
            continue

        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": prompt,
                                }
                            ]
                        }
                    ]
                },
                timeout=30,
            )

            data: dict[str, Any] = resp.json()

            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}: {data}"
                print(f"[REST] key {key[:6]}... failed -> {last_error}")
                continue

            candidates = data.get("candidates") or []
            if not candidates:
                last_error = f"No candidates in response: {data}"
                print(f"[REST] key {key[:6]}... empty candidates")
                continue

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                last_error = f"No parts in first candidate: {data}"
                print(f"[REST] key {key[:6]}... empty parts")
                continue

            text = (parts[0].get("text") or "").strip()
            if not text:
                last_error = f"Empty text in first part: {data}"
                print(f"[REST] key {key[:6]}... empty text")
                continue

            print(f"[REST] success with key {key[:6]}...")
            return text

        except Exception as e:
            last_error = repr(e)
            print(f"[REST] key {key[:6]}... exception -> {e}")

    raise RuntimeError(f"All Gemini REST keys failed. Last error: {last_error}")


async def main() -> None:
    load_dotenv()

    model = (os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip()
    language = (os.getenv("CHANNEL_LANGUAGE") or "uk").strip()

    # One or many keys:
    # GEMINI_API_KEY=...
    # or GEMINI_API_KEYS=key1,key2,key3
    single_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    multi_keys = (os.getenv("GEMINI_API_KEYS") or "").strip()

    api_keys: list[str] = []
    if multi_keys:
        api_keys.extend([x.strip() for x in multi_keys.split(",") if x.strip()])
    if single_key:
        api_keys.append(single_key)

    if not api_keys:
        raise RuntimeError("No GEMINI_API_KEY or GEMINI_API_KEYS found in .env")

    source = SuspilneSource()
    items = await source.fetch_latest(limit=1)

    if not items:
        raise RuntimeError("No RSS items fetched")

    item = items[0]
    prompt = build_prompt(item.title, item.summary or "", language)

    print("\n=== MODEL ===")
    print(model)

    print("\n=== ORIGINAL TITLE ===")
    print(item.title)

    print("\n=== ORIGINAL SUMMARY ===")
    print(item.summary or "(empty)")

    print("\n=== PROMPT ===")
    print(prompt)

    result = call_gemini_rest(prompt, api_keys, model)

    print("\n=== GEMINI REST OUTPUT ===")
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
