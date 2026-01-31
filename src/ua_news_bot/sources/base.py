from __future__ import annotations

from typing import Protocol

from ua_news_bot.models import NewsItem


class NewsSource(Protocol):
    name: str

    async def fetch_latest(self, limit: int = 20) -> list[NewsItem]:
        """Fetch latest items from this source."""
