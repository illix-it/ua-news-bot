import asyncio

from ua_news_bot.aggregator import fetch_all_latest
from ua_news_bot.config import load_settings
from ua_news_bot.dedup import SeenStore
from ua_news_bot.formatter import format_telegram_post
from ua_news_bot.sources.suspilne import SuspilneSource
from ua_news_bot.telegram_client import TelegramClient


async def run() -> None:
    settings = load_settings()

    print(
        f"[CFG] dry_run={settings.dry_run} "
        f"max_posts_per_run={settings.max_posts_per_run} "
        f"ai_enabled={settings.ai_enabled}"
    )

    sources = [SuspilneSource()]
    items = await fetch_all_latest(sources, per_source_limit=30, dedup=SeenStore())

    to_process = items[: settings.max_posts_per_run]
    print(f"[FETCH] fetched={len(items)} will_process={len(to_process)}")

    if settings.dry_run:
        for i, item in enumerate(to_process, start=1):
            text = format_telegram_post(item)
            print(f"\n--- DRY RUN POST #{i} ---\n{text}\n")
        print("[DONE] dry-run completed ✅")
        return

    tg = TelegramClient(settings.telegram_bot_token)

    sent = 0
    for item in to_process:
        text = format_telegram_post(item)
        await tg.send_message(settings.telegram_chat_id, text)
        sent += 1

    print(f"[POST] sent={sent} ✅")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
