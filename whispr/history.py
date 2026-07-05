"""Dictation history stored in a local SQLite database."""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Entry:
    id: int
    ts: float
    text: str
    duration_s: float
    words: int


class History:
    def __init__(self, db_path: Path):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS entries ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "ts REAL NOT NULL,"
            "text TEXT NOT NULL,"
            "duration_s REAL NOT NULL,"
            "words INTEGER NOT NULL)"
        )
        self._conn.commit()

    def add(self, text: str, duration_s: float) -> int:
        words = len(text.split())
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO entries (ts, text, duration_s, words) VALUES (?, ?, ?, ?)",
                (time.time(), text, float(duration_s), words),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def recent(self, limit: int = 50, search: str | None = None) -> list[Entry]:
        query = "SELECT id, ts, text, duration_s, words FROM entries"
        args: list = []
        if search:
            query += " WHERE text LIKE ?"
            args.append(f"%{search}%")
        query += " ORDER BY id DESC LIMIT ?"
        args.append(int(limit))
        with self._lock:
            rows = self._conn.execute(query, args).fetchall()
        return [Entry(*row) for row in rows]

    def delete(self, entry_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            self._conn.commit()

    def clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM entries")
            self._conn.commit()

    def stats(self) -> dict:
        with self._lock:
            entries, words, duration = self._conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(words), 0), COALESCE(SUM(duration_s), 0) FROM entries"
            ).fetchone()
        avg_wpm = (words / duration * 60.0) if duration > 0 else 0.0
        return {"entries": entries, "words": words, "duration_s": duration, "avg_wpm": avg_wpm}

    def close(self) -> None:
        with self._lock:
            self._conn.close()
