"""
SQLite database for storing subscriptions and poller state.
"""

import sqlite3
import json
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._init()

    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    alert_type  TEXT NOT NULL,
                    country     TEXT NOT NULL DEFAULT '',
                    keyword     TEXT NOT NULL DEFAULT '',
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, alert_type, country, keyword)
                );

                CREATE TABLE IF NOT EXISTS poller_state (
                    key     TEXT PRIMARY KEY,
                    value   TEXT NOT NULL
                );
            """)

    # ── Subscriptions ─────────────────────────────────────────────────────────

    def add_subscription(self, user_id: int, alert_type: str, country: str, keyword: str):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO subscriptions (user_id, alert_type, country, keyword)
                VALUES (?, ?, ?, ?)
            """, (user_id, alert_type, country, keyword))

    def remove_subscription(self, user_id: int, alert_type: str):
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM subscriptions WHERE user_id = ? AND alert_type = ?",
                (user_id, alert_type),
            )

    def remove_all_subscriptions(self, user_id: int):
        with self._conn() as conn:
            conn.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))

    def get_subscriptions(self, user_id: int) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY alert_type",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_subscribers_for(self, alert_type: str) -> list[dict]:
        """Return all subscriptions of a given alert type."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM subscriptions WHERE alert_type = ?",
                (alert_type,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Poller state ──────────────────────────────────────────────────────────

    def get_state(self, key: str, default: Any = None) -> Any:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM poller_state WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return default
        return json.loads(row["value"])

    def set_state(self, key: str, value: Any):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO poller_state (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, json.dumps(value)))
