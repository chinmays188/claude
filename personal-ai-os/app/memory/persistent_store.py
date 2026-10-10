import sqlite3
from datetime import datetime

from app.memory.models import MemoryRecord, MemoryStatus, MemoryType

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
        self._migrate_conflict_columns()

    def _migrate_conflict_columns(self) -> None:
        # Same real migration pattern as AuditLog._migrate_undo_columns():
        # a real, already-existing data/personal_ai.db predates the
        # status/superseded_by columns added for real conflict handling,
        # so CREATE TABLE IF NOT EXISTS alone would silently skip them.
        existing_columns = {row["name"] for row in self._conn.execute("PRAGMA table_info(memories)")}
        for column, ddl_type in (
            ("status", f"TEXT NOT NULL DEFAULT '{MemoryStatus.ACTIVE.value}'"),
            ("superseded_by", "TEXT"),
        ):
            if column not in existing_columns:
                self._conn.execute(f"ALTER TABLE memories ADD COLUMN {column} {ddl_type}")
        self._conn.commit()

    def write(self, record: MemoryRecord) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO memories
               (memory_id, tenant_id, user_id, type, content, source, confidence,
                created_at, updated_at, importance, user_confirmed, status, superseded_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.memory_id, record.tenant_id, record.user_id, record.type.value,
                record.content, record.source, record.confidence,
                record.created_at.isoformat(), record.updated_at.isoformat(),
                record.importance, int(record.user_confirmed),
                record.status.value, record.superseded_by,
            ),
        )
        self._conn.commit()

    def mark_superseded(self, tenant_id: str, user_id: str, memory_id: str, superseded_by: str) -> None:
        """Real conflict-resolution primitive: marks an old memory SUPERSEDED
        by a new, contradicting one -- never deletes it, so history is
        preserved (same never-destroy-on-write discipline as memory decay's
        flag-for-review-not-delete behavior)."""
        self._conn.execute(
            "UPDATE memories SET status = ?, superseded_by = ? "
            "WHERE tenant_id = ? AND user_id = ? AND memory_id = ?",
            (MemoryStatus.SUPERSEDED.value, superseded_by, tenant_id, user_id, memory_id),
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

    def delete(self, tenant_id: str, user_id: str, memory_id: str) -> None:
        """Found missing while building a real undo path for write_memory
        (Human-in-the-Loop AI investigation) -- scoped by tenant/user like
        every other real lookup here, so undo can't cross a scope boundary."""
        self._conn.execute(
            "DELETE FROM memories WHERE tenant_id = ? AND user_id = ? AND memory_id = ?",
            (tenant_id, user_id, memory_id),
        )
        self._conn.commit()

    def update_confidence(self, tenant_id: str, user_id: str, memory_id: str, confidence: float) -> None:
        """Found missing while investigating "AI Memory": nothing ever
        updated a memory's confidence over time. Deliberately does NOT
        touch updated_at -- a decay update should record a lower
        confidence without resetting the age clock that decay itself is
        computed from (unlike write(), which is a full INSERT OR REPLACE
        and would wrongly make a just-decayed memory look freshly
        updated)."""
        self._conn.execute(
            "UPDATE memories SET confidence = ? WHERE tenant_id = ? AND user_id = ? AND memory_id = ?",
            (confidence, tenant_id, user_id, memory_id),
        )
        self._conn.commit()

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
        status=MemoryStatus(row["status"]) if row["status"] is not None else MemoryStatus.ACTIVE,
        superseded_by=row["superseded_by"],
    )
