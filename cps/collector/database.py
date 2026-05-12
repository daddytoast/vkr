"""SQLite persistence layer for presence snapshots."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class Database:
    def __init__(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts          TEXT    NOT NULL,
                    client_count INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS clients (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
                    mac_address TEXT    NOT NULL,
                    ip_address  TEXT    NOT NULL,
                    hostname    TEXT    NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON snapshots(ts);
                """
            )

    def record_snapshot(self, ts: datetime, count: int, leases) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO snapshots (ts, client_count) VALUES (?, ?)",
                (ts.isoformat(), count),
            )
            snapshot_id = cur.lastrowid
            conn.executemany(
                "INSERT INTO clients (snapshot_id, mac_address, ip_address, hostname) VALUES (?, ?, ?, ?)",
                [(snapshot_id, l.mac_address, l.ip_address, l.hostname) for l in leases],
            )
        return snapshot_id

    def get_latest_snapshot(self) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM snapshots ORDER BY ts DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            clients = conn.execute(
                "SELECT mac_address, ip_address, hostname FROM clients WHERE snapshot_id = ?",
                (row["id"],),
            ).fetchall()
            return {
                "ts": row["ts"],
                "client_count": row["client_count"],
                "clients": [dict(c) for c in clients],
            }

    def get_history(self, hours: int = 24) -> list[dict]:
        """Return per-minute aggregated counts for the last N hours."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT strftime('%Y-%m-%dT%H:%M:00Z', ts) AS minute,
                       MAX(client_count) AS client_count
                FROM snapshots
                WHERE ts >= datetime('now', ?)
                GROUP BY minute
                ORDER BY minute ASC
                """,
                (f"-{hours} hours",),
            ).fetchall()
        return [dict(r) for r in rows]