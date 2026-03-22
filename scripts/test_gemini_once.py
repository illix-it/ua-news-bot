from __future__ import annotations

import os

from dotenv import load_dotenv

from ua_news_bot.ai.gemini_enhancer import GeminiConfig, GeminiEnhancer
from ua_news_bot.sources.suspilne import SuspilneSource


async def main() -> None:
    load_dotenv()

    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    model = (os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip()
    language = (os.getenv("CHANNEL_LANGUAGE") or "uk").strip()

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing")

    source = SuspilneSource()
    items = await source.fetch_latest(limit=1)

    if not items:
        raise RuntimeError("No RSS items fetched")

    item = items[0]

    enhancer = GeminiEnhancer(
        GeminiConfig(
            api_key=api_key,
            model=model,
            channel_language=language,
        )
    )

    print("\n=== ORIGINAL TITLE ===")
    print(item.title)

    print("\n=== ORIGINAL SUMMARY ===")
    print(item.summary or "(empty)")

    result = enhancer.enhance(item.title, item.summary)

    print("\n=== GEMINI OUTPUT ===")
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
