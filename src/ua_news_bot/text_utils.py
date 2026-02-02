from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean_text(value: str) -> str:
    """
    Cleans RSS/HTML-ish text:
    - unescape HTML entities
    - remove tags
    - normalize whitespace
    """
    s = html.unescape(value)
    s = _TAG_RE.sub("", s)
    s = _WS_RE.sub(" ", s).strip()
    return s
