from __future__ import annotations

from datetime import datetime
from typing import Any

import feedparser
import httpx

from ua_news_bot.models import NewsItem, Source

SUSPILNE_RSS_URL = "https://suspilne.media/rss/ukrnet.rss"


def _parse_published(entry: dict[str, Any]) -> datetime | None:
    # feedparser may provide "published_parsed" as time.struct_time
    parsed = entry.get("published_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6])


async def fetch_latest(limit: int = 20) -> list[NewsItem]:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        resp = await client.get(SUSPILNE_RSS_URL)
        resp.raise_for_status()

    feed = feedparser.parse(resp.content)

    items: list[NewsItem] = []
    for entry in feed.entries[:limit]:
        title = (entry.get("title") or "").strip()
        url = (entry.get("link") or "").strip()

        if not title or not url:
            continue

        items.append(
            NewsItem(
                source=Source.SUSPILNE,
                title=title,
                url=url,
                published_at=_parse_published(entry),
            )
        )

    return items
