from __future__ import annotations

import asyncio
import html
import re
import tempfile
from pathlib import Path

from ua_news_bot.aggregator import fetch_all_latest
from ua_news_bot.config import load_settings
from ua_news_bot.dedup_sqlite import SQLiteSeenStore
from ua_news_bot.formatter import format_telegram_post
from ua_news_bot.media.downloader import download_bytes, download_image_bytes
from ua_news_bot.media.image_editor import add_branding_to_image
from ua_news_bot.media.video_editor import add_branding_to_video_file
from ua_news_bot.media.video_resolver import resolve_video_for_item
from ua_news_bot.media.ytdlp_downloader import download_video_with_ytdlp
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


def _append_video_source_text(text: str, video_source_text: str) -> str:
    if not video_source_text:
        return text
    return f"{text}\n\n{video_source_text}"


def _remove_source_line(text: str) -> str:
    return _SOURCE_LINE_RE.sub("", text).strip()


def _split_media_caption_and_remainder(text: str, limit: int) -> tuple[str, str | None]:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned, None

    cut = cleaned[:limit]
    breakpoints = [
        cut.rfind("\n\n"),
        cut.rfind("\n"),
        cut.rfind(". "),
        cut.rfind("! "),
        cut.rfind("? "),
        cut.rfind(" "),
    ]
    split_at = max(breakpoints)

    if split_at < max(150, limit // 3):
        split_at = limit

    caption = cleaned[:split_at].rstrip()
    remainder = cleaned[split_at:].lstrip()

    if remainder and not caption.endswith(("…", ".", "!", "?", "”", '"', "»")):
        caption = caption.rstrip() + "…"

    return caption, (remainder or None)


def _media_log(settings, message: str) -> None:
    if settings.media_debug:
        print(message)


async def _send_media_with_safe_caption(
    *,
    tg: TelegramClient,
    chat_id: str,
    media_kind: str,
    media_payload,
    text: str,
    caption_limit: int,
) -> None:
    caption, remainder = _split_media_caption_and_remainder(text, caption_limit)

    if media_kind == "photo":
        await tg.send_photo(chat_id, media_payload, caption)
    elif media_kind == "album":
        await tg.send_media_group(chat_id, media_payload, caption)
    elif media_kind == "video":
        await tg.send_video(chat_id, media_payload, caption)
    else:
        raise ValueError(f"Unsupported media_kind: {media_kind}")

    if remainder:
        await tg.send_message(chat_id, remainder)


async def _prepare_media_photos(item, settings) -> list[bytes]:
    if not item.image_urls:
        return []

    prepared: list[bytes] = []
    for image_url in item.image_urls[: settings.telegram_max_media_images]:
        try:
            content = await download_image_bytes(image_url, referer=item.url)
            branded = add_branding_to_image(
                image_bytes=content,
                watermark_text=settings.watermark_text,
                logo_path=settings.watermark_logo_path,
                logo_scale=settings.watermark_image_logo_scale,
                text_scale=settings.watermark_image_text_scale,
            )
            prepared.append(branded.getvalue())
        except Exception as e:
            _media_log(settings, f"[MEDIA] image prepare failed for {image_url}: {e}")

    return prepared


async def _brand_video_file(input_video_path: str, settings) -> str:
    return await add_branding_to_video_file(
        input_video_path=input_video_path,
        watermark_text=settings.watermark_text,
        logo_path=settings.watermark_logo_path,
        logo_scale=settings.watermark_video_logo_scale,
        text_scale=settings.watermark_video_text_scale,
        ffmpeg_bin=settings.ffmpeg_bin,
        ffprobe_bin=settings.ffprobe_bin,
    )


async def _prepare_direct_video_from_url(video_url: str, referer: str, settings) -> str | None:
    temp_input_path: str | None = None
    branded_path: str | None = None

    try:
        content, content_type = await download_bytes(video_url, referer=referer, timeout=120.0)
        if not content_type.startswith("video/"):
            _media_log(settings, f"[MEDIA] direct video skipped: content-type={content_type}")
            return None

        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp_input.write(content)
        temp_input.close()
        temp_input_path = temp_input.name

        branded_path = await _brand_video_file(temp_input_path, settings)
        return branded_path
    except Exception as e:
        _media_log(settings, f"[MEDIA] direct video prepare failed: {e}")
        if branded_path:
            Path(branded_path).unlink(missing_ok=True)
        return None
    finally:
        if temp_input_path:
            Path(temp_input_path).unlink(missing_ok=True)


async def _prepare_ytdlp_video(video_url: str, settings) -> str | None:
    if not settings.ytdlp_enabled:
        return None

    temp_downloaded: str | None = None
    branded_path: str | None = None

    try:
        temp_downloaded = await download_video_with_ytdlp(
            video_url,
            ytdlp_bin=settings.ytdlp_bin,
        )
        branded_path = await _brand_video_file(temp_downloaded, settings)
        return branded_path
    except Exception as e:
        _media_log(settings, f"[MEDIA] yt-dlp video prepare failed: {e}")
        if branded_path:
            Path(branded_path).unlink(missing_ok=True)
        return None
    finally:
        if temp_downloaded:
            Path(temp_downloaded).unlink(missing_ok=True)


async def _prepare_media_video(item, settings) -> str | None:
    resolved = await resolve_video_for_item(item)
    if not resolved:
        return None

    _media_log(settings, f"[MEDIA] resolved video kind={resolved.kind} url={resolved.url}")

    if resolved.kind == "direct":
        return await _prepare_direct_video_from_url(resolved.url, item.url, settings)

    if resolved.kind == "youtube":
        return await _prepare_ytdlp_video(resolved.url, settings)

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
        rss_debug_post = _append_cta(
            rss_post,
            settings.channel_cta_text,
            settings.channel_cta_url,
        )

        branded_video_path: str | None = None

        try:
            if settings.dry_run:
                print(f"\n--- DRY RUN RSS POST ---\n{rss_debug_post}\n")
                if settings.media_debug and item.image_urls:
                    print(
                        f"--- DRY RUN IMAGE URLS ---\n{list(item.image_urls[: settings.telegram_max_media_images])}\n"
                    )
                if settings.media_debug and item.video_urls:
                    print(f"--- DRY RUN VIDEO URL ---\n{item.video_urls[0]}\n")

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

                text = ai_text.strip()
            else:
                text = _remove_source_line(rss_post)

            photo_bytes_list = await _prepare_media_photos(item, settings)
            if not photo_bytes_list:
                branded_video_path = await _prepare_media_video(item, settings)

            if branded_video_path:
                text = _append_video_source_text(text, settings.video_source_text)

            text = _append_cta(
                text,
                settings.channel_cta_text,
                settings.channel_cta_url,
            )

            if settings.dry_run:
                print(f"\n--- DRY RUN AI POST ---\n{text}\n")
                if len(photo_bytes_list) > 1:
                    if settings.media_debug:
                        cap, rest = _split_media_caption_and_remainder(
                            text,
                            settings.telegram_media_caption_limit,
                        )
                        print(
                            "--- DRY RUN MEDIA ---\n"
                            f"album prepared with branding ({len(photo_bytes_list)} images)\n"
                            f"caption_len={len(cap)} overflow={'yes' if rest else 'no'}\n"
                        )
                    else:
                        print(
                            f"--- DRY RUN MEDIA ---\nalbum prepared with branding ({len(photo_bytes_list)} images)\n"
                        )
                elif len(photo_bytes_list) == 1:
                    if settings.media_debug:
                        cap, rest = _split_media_caption_and_remainder(
                            text,
                            settings.telegram_media_caption_limit,
                        )
                        print(
                            "--- DRY RUN MEDIA ---\n"
                            "photo prepared with branding\n"
                            f"caption_len={len(cap)} overflow={'yes' if rest else 'no'}\n"
                        )
                    else:
                        print("--- DRY RUN MEDIA ---\nphoto prepared with branding\n")
                elif branded_video_path:
                    if settings.media_debug:
                        cap, rest = _split_media_caption_and_remainder(
                            text,
                            settings.telegram_media_caption_limit,
                        )
                        print(
                            "--- DRY RUN MEDIA ---\n"
                            "video prepared with branding\n"
                            f"caption_len={len(cap)} overflow={'yes' if rest else 'no'}\n"
                        )
                    else:
                        print("--- DRY RUN MEDIA ---\nvideo prepared with branding\n")
                if settings.dry_run_mark_seen:
                    dedup.mark_seen(item.url)
                if branded_video_path:
                    Path(branded_video_path).unlink(missing_ok=True)
                continue

            if len(photo_bytes_list) > 1:
                await _send_media_with_safe_caption(
                    tg=tg,
                    chat_id=settings.telegram_chat_id,
                    media_kind="album",
                    media_payload=photo_bytes_list,
                    text=text,
                    caption_limit=settings.telegram_media_caption_limit,
                )
            elif len(photo_bytes_list) == 1:
                await _send_media_with_safe_caption(
                    tg=tg,
                    chat_id=settings.telegram_chat_id,
                    media_kind="photo",
                    media_payload=photo_bytes_list[0],
                    text=text,
                    caption_limit=settings.telegram_media_caption_limit,
                )
            elif branded_video_path:
                await _send_media_with_safe_caption(
                    tg=tg,
                    chat_id=settings.telegram_chat_id,
                    media_kind="video",
                    media_payload=branded_video_path,
                    text=text,
                    caption_limit=settings.telegram_media_caption_limit,
                )
            else:
                await tg.send_message(settings.telegram_chat_id, text)

            dedup.mark_seen(item.url)
            sent += 1

        except Exception as e:
            print(f"[AI/FALLBACK] {type(e).__name__}: {e}")

            photo_bytes_list = await _prepare_media_photos(item, settings)
            if not photo_bytes_list and branded_video_path is None:
                branded_video_path = await _prepare_media_video(item, settings)

            fallback_text = _remove_source_line(rss_post)
            if branded_video_path:
                fallback_text = _append_video_source_text(
                    fallback_text,
                    settings.video_source_text,
                )
            fallback_text = _append_cta(
                fallback_text,
                settings.channel_cta_text,
                settings.channel_cta_url,
            )

            if settings.dry_run:
                print(f"\n--- DRY RUN FALLBACK POST ---\n{fallback_text}\n")
                if len(photo_bytes_list) > 1:
                    if settings.media_debug:
                        cap, rest = _split_media_caption_and_remainder(
                            fallback_text,
                            settings.telegram_media_caption_limit,
                        )
                        print(
                            "--- DRY RUN MEDIA ---\n"
                            f"album prepared with branding ({len(photo_bytes_list)} images)\n"
                            f"caption_len={len(cap)} overflow={'yes' if rest else 'no'}\n"
                        )
                    else:
                        print(
                            f"--- DRY RUN MEDIA ---\nalbum prepared with branding ({len(photo_bytes_list)} images)\n"
                        )
                elif len(photo_bytes_list) == 1:
                    if settings.media_debug:
                        cap, rest = _split_media_caption_and_remainder(
                            fallback_text,
                            settings.telegram_media_caption_limit,
                        )
                        print(
                            "--- DRY RUN MEDIA ---\n"
                            "photo prepared with branding\n"
                            f"caption_len={len(cap)} overflow={'yes' if rest else 'no'}\n"
                        )
                    else:
                        print("--- DRY RUN MEDIA ---\nphoto prepared with branding\n")
                elif branded_video_path:
                    if settings.media_debug:
                        cap, rest = _split_media_caption_and_remainder(
                            fallback_text,
                            settings.telegram_media_caption_limit,
                        )
                        print(
                            "--- DRY RUN MEDIA ---\n"
                            "video prepared with branding\n"
                            f"caption_len={len(cap)} overflow={'yes' if rest else 'no'}\n"
                        )
                    else:
                        print("--- DRY RUN MEDIA ---\nvideo prepared with branding\n")
                if settings.dry_run_mark_seen:
                    dedup.mark_seen(item.url)
                if branded_video_path:
                    Path(branded_video_path).unlink(missing_ok=True)
                continue

            if len(photo_bytes_list) > 1:
                await _send_media_with_safe_caption(
                    tg=tg,
                    chat_id=settings.telegram_chat_id,
                    media_kind="album",
                    media_payload=photo_bytes_list,
                    text=fallback_text,
                    caption_limit=settings.telegram_media_caption_limit,
                )
            elif len(photo_bytes_list) == 1:
                await _send_media_with_safe_caption(
                    tg=tg,
                    chat_id=settings.telegram_chat_id,
                    media_kind="photo",
                    media_payload=photo_bytes_list[0],
                    text=fallback_text,
                    caption_limit=settings.telegram_media_caption_limit,
                )
            elif branded_video_path:
                await _send_media_with_safe_caption(
                    tg=tg,
                    chat_id=settings.telegram_chat_id,
                    media_kind="video",
                    media_payload=branded_video_path,
                    text=fallback_text,
                    caption_limit=settings.telegram_media_caption_limit,
                )
            else:
                await tg.send_message(settings.telegram_chat_id, fallback_text)

            dedup.mark_seen(item.url)
            sent += 1

        finally:
            if branded_video_path:
                Path(branded_video_path).unlink(missing_ok=True)

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
