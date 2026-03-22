from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import feedparser
import httpx

from ua_news_bot.models import NewsItem, Source
from ua_news_bot.text_utils import clean_text

SUSPILNE_RSS_URL = "https://suspilne.media/rss/ukrnet.rss"
_IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.IGNORECASE)


def _parse_published(entry: dict[str, Any]) -> datetime | None:
    parsed = entry.get("published_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6])


def _extract_image_urls(entry: Any) -> tuple[str, ...]:
    urls: list[str] = []

    media_content = entry.get("media_content") or []
    for item in media_content:
        url = (item.get("url") or "").strip()
        media_type = (item.get("type") or "").lower()
        if url and media_type.startswith("image/"):
            urls.append(url)

    links = entry.get("links") or []
    for link in links:
        url = (link.get("href") or "").strip()
        media_type = (link.get("type") or "").lower()
        rel = (link.get("rel") or "").lower()
        if url and media_type.startswith("image/"):
            urls.append(url)
        elif url and rel == "enclosure" and media_type.startswith("image/"):
            urls.append(url)

    raw_summary = entry.get("summary") or entry.get("description") or ""
    for match in _IMG_RE.findall(raw_summary):
        url = match.strip()
        if url:
            urls.append(url)

    unique: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            unique.append(url)
            seen.add(url)

    return tuple(unique)


class SuspilneSource:
    name = "Суспільне"

    async def fetch_latest(self, limit: int = 20) -> list[NewsItem]:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(SUSPILNE_RSS_URL)
            resp.raise_for_status()

        feed = feedparser.parse(resp.content)

        items: list[NewsItem] = []
        for entry in feed.entries[:limit]:
            title = clean_text(entry.get("title") or "")
            url = (entry.get("link") or "").strip()

            if not title or not url:
                continue

            raw_summary = entry.get("summary") or entry.get("description") or ""
            summary = clean_text(raw_summary) if raw_summary else None
            image_urls = _extract_image_urls(entry)

            items.append(
                NewsItem(
                    source=Source.SUSPILNE,
                    title=title,
                    url=url,
                    published_at=_parse_published(entry),
                    summary=summary,
                    image_urls=image_urls,
                    video_urls=(),
                )
            )

        return items
