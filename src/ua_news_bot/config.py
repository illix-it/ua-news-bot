from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    telegram_bot_token: str
    telegram_chat_id: str

    # Safety switches
    max_posts_per_run: int = 1
    dry_run: bool = True
    ai_enabled: bool = False

    # Polling
    poll_interval_seconds: int = 60

    # Warm start (one-time)
    init_skip_existing: bool = False
    init_post_latest: bool = False

    # Dedup (dev/testing)
    dedup_db_path: str = "data/seen.sqlite3"
    reset_dedup_on_start: bool = False
    dry_run_mark_seen: bool = True

    # AI / Gemini
    ai_provider: str = "gemini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    channel_language: str = "uk"


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
    """
    Loads settings from environment (.env supported for local dev).
    """
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

    # Dedup testing controls
    dedup_db_path = (os.getenv("DEDUP_DB_PATH") or "").strip() or "data/seen.sqlite3"
    reset_dedup_on_start = _parse_bool(os.getenv("RESET_DEDUP_ON_START"), default=False)
    dry_run_mark_seen = _parse_bool(os.getenv("DRY_RUN_MARK_SEEN"), default=True)

    ai_provider = os.getenv("AI_PROVIDER", "gemini").strip() or "gemini"
    gemini_api_key = (os.getenv("GEMINI_API_KEY") or "").strip() or None
    gemini_model = (os.getenv("GEMINI_MODEL") or "").strip() or "gemini-2.5-flash"
    channel_language = (os.getenv("CHANNEL_LANGUAGE") or "").strip() or "uk"

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
        gemini_model=gemini_model,
        channel_language=channel_language,
    )