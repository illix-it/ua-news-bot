from __future__ import annotations

from ua_news_bot.dedup import SeenStore
from ua_news_bot.models import NewsItem
from ua_news_bot.sources.base import NewsSource


async def fetch_all_latest(
    sources: list[NewsSource],
    *,
    per_source_limit: int = 30,
    dedup: SeenStore | None = None,
) -> list[NewsItem]:
    """
    Fetches latest items from all sources, optionally deduplicating by URL.
    No filtering by topic/category.
    """
    all_items: list[NewsItem] = []
    for src in sources:
        items = await src.fetch_latest(limit=per_source_limit)
        all_items.extend(items)

    if dedup is None:
        return all_items

    unique: list[NewsItem] = []
    for item in all_items:
        if dedup.is_new(item.url):
            unique.append(item)
    return unique
