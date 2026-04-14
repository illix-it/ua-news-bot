from __future__ import annotations

import asyncio

from ua_news_bot.config import load_settings
from ua_news_bot.media.downloader import download_image_bytes
from ua_news_bot.media.image_editor import add_branding_to_image
from ua_news_bot.telegram_client import TelegramClient

TEST_IMAGE_URLS = [
    "https://cdn4.suspilne.media/images/60dfd0bb527c86c9.png",
    "https://cdn4.suspilne.media/images/0ffa3d2bc356e163.jpg",
    "https://cdn4.suspilne.media/images/c9d819764e17a8be.jpg",
]

REFERER_URL = "https://suspilne.media/"


async def main() -> None:
    settings = load_settings()
    tg = TelegramClient(settings.telegram_bot_token)

    prepared: list[bytes] = []

    for url in TEST_IMAGE_URLS:
        print(f"Downloading: {url}")
        content = await download_image_bytes(url, referer=REFERER_URL)
        branded = add_branding_to_image(
            image_bytes=content,
            watermark_text=settings.watermark_text,
            logo_path=settings.watermark_logo_path,
            logo_scale=settings.watermark_image_logo_scale,
            text_scale=settings.watermark_image_text_scale,
        )
        prepared.append(branded.getvalue())

    if not prepared:
        raise RuntimeError("No images prepared")

    caption = (
        "<b>Тест альбому Smart News</b>\n\n"
        "Перевірка відправки кількох зображень одним постом.\n\n"
        '<a href="https://t.me/smart_news_ua">📲 Підписатися на Smart News</a>'
    )

    print(f"Prepared images: {len(prepared)}")
    await tg.send_media_group(
        chat_id=settings.telegram_chat_id,
        images=prepared,
        caption=caption,
    )
    print("Album sent ✅")


if __name__ == "__main__":
    asyncio.run(main())
