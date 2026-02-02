from __future__ import annotations

import re

from ua_news_bot.models import NewsItem

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT_RE.split(text) if p.strip()]
    return parts


def format_telegram_post(item: NewsItem) -> str:
    """
    Builds a UA post strictly from source-provided fields (title + RSS summary).
    No new facts. No speculation.

    Format:
    - Title (<=110 chars)
    - 1–2 sentences: essence
    - 3 bullets: key facts (taken from summary sentences/fragments)
    - Source line with link
    Target length: 500–900 chars (best-effort in v1).
    """
    title = item.title.strip()
    if len(title) > 110:
        title = title[:107].rstrip() + "…"

    summary = (item.summary or "").strip()

    # If no summary: we can't safely invent facts.
    if not summary:
        essence = "Короткий опис у RSS відсутній. Детальніше — за посиланням."
        bullets = [
            "Подробиці — на сайті джерела.",
            "Офіційний матеріал за посиланням нижче.",
            "Слідкуємо за оновленнями.",
        ]
    else:
        sentences = _split_sentences(summary)

        essence_sentences = sentences[:2]
        essence = " ".join(essence_sentences).strip()

        bullet_candidates = sentences[2:5]
        if len(bullet_candidates) < 3:
            # fallback: split by semicolons/commas without adding new info
            fragments = [f.strip() for f in re.split(r"[;•]\s*|,\s+", summary) if f.strip()]
            bullet_candidates = (sentences[1:2] + fragments)[:3]

        bullets = bullet_candidates[:3]
        # Ensure bullets are non-empty and not too long
        bullets = [b[:220].rstrip() + ("…" if len(b) > 220 else "") for b in bullets]
        while len(bullets) < 3:
            bullets.append("Детальніше — за посиланням.")

    post = (
        f"{title}\n\n"
        f"{essence}\n\n"
        f"• {bullets[0]}\n"
        f"• {bullets[1]}\n"
        f"• {bullets[2]}\n\n"
        f"Джерело: {item.source} {item.url}"
    )

    # Best-effort length control (we won't fabricate; we only trim)
    if len(post) > 900:
        # trim essence first
        excess = len(post) - 900
        if excess > 0 and len(essence) > 80:
            new_len = max(80, len(essence) - excess)
            essence_trim = essence[:new_len].rstrip() + "…"
            post = post.replace(essence, essence_trim, 1)

    # If too short, add safe generic line (not a new fact)
    if len(post) < 500:
        post = post.replace(
            "\n\nДжерело:",
            "\n\nДетальніше — за посиланням нижче.\n\nДжерело:",
            1,
        )

    return post
