import asyncio

from ua_news_bot.aggregator import fetch_all_latest
from ua_news_bot.config import load_settings
from ua_news_bot.dedup import SeenStore
from ua_news_bot.formatter import format_telegram_post
from ua_news_bot.sources.suspilne import SuspilneSource
from ua_news_bot.telegram_client import TelegramClient

POST_LIMIT = 3  # safety for v1


async def run() -> None:
    settings = load_settings()
    tg = TelegramClient(settings.telegram_bot_token)

    sources = [SuspilneSource()]
    items = await fetch_all_latest(sources, per_source_limit=20, dedup=SeenStore())

    to_post = items[:POST_LIMIT]
    print(f"Fetched: {len(items)}; posting: {len(to_post)}")

    for item in to_post:
        text = format_telegram_post(item)
        await tg.send_message(settings.telegram_chat_id, text)

    print("Done ✅")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
