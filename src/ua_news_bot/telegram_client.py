from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import httpx


class TelegramAPIError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self, token: str) -> None:
        self._base_url = f"https://api.telegram.org/bot{token}"

    async def send_message(self, chat_id: str, text: str) -> None:
        url = f"{self._base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()

        if not resp.is_success:
            raise TelegramAPIError(f"HTTP {resp.status_code}: {data}")

        if not data.get("ok", False):
            raise TelegramAPIError(f"Telegram API error: {data}")

    async def send_photo(self, chat_id: str, photo_bytes: bytes, caption: str) -> None:
        url = f"{self._base_url}/sendPhoto"

        files = {
            "photo": ("image.jpg", BytesIO(photo_bytes), "image/jpeg"),
        }
        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "HTML",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, data=data, files=files)
            payload = resp.json()

        if not resp.is_success:
            raise TelegramAPIError(f"HTTP {resp.status_code}: {payload}")

        if not payload.get("ok", False):
            raise TelegramAPIError(f"Telegram API error: {payload}")

    async def send_media_group(
        self,
        chat_id: str,
        images: list[bytes],
        caption: str,
    ) -> None:
        if not images:
            raise ValueError("images must not be empty")

        url = f"{self._base_url}/sendMediaGroup"

        media = []
        files: dict[str, tuple[str, BytesIO, str]] = {}

        for idx, image_bytes in enumerate(images):
            attach_name = f"photo{idx}"
            media_item = {
                "type": "photo",
                "media": f"attach://{attach_name}",
            }
            if idx == 0 and caption:
                media_item["caption"] = caption
                media_item["parse_mode"] = "HTML"

            media.append(media_item)
            files[attach_name] = (
                f"{attach_name}.jpg",
                BytesIO(image_bytes),
                "image/jpeg",
            )

        data = {
            "chat_id": chat_id,
            "media": json.dumps(media, ensure_ascii=False),
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, data=data, files=files)
            payload = resp.json()

        if not resp.is_success:
            raise TelegramAPIError(f"HTTP {resp.status_code}: {payload}")

        if not payload.get("ok", False):
            raise TelegramAPIError(f"Telegram API error: {payload}")

    async def send_video(self, chat_id: str, video_path: str, caption: str) -> None:
        url = f"{self._base_url}/sendVideo"

        with open(video_path, "rb") as f:
            files = {
                "video": (Path(video_path).name, f, "video/mp4"),
            }
            data = {
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "HTML",
                "supports_streaming": "true",
            }

            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(url, data=data, files=files)
                payload = resp.json()

        if not resp.is_success:
            raise TelegramAPIError(f"HTTP {resp.status_code}: {payload}")

        if not payload.get("ok", False):
            raise TelegramAPIError(f"Telegram API error: {payload}")
