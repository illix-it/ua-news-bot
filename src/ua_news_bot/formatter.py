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
    return _normalize(text).casefold()


def format_telegram_post(item: NewsItem) -> str:
    # ---- title ----
    title = _normalize(item.title)
    MAX_TITLE = 110

    if len(title) > MAX_TITLE:
        cut = title[:MAX_TITLE].rstrip()
        # Try to cut on a word boundary to avoid mid-word truncation
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0].rstrip()
        # Fallback: if cutting by space would make it too short, keep hard cut
        if len(cut) < 80:
            cut = title[: MAX_TITLE - 1].rstrip()
        title = cut + "…"

    # ---- summary ----
    summary = _normalize(item.summary or "")

    bullets: list[str] = []

    if not summary:
        essence = "Короткий опис у RSS відсутній."
    else:
        sentences = _split_sentences(summary)
        essence = " ".join(sentences[:2]).strip()

        # primary bullets from remaining sentences
        for s in sentences[2:]:
            if _is_valid_bullet(s):
                bullets.append(s)
            if len(bullets) == 3:
                break

        # fallback bullets from safe separators (; or •), never commas
        if len(bullets) < 3:
            for part in _SAFE_SPLIT_RE.split(summary):
                part = _normalize(part)
                if _is_valid_bullet(part) and part not in bullets:
                    bullets.append(part)
                if len(bullets) == 3:
                    break

        # remove bullets that duplicate essence (key-based, whitespace/case insensitive)
        essence_key = _norm_key(essence)
        bullets = [b for b in bullets if _norm_key(b) != essence_key]

    # If after dedupe there are no bullets, don't show bullet block at all.
    if bullets:
        # keep up to 3 bullets, but do not force-fill with repetitive fallbacks
        bullets = bullets[:3]
        bullets_block = "\n".join(f"• {b}" for b in bullets)
        post = f"{title}\n\n{essence}\n\n{bullets_block}\n\nДжерело: {item.source} {item.url}"
    else:
        post = f"{title}\n\n{essence}\n\nДжерело: {item.source} {item.url}"

    # ---- length control (trim only, never add facts) ----
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

    # If too short, add a single safe generic line (not a fact)
    if len(post) < 500:
        post = post.replace(
            "\n\nДжерело:",
            "\n\nДетальніше — за посиланням нижче.\n\nДжерело:",
            1,
        )

    return post
