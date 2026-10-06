import json
import sqlite3

from app.actions.models import ActionProposal, ApprovalStatus, AuditRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    action_id TEXT PRIMARY KEY,
    proposal_json TEXT NOT NULL,
    approval_status TEXT NOT NULL,
    approved_by TEXT,
    executed INTEGER NOT NULL,
    execution_result TEXT,
    verified INTEGER NOT NULL,
    verification_note TEXT,
    undone INTEGER NOT NULL DEFAULT 0,
    undo_result TEXT,
    undone_by TEXT,
    recorded_at TEXT NOT NULL
);
"""


class AuditLog:
    """Section 28: 'Every action should generate an audit record.' SQLite-backed
    so the audit trail survives process restarts — an audit log that resets on
    every run isn't an audit log."""

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._migrate_undo_columns()

    def _migrate_undo_columns(self) -> None:
        # First real migration this project has ever needed -- every
        # earlier store only ever ran its _SCHEMA against a fresh/reseeded
        # DB. A real, already-existing data/personal_ai.db predates the
        # undone/undo_result/undone_by columns, so CREATE TABLE IF NOT
        # EXISTS alone would silently skip them on that real file.
        existing_columns = {row["name"] for row in self._conn.execute("PRAGMA table_info(audit_log)")}
        for column, ddl_type in (("undone", "INTEGER NOT NULL DEFAULT 0"), ("undo_result", "TEXT"), ("undone_by", "TEXT")):
            if column not in existing_columns:
                self._conn.execute(f"ALTER TABLE audit_log ADD COLUMN {column} {ddl_type}")
        self._conn.commit()

    def record(self, record: AuditRecord) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO audit_log
               (action_id, proposal_json, approval_status, approved_by, executed,
                execution_result, verified, verification_note, undone, undo_result,
                undone_by, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.action_id, record.proposal.model_dump_json(), record.approval_status.value,
                record.approved_by, int(record.executed), record.execution_result,
                int(record.verified), record.verification_note, int(record.undone),
                record.undo_result, record.undone_by, record.recorded_at.isoformat(),
            ),
        )
        self._conn.commit()

    def get(self, action_id: str) -> AuditRecord | None:
        row = self._conn.execute("SELECT * FROM audit_log WHERE action_id = ?", (action_id,)).fetchone()
        return _row_to_record(row) if row else None

    def list_all(self) -> list[AuditRecord]:
        rows = self._conn.execute("SELECT * FROM audit_log ORDER BY recorded_at DESC").fetchall()
        return [_row_to_record(row) for row in rows]

    def list_pending_approval(self) -> list[AuditRecord]:
        rows = self._conn.execute(
            "SELECT * FROM audit_log WHERE approval_status = ? ORDER BY recorded_at ASC",
            (ApprovalStatus.PENDING.value,),
        ).fetchall()
        return [_row_to_record(row) for row in rows]

    def list_executed_not_undone(self) -> list[AuditRecord]:
        """Real candidates for undo: executed, not already undone. Whether
        the underlying Tool actually supports undo is checked separately
        (PolicyEngine.undo_action) -- this list can include non-undoable
        tools' records too, same as list_pending_approval doesn't pre-filter
        by tool either."""
        rows = self._conn.execute(
            "SELECT * FROM audit_log WHERE executed = 1 AND undone = 0 "
            "AND approval_status != ? ORDER BY recorded_at DESC",
            (ApprovalStatus.REJECTED.value,),
        ).fetchall()
        return [_row_to_record(row) for row in rows]


def _row_to_record(row: sqlite3.Row) -> AuditRecord:
    return AuditRecord(
        action_id=row["action_id"],
        proposal=ActionProposal.model_validate(json.loads(row["proposal_json"])),
        approval_status=ApprovalStatus(row["approval_status"]),
        approved_by=row["approved_by"],
        executed=bool(row["executed"]),
        execution_result=row["execution_result"],
        verified=bool(row["verified"]),
        verification_note=row["verification_note"],
        undone=bool(row["undone"]) if row["undone"] is not None else False,
        undo_result=row["undo_result"],
        undone_by=row["undone_by"],
        recorded_at=row["recorded_at"],
    )
