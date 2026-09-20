import sqlite3
from datetime import datetime, timezone

from app.observability.traces import Trace

_SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    execution_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    model TEXT NOT NULL,
    input_text TEXT NOT NULL,
    status TEXT NOT NULL,
    cost REAL NOT NULL,
    latency_ms REAL NOT NULL,
    created_at TEXT NOT NULL,
    trace_json TEXT NOT NULL
);
"""


class TraceNotFoundError(Exception):
    pass


class TraceStore:
    """SQLite-backed persistence for app/observability/traces.py's Trace
    model, following the same pattern as every other store in this project
    (TaskStore, GoalStore, etc.). TraceRecorder builds a Trace in-memory for
    a single execution; this store is what lets a trace be looked up again
    later by its execution_id (== trace_id), e.g. from the dashboard's
    Traces page. The full Trace (with all nested spans) is stored as JSON in
    trace_json -- the other columns are just an indexable summary for
    listing without deserializing every row."""

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def save(self, trace: Trace, input_text: str) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO traces
                (execution_id, session_id, user_id, agent, model, input_text,
                 status, cost, latency_ms, created_at, trace_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace.execution_id, trace.session_id, trace.user_id, trace.agent,
                trace.model, input_text, trace.status, trace.cost, trace.latency_ms,
                datetime.now(timezone.utc).isoformat(), trace.model_dump_json(),
            ),
        )
        self._conn.commit()

    def get(self, execution_id: str) -> Trace:
        row = self._conn.execute(
            "SELECT trace_json FROM traces WHERE execution_id = ?", (execution_id,)
        ).fetchone()
        if row is None:
            raise TraceNotFoundError(f"No trace with execution_id '{execution_id}'.")
        return Trace.model_validate_json(row["trace_json"])

    def list_summaries(self, limit: int = 100) -> list[dict]:
        """Lightweight listing (no full trace_json deserialization) for a
        sidebar of trace_ids, newest first."""
        rows = self._conn.execute(
            """
            SELECT execution_id, session_id, user_id, agent, model, input_text,
                   status, cost, latency_ms, created_at
            FROM traces ORDER BY created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
