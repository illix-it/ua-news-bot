import asyncio

from ua_news_bot.aggregator import fetch_all_latest
from ua_news_bot.config import load_settings
from ua_news_bot.dedup_sqlite import SQLiteSeenStore
from ua_news_bot.formatter import format_telegram_post
from ua_news_bot.sources.suspilne import SuspilneSource
from ua_news_bot.telegram_client import TelegramClient


async def run_once(
    *,
    tg: TelegramClient,
    chat_id: str,
    dedup: SQLiteSeenStore,
    max_posts: int,
    dry_run: bool,
) -> int:
    sources = [SuspilneSource()]

    # Fetch recent items (RSS usually returns latest N)
    items = await fetch_all_latest(sources, per_source_limit=30, dedup=None)

    # Apply persisted dedup by URL (forever)
    new_items = [x for x in items if dedup.is_new(x.url)]
    to_post = new_items[:max_posts]

    print(f"[FETCH] fetched={len(items)} new={len(new_items)} will_post={len(to_post)}")

    if dry_run:
        for i, item in enumerate(to_post, start=1):
            text = format_telegram_post(item)
            print(f"\n--- DRY RUN POST #{i} ---\n{text}\n")
        return 0

    sent = 0
    for item in to_post:
        text = format_telegram_post(item)
        await tg.send_message(chat_id, text)
        sent += 1

    return sent


async def run_forever() -> None:
    settings = load_settings()

    print(
        f"[CFG] dry_run={settings.dry_run} "
        f"max_posts_per_run={settings.max_posts_per_run} "
        f"poll_interval_seconds={settings.poll_interval_seconds} "
        f"ai_enabled={settings.ai_enabled}"
    )

    tg = TelegramClient(settings.telegram_bot_token)
    dedup = SQLiteSeenStore()

    try:
        while True:
            try:
                sent = await run_once(
                    tg=tg,
                    chat_id=settings.telegram_chat_id,
                    dedup=dedup,
                    max_posts=settings.max_posts_per_run,
                    dry_run=settings.dry_run,
                )
                if not settings.dry_run:
                    print(f"[POST] sent={sent} ✅")
                else:
                    print("[DONE] dry-run cycle ✅")
            except Exception as e:
                # keep process alive; later we’ll replace with structured logging
                print(f"[ERR] {type(e).__name__}: {e}")

            await asyncio.sleep(settings.poll_interval_seconds)
    finally:
        dedup.close()


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
