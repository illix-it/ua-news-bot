from __future__ import annotations

import asyncio
import html
import re
from pathlib import Path

from ua_news_bot.aggregator import fetch_all_latest
from ua_news_bot.config import load_settings
from ua_news_bot.dedup_sqlite import SQLiteSeenStore
from ua_news_bot.formatter import format_telegram_post
from ua_news_bot.media.downloader import download_image_bytes
from ua_news_bot.media.image_editor import add_branding_to_image
from ua_news_bot.sources.suspilne import SuspilneSource
from ua_news_bot.telegram_client import TelegramClient

_B_RE = re.compile(r"<b>.*?</b>", re.DOTALL)
_TAG_BALANCE_TAGS = ["b", "i", "u", "blockquote", "tg-spoiler"]
_SOURCE_LINE_RE = re.compile(r"\n\nДжерело:.*$", re.DOTALL)


def _build_ai_input(title: str, summary: str | None) -> str:
    summary = (summary or "").strip()
    if summary:
        return f"{title.strip()}\n\n{summary}"
    return title.strip()


def _has_balanced_tags(text: str) -> bool:
    for tag in _TAG_BALANCE_TAGS:
        if text.count(f"<{tag}>") != text.count(f"</{tag}>"):
            return False
    return True


def _ai_output_is_bad(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return True
    if len(cleaned) < 120:
        return True
    if not _B_RE.search(cleaned):
        return True
    if not _has_balanced_tags(cleaned):
        return True
    if "Джерело:" in cleaned:
        return True
    last_char = cleaned[-1]
    if last_char.isalnum():
        return True
    return False


def _append_cta(text: str, cta_text: str, cta_url: str) -> str:
    if not cta_text or not cta_url:
        return text

    safe_text = html.escape(cta_text)
    cta = f'<a href="{cta_url}">{safe_text}</a>'
    return f"{text}\n\n{cta}"


def _remove_source_line(text: str) -> str:
    return _SOURCE_LINE_RE.sub("", text).strip()


async def _prepare_media_photo(item) -> bytes | None:
    if not item.image_urls:
        return None

    first_url = item.image_urls[0]
    try:
        content = await download_image_bytes(first_url, referer=item.url)
        branded = add_branding_to_image(
            image_bytes=content,
            watermark_text="@smart_news_ua",
        )
        return branded.getvalue()
    except Exception as e:
        print(f"[MEDIA] image prepare failed: {e}")
        return None


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

        api_keys: list[str] = []
        if settings.gemini_api_keys:
            api_keys.extend([x.strip() for x in settings.gemini_api_keys.split(",") if x.strip()])
        if settings.gemini_api_key:
            api_keys.append(settings.gemini_api_key)

        if not api_keys:
            raise RuntimeError("AI_ENABLED=true but no Gemini API keys found")

        enhancer = GeminiEnhancer(
            GeminiConfig(
                api_keys=api_keys,
                model=settings.gemini_model,
                channel_language=settings.channel_language,
            )
        )

    sent = 0
    for item in to_post:
        rss_post = format_telegram_post(item)
        channel_fallback = _append_cta(
            _remove_source_line(rss_post),
            settings.channel_cta_text,
            settings.channel_cta_url,
        )
        rss_debug_post = _append_cta(
            rss_post,
            settings.channel_cta_text,
            settings.channel_cta_url,
        )

        try:
            if settings.dry_run:
                print(f"\n--- DRY RUN RSS POST ---\n{rss_debug_post}\n")
                if item.image_urls:
                    print(f"--- DRY RUN IMAGE URL ---\n{item.image_urls[0]}\n")

            if enhancer is not None:
                ai_input = _build_ai_input(item.title, item.summary)
                ai_text = enhancer.enhance(ai_input)

                if ai_text == "SKIP":
                    print("[AI] SKIP classified as ad/marketing")
                    if settings.dry_run_mark_seen:
                        dedup.mark_seen(item.url)
                    continue

                if _ai_output_is_bad(ai_text):
                    print("[AI] first response looks bad, retrying once...")
                    ai_text = enhancer.enhance(ai_input)

                if _ai_output_is_bad(ai_text):
                    raise ValueError("AI output failed quality gate")

                text = _append_cta(
                    ai_text.strip(),
                    settings.channel_cta_text,
                    settings.channel_cta_url,
                )
            else:
                text = channel_fallback

            photo_bytes = await _prepare_media_photo(item)

            if settings.dry_run:
                print(f"\n--- DRY RUN AI POST ---\n{text}\n")
                if photo_bytes:
                    print("--- DRY RUN MEDIA ---\nphoto prepared with branding\n")
                if settings.dry_run_mark_seen:
                    dedup.mark_seen(item.url)
                continue

            if photo_bytes:
                await tg.send_photo(settings.telegram_chat_id, photo_bytes, text)
            else:
                await tg.send_message(settings.telegram_chat_id, text)

            dedup.mark_seen(item.url)
            sent += 1

        except Exception as e:
            print(f"[AI/FALLBACK] {type(e).__name__}: {e}")

            photo_bytes = await _prepare_media_photo(item)

            if settings.dry_run:
                print(f"\n--- DRY RUN FALLBACK POST ---\n{channel_fallback}\n")
                if photo_bytes:
                    print("--- DRY RUN MEDIA ---\nphoto prepared with branding\n")
                if settings.dry_run_mark_seen:
                    dedup.mark_seen(item.url)
                continue

            if photo_bytes:
                await tg.send_photo(settings.telegram_chat_id, photo_bytes, channel_fallback)
            else:
                await tg.send_message(settings.telegram_chat_id, channel_fallback)

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
                sent = await run_once(
                    tg=tg,
                    settings=settings,
                    dedup=dedup,
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
