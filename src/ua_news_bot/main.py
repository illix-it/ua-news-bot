import asyncio
from pathlib import Path

from ua_news_bot.aggregator import fetch_all_latest
from ua_news_bot.config import load_settings
from ua_news_bot.dedup_sqlite import SQLiteSeenStore
from ua_news_bot.formatter import format_telegram_post
from ua_news_bot.sources.suspilne import SuspilneSource
from ua_news_bot.telegram_client import TelegramClient


def _build_raw_text(title: str, summary: str | None) -> str:
    s = (summary or "").strip()
    if s:
        return f"{title}\n\n{s}"
    return title


def _is_balanced_html(text: str) -> bool:
    tags = ["b", "i", "u", "blockquote"]
    for t in tags:
        if text.count(f"<{t}>") != text.count(f"</{t}>"):
            return False
    return True


def _validate_ai_post(text: str) -> bool:
    if not text:
        return False
    if not _is_balanced_html(text):
        return False

    lines = [ln.rstrip() for ln in text.splitlines()]
    first = next((ln for ln in lines if ln.strip()), "")
    if not (first.startswith("<b>") and "</b>" in first):
        return False

    bullet_lines = [ln for ln in lines if ln.strip().startswith("• ")]
    if len(bullet_lines) < 3:
        return False

    if len(text) < 200:
        return False

    return True


async def run_once(
        *,
        tg: TelegramClient,
        settings,
        dedup: SQLiteSeenStore,
) -> int:
    sources = [SuspilneSource()]
    items = await fetch_all_latest(sources, per_source_limit=30, dedup=None)

    candidates = [x for x in items if not dedup.has(x.url)]
    to_post = candidates[: settings.max_posts_per_run]

    # Skip backlog: mark extras as seen so we only post the freshest.
    for it in candidates[settings.max_posts_per_run :]:
        dedup.mark_seen(it.url)

    print(
        f"[FETCH] fetched={len(items)} candidates={len(candidates)} "
        f"will_post={len(to_post)} skipped_backlog={max(0, len(candidates) - len(to_post))}"
    )

    if not to_post:
        return 0

    enhancer = None
    if settings.ai_enabled and settings.ai_provider == "gemini":
        from ua_news_bot.ai.gemini_enhancer import GeminiConfig, GeminiEnhancer

        if not settings.gemini_api_key:
            raise RuntimeError("AI_ENABLED=true but GEMINI_API_KEY is missing")

        enhancer = GeminiEnhancer(
            GeminiConfig(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                channel_language=settings.channel_language,
            )
        )

    sent = 0
    for item in to_post:
        try:
            if enhancer is not None:
                raw = _build_raw_text(item.title, item.summary)
                ai_text = enhancer.enhance(raw)

                if ai_text.strip().upper() == "SKIP":
                    print(f"[AI] SKIP: {item.url}")
                    dedup.mark_seen(item.url)
                    continue

                if not _validate_ai_post(ai_text):
                    raise ValueError("AI output failed validation")

                text = f"{ai_text}\n\nДжерело: {item.source} {item.url}"
            else:
                text = format_telegram_post(item)

            if settings.dry_run:
                print(f"\n--- DRY RUN POST ---\n{text}\n")
                if settings.dry_run_mark_seen:
                    dedup.mark_seen(item.url)
                continue

            await tg.send_message(settings.telegram_chat_id, text)
            dedup.mark_seen(item.url)
            sent += 1

        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e} (fallback formatter)")

            fallback = format_telegram_post(item)
            if settings.dry_run:
                print(f"\n--- DRY RUN FALLBACK ---\n{fallback}\n")
                if settings.dry_run_mark_seen:
                    dedup.mark_seen(item.url)
                continue

            await tg.send_message(settings.telegram_chat_id, fallback)
            dedup.mark_seen(item.url)
            sent += 1

    return sent


async def run_forever() -> None:
    settings = load_settings()

    print(
        f"[CFG] dry_run={settings.dry_run} "
        f"max_posts_per_run={settings.max_posts_per_run} "
        f"poll_interval_seconds={settings.poll_interval_seconds} "
        f"ai_enabled={settings.ai_enabled} ai_provider={settings.ai_provider}"
    )
    if settings.ai_enabled and settings.ai_provider == "gemini":
        print(f"[AI] model={settings.gemini_model}")

    # Optional: reset dedup for local testing
    if settings.reset_dedup_on_start:
        try:
            Path(settings.dedup_db_path).unlink(missing_ok=True)
            print(f"[DEDUP] reset: deleted {settings.dedup_db_path}")
        except Exception as e:
            print(f"[DEDUP] reset failed: {type(e).__name__}: {e}")

    tg = TelegramClient(settings.telegram_bot_token)
    dedup = SQLiteSeenStore(settings.dedup_db_path)

    try:
        while True:
            try:
                sent = await run_once(tg=tg, settings=settings, dedup=dedup)
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