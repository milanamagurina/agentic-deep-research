"""SQLite persistence: sessions, the audit event stream and graph snapshots.

Events are written as they happen (append-only). Swap-out point for Postgres/Neo4j later.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..models import ResearchSession
from ..observability.events import ResearchEvent

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, question TEXT, phase TEXT, synthetic INTEGER,
    status TEXT, started_at TEXT, updated_at TEXT, session_json TEXT);
CREATE TABLE IF NOT EXISTS events (session_id TEXT, seq INTEGER, ts TEXT, type TEXT, message TEXT, data_json TEXT,
    PRIMARY KEY (session_id, seq));
CREATE TABLE IF NOT EXISTS snapshots (session_id TEXT PRIMARY KEY, graph_json TEXT, report_json TEXT, report_md TEXT);
"""


class Repository:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.executescript(SCHEMA)

    def save_session(self, s: ResearchSession, status: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET phase=excluded.phase, "
            "status=COALESCE(excluded.status, sessions.status), updated_at=excluded.updated_at, session_json=excluded.session_json",
            (s.id, s.question, s.phase.value, int(s.synthetic), status, s.started_at.isoformat(), s.updated_at.isoformat(), s.model_dump_json()),
        )
        self.conn.commit()

    def append_event(self, session_id: str, e: ResearchEvent) -> None:
        self.conn.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?)",
                          (session_id, e.seq, e.ts.isoformat(), e.type.value, e.message, json.dumps(e.data, default=str)))
        self.conn.commit()

    def save_snapshot(self, session_id: str, graph: dict[str, Any], report_json: str, report_md: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?)",
                          (session_id, json.dumps(graph, default=str), report_json, report_md))
        self.conn.commit()

    def list_sessions(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT id, question, status, synthetic, updated_at FROM sessions ORDER BY updated_at DESC").fetchall()
        return [dict(zip(("id", "question", "status", "synthetic", "updated_at"), r)) for r in rows]

    def load(self, session_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT graph_json, report_json, report_md FROM snapshots WHERE session_id=?", (session_id,)).fetchone()
        if not row:
            return None
        events = self.conn.execute("SELECT seq, ts, type, message, data_json FROM events WHERE session_id=? ORDER BY seq", (session_id,)).fetchall()
        return {"graph": json.loads(row[0]), "report": json.loads(row[1]), "report_md": row[2],
                "events": [{"seq": e[0], "ts": e[1], "type": e[2], "message": e[3], "data": json.loads(e[4])} for e in events]}
