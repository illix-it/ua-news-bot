from __future__ import annotations

import httpx


class TelegramAPIError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self, token: str) -> None:
        self._base_url = f"https://api.telegram.org/bot{token}"

    async def send_message(self, chat_id: str, text: str) -> None:
        """
        Sends a text message via Telegram Bot API.

        Raises TelegramAPIError on non-OK responses from Telegram.
        """
        url = f"{self._base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()

        if not resp.is_success:
            raise TelegramAPIError(f"HTTP {resp.status_code}: {data}")

        if not data.get("ok", False):
            raise TelegramAPIError(f"Telegram API error: {data}")
