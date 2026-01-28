from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Source(StrEnum):
    SUSPILNE = "Суспільне"
    UKRINFORM = "Укрінформ"


@dataclass(frozen=True, slots=True)
class NewsItem:
    """
    Normalized representation of a news item from any source.
    This is *not* the final Telegram post yet.
    """

    source: Source
    title: str
    url: str
    published_at: datetime | None
