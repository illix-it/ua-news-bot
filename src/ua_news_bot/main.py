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
    items = await fetch_all_latest(sources, per_source_limit=30, dedup=None)

    # Only select items not seen yet (but do NOT mark them yet)
    candidates = [x for x in items if not dedup.has(x.url)]
    # We only want the freshest item(s) and do NOT want to "catch up" backlog.
    to_post = candidates[:max_posts]

    # Mark the rest as seen to avoid slowly draining old backlog over time.
    for it in candidates[max_posts:]:
        dedup.mark_seen(it.url)

    print(
        f"[FETCH] fetched={len(items)} candidates={len(candidates)} "
        f"will_post={len(to_post)} skipped_backlog={max(0, len(candidates) - len(to_post))}"
    )

    if dry_run:
        for i, item in enumerate(to_post, start=1):
            text = format_telegram_post(item)
            print(f"\n--- DRY RUN POST #{i} ---\n{text}\n")

            # Simulate successful posting to advance the queue during dry-run
            dedup.mark_seen(item.url)

        return 0

    sent = 0
    for item in to_post:
        text = format_telegram_post(item)

        # NOTE: Telegram HTML formatting requires parse_mode="HTML" in your client
        await tg.send_message(chat_id, text)

        # Mark as seen only AFTER successful send
        dedup.mark_seen(item.url)
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

    # Warm start: skip backlog so we only post truly new items going forward.
    if settings.init_skip_existing:
        sources = [SuspilneSource()]
        items = await fetch_all_latest(sources, per_source_limit=30, dedup=None)

        if items and settings.init_post_latest:
            latest = items[0]  # assuming aggregator returns newest-first
            text = format_telegram_post(latest)

            print(f"[INIT] latest: {latest.title} ({latest.url})")
            if settings.dry_run:
                print(f"\n--- INIT PREVIEW ---\n{text}\n")
            else:
                await tg.send_message(settings.telegram_chat_id, text)
                print("[INIT] posted latest ✅")

            # Mark it as seen so it won't be reposted in the loop
            dedup.mark_seen(latest.url)

        marked = 0
        for it in items:
            if not dedup.has(it.url):
                dedup.mark_seen(it.url)
                marked += 1

        print(f"[INIT] skip-existing enabled: marked_seen={marked} (backlog skipped)")
        print("[INIT] IMPORTANT: set INIT_SKIP_EXISTING=false after first run")

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
                if settings.dry_run:
                    print("[DONE] dry-run cycle ✅")
                else:
                    print(f"[POST] sent={sent} ✅")
            except Exception as e:
                print(f"[ERR] {type(e).__name__}: {e}")

            await asyncio.sleep(settings.poll_interval_seconds)
    finally:
        dedup.close()


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
