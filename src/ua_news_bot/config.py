import os

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    telegram_bot_token: str
    telegram_chat_id: str


def load_settings() -> Settings:
    """
    Loads settings from environment (.env is supported for local dev).

    Fail-fast: raises ValueError if required settings are missing.
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

    return Settings(telegram_bot_token=token, telegram_chat_id=chat_id)
