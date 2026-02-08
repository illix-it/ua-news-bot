from __future__ import annotations

import sqlite3
from pathlib import Path
from time import time


class SQLiteSeenStore:
    """
    Persistent dedup store using SQLite.

    Stores seen URLs forever (v1). This prevents reposts across restarts.
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

    def is_new(self, url: str) -> bool:
        cur = self._conn.execute("SELECT 1 FROM seen WHERE url = ?", (url,))
        if cur.fetchone() is not None:
            return False

        self._conn.execute(
            "INSERT INTO seen (url, seen_at) VALUES (?, ?)",
            (url, int(time())),
        )
        self._conn.commit()
        return True

    def close(self) -> None:
        self._conn.close()
