from __future__ import annotations


class SeenStore:
    """
    In-memory dedup store (v1).
    Keeps URLs seen during the current process lifetime.

    Later (v2): replace with Redis/DB + TTL to dedupe between runs.
    """

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def is_new(self, key: str) -> bool:
        if key in self._seen:
            return False
        self._seen.add(key)
        return True
