"""SQLite persistence for Copilot call traces (not the Ratti demo DB)."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DEFAULT_TRACES_DB = os.path.join(_BASE_DIR, "data", "traces.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    query TEXT NOT NULL,
    response_language TEXT,
    intent TEXT,
    confidence REAL,
    final_answer TEXT,
    total_latency_ms REAL,
    total_prompt_tokens INTEGER DEFAULT 0,
    total_completion_tokens INTEGER DEFAULT 0,
    error TEXT,
    agent_config_id TEXT
);

CREATE TABLE IF NOT EXISTS trace_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    step_num INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    tool_called TEXT NOT NULL,
    tool_latency_ms REAL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    detail TEXT,
    FOREIGN KEY (trace_id) REFERENCES traces(id)
);

CREATE INDEX IF NOT EXISTS idx_trace_steps_trace_id ON trace_steps(trace_id);
CREATE INDEX IF NOT EXISTS idx_traces_timestamp ON traces(timestamp);
CREATE INDEX IF NOT EXISTS idx_traces_agent_config_id ON traces(agent_config_id);
"""

_lock = threading.Lock()
_store: TraceStore | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class TraceStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.getenv("TRACES_DB_PATH", DEFAULT_TRACES_DB)
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            cols = {
                r["name"]
                for r in conn.execute("PRAGMA table_info(traces)").fetchall()
            }
            if "agent_config_id" not in cols:
                conn.execute("ALTER TABLE traces ADD COLUMN agent_config_id TEXT")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_traces_agent_config_id ON traces(agent_config_id)"
            )

    def create_trace(
        self,
        trace_id: str,
        query: str,
        response_language: str | None = None,
        agent_config_id: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO traces (id, timestamp, query, response_language, agent_config_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (trace_id, _utc_now(), query, response_language, agent_config_id),
            )

    def add_step(
        self,
        trace_id: str,
        step_num: int,
        tool_called: str,
        tool_latency_ms: float | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO trace_steps (
                    trace_id, step_num, timestamp, tool_called,
                    tool_latency_ms, prompt_tokens, completion_tokens, detail
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_id,
                    step_num,
                    _utc_now(),
                    tool_called,
                    tool_latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    json.dumps(detail, ensure_ascii=False) if detail else None,
                ),
            )

    def finish_trace(
        self,
        trace_id: str,
        *,
        final_answer: str | None = None,
        confidence: float | None = None,
        intent: str | None = None,
        total_latency_ms: float | None = None,
        error: str | None = None,
    ) -> None:
        with self._connect() as conn:
            totals = conn.execute(
                """
                SELECT
                    COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) AS completion_tokens
                FROM trace_steps
                WHERE trace_id = ?
                """,
                (trace_id,),
            ).fetchone()
            conn.execute(
                """
                UPDATE traces
                SET final_answer = ?,
                    confidence = ?,
                    intent = ?,
                    total_latency_ms = ?,
                    total_prompt_tokens = ?,
                    total_completion_tokens = ?,
                    error = ?
                WHERE id = ?
                """,
                (
                    final_answer,
                    confidence,
                    intent,
                    total_latency_ms,
                    int(totals["prompt_tokens"] or 0),
                    int(totals["completion_tokens"] or 0),
                    error,
                    trace_id,
                ),
            )

    def list_traces(
        self,
        limit: int = 50,
        agent_config_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if agent_config_id:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM traces
                    WHERE agent_config_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (agent_config_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM traces
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM traces WHERE id = ?", (trace_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_steps(self, trace_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM trace_steps
                WHERE trace_id = ?
                ORDER BY step_num ASC
                """,
                (trace_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_recent_steps(self, limit: int = 100) -> list[dict[str, Any]]:
        """Flat join for dataframe: one row per step with parent query metadata."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    s.id AS step_id,
                    s.trace_id,
                    s.timestamp AS step_timestamp,
                    t.timestamp AS trace_timestamp,
                    t.query,
                    s.step_num,
                    s.tool_called,
                    s.tool_latency_ms,
                    s.prompt_tokens,
                    s.completion_tokens,
                    (COALESCE(s.prompt_tokens, 0) + COALESCE(s.completion_tokens, 0))
                        AS total_tokens,
                    t.confidence,
                    t.intent,
                    t.final_answer,
                    t.total_latency_ms,
                    t.response_language,
                    t.error
                FROM trace_steps s
                JOIN traces t ON t.id = s.trace_id
                ORDER BY s.timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_all(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM trace_steps")
            conn.execute("DELETE FROM traces")


def get_store(db_path: str | None = None) -> TraceStore:
    global _store
    with _lock:
        if _store is None or (db_path and db_path != _store.db_path):
            _store = TraceStore(db_path)
        return _store
