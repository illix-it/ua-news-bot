import asyncio

from ua_news_bot.config import load_settings
from ua_news_bot.telegram_client import TelegramClient


def build_test_message() -> str:
    return (
        "Test message from ua-news-bot ✅\n\nIf you see this in the channel, Bot API posting works."
    )


async def run() -> None:
    settings = load_settings()
    tg = TelegramClient(settings.telegram_bot_token)
    await tg.send_message(settings.telegram_chat_id, build_test_message())
    print("Message sent ✅")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
