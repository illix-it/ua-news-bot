from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

import httpx

from ua_news_bot.media.downloader import DEFAULT_USER_AGENT

ResolvedVideoKind = Literal["direct", "youtube", "unsupported"]


@dataclass(frozen=True)
class ResolvedVideo:
    kind: ResolvedVideoKind
    url: str


_YOUTUBE_EMBED_RE = re.compile(
    r"""<iframe[^>]+src=["'](https?://(?:www\.)?youtube\.com/embed/[^"']+)["']""",
    re.IGNORECASE,
)
_YOUTUBE_WATCH_RE = re.compile(
    r"""https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube-nocookie\.com/embed/)([A-Za-z0-9_-]{6,})""",
    re.IGNORECASE,
)
_DIRECT_VIDEO_RE = re.compile(
    r"""https?://[^\s"'<>]+?\.(?:mp4|m4v|mov)(?:\?[^\s"'<>]*)?""",
    re.IGNORECASE,
)
_VIDEO_TAG_RE = re.compile(
    r"""<video[^>]+src=["'](https?://[^"']+)["']""",
    re.IGNORECASE,
)
_SOURCE_TAG_RE = re.compile(
    r"""<source[^>]+src=["'](https?://[^"']+)["'][^>]*type=["']video/[^"']+["']""",
    re.IGNORECASE,
)
_OG_VIDEO_RE = re.compile(
    r"""<meta[^>]+property=["']og:video(?::url)?["'][^>]+content=["'](https?://[^"']+)["']""",
    re.IGNORECASE,
)
_TWITTER_PLAYER_RE = re.compile(
    r"""<meta[^>]+name=["']twitter:player["'][^>]+content=["'](https?://[^"']+)["']""",
    re.IGNORECASE,
)
_YOUTUBE_HOST_RE = re.compile(
    r"""(?:youtube\.com|youtu\.be|youtube-nocookie\.com)""",
    re.IGNORECASE,
)


def normalize_youtube_url(url: str) -> str:
    url = url.strip()

    if "youtube.com/embed/" in url:
        video_id = url.split("youtube.com/embed/", 1)[1].split("?", 1)[0].strip("/")
        return f"https://www.youtube.com/watch?v={video_id}"

    if "youtube-nocookie.com/embed/" in url:
        video_id = url.split("youtube-nocookie.com/embed/", 1)[1].split("?", 1)[0].strip("/")
        return f"https://www.youtube.com/watch?v={video_id}"

    if "youtu.be/" in url:
        video_id = url.split("youtu.be/", 1)[1].split("?", 1)[0].strip("/")
        return f"https://www.youtube.com/watch?v={video_id}"

    return url


def resolve_video_candidate(url: str) -> ResolvedVideo | None:
    candidate = (url or "").strip()
    if not candidate:
        return None

    lowered = candidate.lower()

    if lowered.endswith((".mp4", ".m4v", ".mov")) or ".mp4?" in lowered or ".m4v?" in lowered:
        return ResolvedVideo(kind="direct", url=candidate)

    if _YOUTUBE_HOST_RE.search(candidate):
        return ResolvedVideo(kind="youtube", url=normalize_youtube_url(candidate))

    return None


async def fetch_page_html(url: str, timeout: float = 30.0) -> str:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": url,
    }
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


def resolve_video_from_html(html: str) -> ResolvedVideo | None:
    if not html:
        return None

    for pattern in (
        _YOUTUBE_EMBED_RE,
        _OG_VIDEO_RE,
        _TWITTER_PLAYER_RE,
        _VIDEO_TAG_RE,
        _SOURCE_TAG_RE,
    ):
        match = pattern.search(html)
        if not match:
            continue
        found = match.group(1).strip()
        resolved = resolve_video_candidate(found)
        if resolved:
            return resolved

    direct_match = _DIRECT_VIDEO_RE.search(html)
    if direct_match:
        resolved = resolve_video_candidate(direct_match.group(0))
        if resolved:
            return resolved

    yt_match = _YOUTUBE_WATCH_RE.search(html)
    if yt_match:
        video_id = yt_match.group(1)
        return ResolvedVideo(kind="youtube", url=f"https://www.youtube.com/watch?v={video_id}")

    return None


async def resolve_video_for_item(item) -> ResolvedVideo | None:
    for candidate in getattr(item, "video_urls", ()) or ():
        resolved = resolve_video_candidate(candidate)
        if resolved:
            return resolved

    try:
        html = await fetch_page_html(item.url)
    except Exception as e:
        print(f"[MEDIA] article html fetch failed: {e}")
        return None

    return resolve_video_from_html(html)
