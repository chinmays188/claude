import sqlite3
from datetime import datetime

from app.memory.models import MemoryRecord, MemoryType

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    importance REAL NOT NULL,
    user_confirmed INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(tenant_id, user_id);
"""


class PersistentMemoryStore:
    """SQLite-backed memory store, scoped by (tenant_id, user_id) per Section 55 —
    same isolation discipline as Phase 1's in-memory MemoryStore, but durable
    across process restarts, which is the actual point of 'long-term' memory
    (Section 11: 'move from conversation history to meaningful personal memory')."""

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def write(self, record: MemoryRecord) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO memories
               (memory_id, tenant_id, user_id, type, content, source, confidence,
                created_at, updated_at, importance, user_confirmed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.memory_id, record.tenant_id, record.user_id, record.type.value,
                record.content, record.source, record.confidence,
                record.created_at.isoformat(), record.updated_at.isoformat(),
                record.importance, int(record.user_confirmed),
            ),
        )
        self._conn.commit()

    def get(self, tenant_id: str, user_id: str, memory_id: str) -> MemoryRecord | None:
        row = self._conn.execute(
            "SELECT * FROM memories WHERE tenant_id = ? AND user_id = ? AND memory_id = ?",
            (tenant_id, user_id, memory_id),
        ).fetchone()
        return _row_to_record(row) if row else None

    def list_all(self, tenant_id: str, user_id: str) -> list[MemoryRecord]:
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE tenant_id = ? AND user_id = ? ORDER BY created_at DESC",
            (tenant_id, user_id),
        ).fetchall()
        return [_row_to_record(row) for row in rows]

    def list_by_type(self, tenant_id: str, user_id: str, memory_type: MemoryType) -> list[MemoryRecord]:
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE tenant_id = ? AND user_id = ? AND type = ? ORDER BY created_at DESC",
            (tenant_id, user_id, memory_type.value),
        ).fetchall()
        return [_row_to_record(row) for row in rows]

    def count(self, tenant_id: str, user_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM memories WHERE tenant_id = ? AND user_id = ?",
            (tenant_id, user_id),
        ).fetchone()
        return row["n"]


def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
    return MemoryRecord(
        memory_id=row["memory_id"],
        tenant_id=row["tenant_id"],
        user_id=row["user_id"],
        type=MemoryType(row["type"]),
        content=row["content"],
        source=row["source"],
        confidence=row["confidence"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        importance=row["importance"],
        user_confirmed=bool(row["user_confirmed"]),
    )
