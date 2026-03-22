from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Source(StrEnum):
    SUSPILNE = "Суспільне"


@dataclass(frozen=True)
class NewsItem:
    source: Source
    title: str
    url: str
    published_at: datetime | None = None
    summary: str | None = None
    image_urls: tuple[str, ...] = ()
    video_urls: tuple[str, ...] = ()
