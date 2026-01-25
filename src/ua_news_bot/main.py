from ua_news_bot.config import load_settings


def main() -> None:
    settings = load_settings()
    print("ua-news-bot is ready")
    print(f"BOT token present: {bool(settings.telegram_bot_token)}")
    print(f"CHAT id present: {bool(settings.telegram_chat_id)}")


if __name__ == "__main__":
    main()
