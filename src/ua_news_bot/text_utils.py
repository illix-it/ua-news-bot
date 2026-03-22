from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_OBJECT_RE = re.compile(r"\[object Object\]", re.IGNORECASE)


def clean_text(value: str) -> str:
    """
    Cleans RSS/HTML-ish text:
    - unescape HTML entities
    - remove tags
    - remove junk placeholders like [object Object]
    - normalize whitespace
    """
    s = html.unescape(value)

    # Remove HTML tags
    s = _TAG_RE.sub(" ", s)

    # Remove known garbage fragments
    s = _OBJECT_RE.sub(" ", s)

    # Normalize strange invisible chars
    s = s.replace("\u200b", " ")
    s = s.replace("\ufeff", " ")
    s = s.replace("️", "")

    # Normalize quotes spacing a bit
    s = s.replace("“", '"').replace("”", '"').replace("„", '"')

    # Collapse whitespace
    s = _WS_RE.sub(" ", s).strip()

    return s
