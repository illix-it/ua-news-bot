from __future__ import annotations

from datetime import datetime
from typing import Any

import feedparser
import httpx

from ua_news_bot.models import NewsItem, Source
from ua_news_bot.text_utils import clean_text

# Public aggregate RSS feed (mixed categories)
SUSPILNE_RSS_URL = "https://suspilne.media/rss/ukrnet.rss"


def _parse_published(entry: dict[str, Any]) -> datetime | None:
    """
    Parse publication datetime from RSS entry.

    feedparser provides `published_parsed` as time.struct_time
    or it may be missing.
    """
    parsed = entry.get("published_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6])


class SuspilneSource:
    """
    Suspilne news source (RSS).

    Note:
    - This feed is an aggregate RSS (ukrnet), not a single rubric.
    - Categories may include politics, war, sports, culture, etc.
    """

    name = "Суспільне"

    async def fetch_latest(self, limit: int = 20) -> list[NewsItem]:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
        ) as client:
            resp = await client.get(SUSPILNE_RSS_URL)
            resp.raise_for_status()

        feed = feedparser.parse(resp.content)

        items: list[NewsItem] = []
        for entry in feed.entries[:limit]:
            title = (entry.get("title") or "").strip()
            url = (entry.get("link") or "").strip()

            if not title or not url:
                continue

            raw_summary = entry.get("summary") or entry.get("description") or ""
            summary = clean_text(raw_summary) if raw_summary else None

            items.append(
                NewsItem(
                    source=Source.SUSPILNE,
                    title=title,
                    url=url,
                    published_at=_parse_published(entry),
                    summary=summary,
                )
            )

        return items
