from __future__ import annotations

import re

from ua_news_bot.models import NewsItem

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_SAFE_SPLIT_RE = re.compile(r"[;•]\s*")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _split_sentences(text: str) -> list[str]:
    return [_normalize(s) for s in _SENT_SPLIT_RE.split(text) if s.strip()]


def _is_valid_bullet(text: str) -> bool:
    # Avoid broken fragments / continuations
    if len(text) < 35:
        return False
    if text[0].islower():
        return False
    return True


def _norm_key(text: str) -> str:
    # Normalize for comparisons: whitespace + case
    return _normalize(text).casefold()


def _contains_normalized(haystack: str, needle: str) -> bool:
    """
    True if normalized needle is contained in normalized haystack.
    Used to avoid bullets that repeat essence or previous bullets.
    """
    n = _norm_key(needle)
    if not n:
        return False
    return n in _norm_key(haystack)


def format_telegram_post(item: NewsItem) -> str:
    # ---- title ----
    title = _normalize(item.title)
    MAX_TITLE = 110
    if len(title) > MAX_TITLE:
        cut = title[:MAX_TITLE].rstrip()
        # cut on word boundary if possible
        if " " in cut:
            cut2 = cut.rsplit(" ", 1)[0].rstrip()
            if len(cut2) >= 80:
                cut = cut2
        title = cut + "…"

    # ---- summary ----
    summary = _normalize(item.summary or "")

    bullets: list[str] = []

    if not summary:
        # Important: no "детальніше" here to avoid duplicates later
        essence = "Короткий опис у RSS відсутній."
    else:
        sentences = _split_sentences(summary)
        essence = " ".join(sentences[:2]).strip()

        # primary bullets from remaining sentences
        for s in sentences[2:]:
            if not _is_valid_bullet(s):
                continue
            # avoid repeats of essence and earlier bullets
            if _contains_normalized(s, essence):
                continue
            if any(_contains_normalized(s, b) or _contains_normalized(b, s) for b in bullets):
                continue
            bullets.append(s)
            if len(bullets) == 3:
                break

        # fallback bullets from safe separators (; or •), never commas
        if len(bullets) < 3:
            for part in _SAFE_SPLIT_RE.split(summary):
                part = _normalize(part)
                if not _is_valid_bullet(part):
                    continue
                if _contains_normalized(part, essence):
                    continue
                if any(
                    _contains_normalized(part, b) or _contains_normalized(b, part) for b in bullets
                ):
                    continue
                bullets.append(part)
                if len(bullets) == 3:
                    break

        # final: remove exact duplicates of essence (case/space-insensitive)
        essence_key = _norm_key(essence)
        bullets = [b for b in bullets if _norm_key(b) != essence_key]

    # Build post
    if bullets:
        bullets = bullets[:3]
        bullets_block = "\n".join(f"• {b}" for b in bullets)
        post = f"{title}\n\n{essence}\n\n{bullets_block}\n\nДжерело: {item.source} {item.url}"
    else:
        post = f"{title}\n\n{essence}\n\nДжерело: {item.source} {item.url}"

    # If too long: trim essence only (never add facts)
    if len(post) > 900 and len(essence) > 100:
        excess = len(post) - 900
        essence_trim = essence[: max(100, len(essence) - excess)].rstrip() + "…"
        if bullets:
            bullets_block = "\n".join(f"• {b}" for b in bullets)
            post = (
                f"{title}\n\n{essence_trim}\n\n{bullets_block}\n\nДжерело: {item.source} {item.url}"
            )
        else:
            post = f"{title}\n\n{essence_trim}\n\nДжерело: {item.source} {item.url}"

    # If too short: add a single safe generic line once
    if len(post) < 500:
        post = post.replace(
            "\n\nДжерело:",
            "\n\nДетальніше — за посиланням нижче.\n\nДжерело:",
            1,
        )

    return post
