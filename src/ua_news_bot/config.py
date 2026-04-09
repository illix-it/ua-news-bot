from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    telegram_bot_token: str
    telegram_chat_id: str

    max_posts_per_run: int = 1
    dry_run: bool = True
    ai_enabled: bool = False

    poll_interval_seconds: int = 60

    init_skip_existing: bool = False
    init_post_latest: bool = False

    dedup_db_path: str = "data/seen.sqlite3"
    reset_dedup_on_start: bool = False
    dry_run_mark_seen: bool = True

    ai_provider: str = "gemini"
    gemini_api_key: str | None = None
    gemini_api_keys: str = ""
    gemini_model: str = "gemini-2.5-flash"
    channel_language: str = "uk"

    channel_cta_text: str = ""
    channel_cta_url: str = ""

    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"

    watermark_text: str = "Smart News UA"
    watermark_logo_path: str = "data/images/smart_news_ua_logo.png"

    ytdlp_enabled: bool = False
    ytdlp_bin: str = "yt-dlp"

    video_source_text: str = "🎥 Відео: Суспільне"


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    v = value.strip().casefold()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    return default


def load_settings() -> Settings:
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    missing: list[str] = []
    if not token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not chat_id:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    max_posts_raw = os.getenv("MAX_POSTS_PER_RUN", "").strip()
    max_posts = int(max_posts_raw) if max_posts_raw.isdigit() else 1
    if max_posts < 0:
        max_posts = 0

    poll_raw = os.getenv("POLL_INTERVAL_SECONDS", "").strip()
    poll_interval = int(poll_raw) if poll_raw.isdigit() else 60
    if poll_interval < 10:
        poll_interval = 10

    dry_run = _parse_bool(os.getenv("DRY_RUN"), default=True)
    ai_enabled = _parse_bool(os.getenv("AI_ENABLED"), default=False)

    init_skip_existing = _parse_bool(os.getenv("INIT_SKIP_EXISTING"), default=False)
    init_post_latest = _parse_bool(os.getenv("INIT_POST_LATEST"), default=False)

    dedup_db_path = (os.getenv("DEDUP_DB_PATH") or "").strip() or "data/seen.sqlite3"
    reset_dedup_on_start = _parse_bool(os.getenv("RESET_DEDUP_ON_START"), default=False)
    dry_run_mark_seen = _parse_bool(os.getenv("DRY_RUN_MARK_SEEN"), default=True)

    ai_provider = (os.getenv("AI_PROVIDER") or "gemini").strip() or "gemini"
    gemini_api_key = (os.getenv("GEMINI_API_KEY") or "").strip() or None
    gemini_api_keys = (os.getenv("GEMINI_API_KEYS") or "").strip()
    gemini_model = (os.getenv("GEMINI_MODEL") or "").strip() or "gemini-2.5-flash"
    channel_language = (os.getenv("CHANNEL_LANGUAGE") or "").strip() or "uk"

    channel_cta_text = (os.getenv("CHANNEL_CTA_TEXT") or "").strip()
    channel_cta_url = (os.getenv("CHANNEL_CTA_URL") or "").strip()

    ffmpeg_bin = (os.getenv("FFMPEG_BIN") or "").strip() or "ffmpeg"
    ffprobe_bin = (os.getenv("FFPROBE_BIN") or "").strip() or "ffprobe"

    watermark_text = (os.getenv("WATERMARK_TEXT") or "").strip() or "Smart News UA"
    watermark_logo_path = (
        os.getenv("WATERMARK_LOGO_PATH") or ""
    ).strip() or "data/images/smart_news_ua_logo.png"

    ytdlp_enabled = _parse_bool(os.getenv("YTDLP_ENABLED"), default=False)
    ytdlp_bin = (os.getenv("YTDLP_BIN") or "").strip() or "yt-dlp"

    video_source_text = (os.getenv("VIDEO_SOURCE_TEXT") or "").strip() or "🎥 Відео: Суспільне"

    return Settings(
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        max_posts_per_run=max_posts,
        dry_run=dry_run,
        ai_enabled=ai_enabled,
        poll_interval_seconds=poll_interval,
        init_skip_existing=init_skip_existing,
        init_post_latest=init_post_latest,
        dedup_db_path=dedup_db_path,
        reset_dedup_on_start=reset_dedup_on_start,
        dry_run_mark_seen=dry_run_mark_seen,
        ai_provider=ai_provider,
        gemini_api_key=gemini_api_key,
        gemini_api_keys=gemini_api_keys,
        gemini_model=gemini_model,
        channel_language=channel_language,
        channel_cta_text=channel_cta_text,
        channel_cta_url=channel_cta_url,
        ffmpeg_bin=ffmpeg_bin,
        ffprobe_bin=ffprobe_bin,
        watermark_text=watermark_text,
        watermark_logo_path=watermark_logo_path,
        ytdlp_enabled=ytdlp_enabled,
        ytdlp_bin=ytdlp_bin,
        video_source_text=video_source_text,
    )
