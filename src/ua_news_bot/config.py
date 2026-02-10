import os

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    telegram_bot_token: str
    telegram_chat_id: str

    # Safety switches
    max_posts_per_run: int = 5
    dry_run: bool = True
    ai_enabled: bool = False

    poll_interval_seconds: int = 60

    init_skip_existing: bool = True
    init_post_latest: bool = True


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
    Loads settings from environment (.env is supported for local dev).

    Fail-fast for required Telegram settings.
    Safety switches have defaults.
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
    max_posts = int(max_posts_raw) if max_posts_raw.isdigit() else 5
    if max_posts < 0:
        max_posts = 0

    dry_run = _parse_bool(os.getenv("DRY_RUN"), default=True)
    ai_enabled = _parse_bool(os.getenv("AI_ENABLED"), default=False)

    poll_raw = os.getenv("POLL_INTERVAL_SECONDS", "").strip()
    poll_interval = int(poll_raw) if poll_raw.isdigit() else 60
    if poll_interval < 10:
        poll_interval = 10

    init_skip_existing = _parse_bool(os.getenv("INIT_SKIP_EXISTING"), default=True)
    init_post_latest = _parse_bool(os.getenv("INIT_POST_LATEST"), default=True)

    return Settings(
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        max_posts_per_run=max_posts,
        dry_run=dry_run,
        ai_enabled=ai_enabled,
        poll_interval_seconds=poll_interval,
        init_skip_existing=init_skip_existing,
        init_post_latest=init_post_latest,
    )
