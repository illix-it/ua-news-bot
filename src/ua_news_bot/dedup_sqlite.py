from __future__ import annotations

import sqlite3
from pathlib import Path
from time import time


class SQLiteSeenStore:
    """
    Persistent dedup store using SQLite.

    IMPORTANT:
    - `has(url)` checks if URL was seen.
    - `mark_seen(url)` stores URL as seen.
    We mark URLs as seen ONLY after we actually post (or intentionally skip).
    """

    def __init__(self, db_path: str = "data/seen.sqlite3") -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen (
                url TEXT PRIMARY KEY,
                seen_at INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()

    def has(self, url: str) -> bool:
        cur = self._conn.execute("SELECT 1 FROM seen WHERE url = ?", (url,))
        return cur.fetchone() is not None

    def mark_seen(self, url: str) -> None:
        # INSERT OR IGNORE makes it idempotent
        self._conn.execute(
            "INSERT OR IGNORE INTO seen (url, seen_at) VALUES (?, ?)",
            (url, int(time())),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
