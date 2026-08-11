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

    def record(self, record: AuditRecord) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO audit_log
               (action_id, proposal_json, approval_status, approved_by, executed,
                execution_result, verified, verification_note, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.action_id, record.proposal.model_dump_json(), record.approval_status.value,
                record.approved_by, int(record.executed), record.execution_result,
                int(record.verified), record.verification_note, record.recorded_at.isoformat(),
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
        recorded_at=row["recorded_at"],
    )
