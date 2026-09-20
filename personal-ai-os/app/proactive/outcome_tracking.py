import json
import sqlite3
import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class OutcomeStatus(str, Enum):
    PENDING = "pending"  # action executed, outcome not yet known
    ACHIEVED = "achieved"  # the action accomplished its intended purpose
    FAILED = "failed"  # the action executed but did not achieve its purpose
    UNKNOWN = "unknown"  # never resolved (e.g. no way to observe the outcome)


class Outcome(BaseModel):
    """Milestone 37: tracks whether an executed action actually worked, as a
    distinct record from PolicyEngine's per-execution 'verified' flag
    (Phase 2, Milestone 25) — that flag checks 'did the tool call return
    something,' this tracks 'did the underlying goal get achieved,' which may
    only be knowable later (e.g. did the stakeholder actually reply?)."""

    outcome_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    action_id: str  # PolicyEngine's ActionProposal.action_id
    owner_id: str
    expected_result: str
    status: OutcomeStatus = OutcomeStatus.PENDING
    actual_result: str | None = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS outcomes (
    outcome_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    expected_result TEXT NOT NULL,
    status TEXT NOT NULL,
    actual_result TEXT,
    recorded_at TEXT NOT NULL,
    resolved_at TEXT
);
"""


class OutcomeNotFoundError(Exception):
    pass


class OutcomeStore:
    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def record(self, outcome: Outcome) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO outcomes
               (outcome_id, action_id, owner_id, expected_result, status, actual_result, recorded_at, resolved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                outcome.outcome_id, outcome.action_id, outcome.owner_id, outcome.expected_result,
                outcome.status.value, outcome.actual_result, outcome.recorded_at.isoformat(),
                outcome.resolved_at.isoformat() if outcome.resolved_at else None,
            ),
        )
        self._conn.commit()

    def get(self, outcome_id: str) -> Outcome:
        row = self._conn.execute("SELECT * FROM outcomes WHERE outcome_id = ?", (outcome_id,)).fetchone()
        if row is None:
            raise OutcomeNotFoundError(f"No outcome with id '{outcome_id}'.")
        return _row_to_outcome(row)

    def resolve(self, outcome_id: str, status: OutcomeStatus, actual_result: str) -> Outcome:
        outcome = self.get(outcome_id)
        outcome.status = status
        outcome.actual_result = actual_result
        outcome.resolved_at = datetime.now(timezone.utc)
        self.record(outcome)
        return outcome

    def list_pending(self, owner_id: str) -> list[Outcome]:
        rows = self._conn.execute(
            "SELECT * FROM outcomes WHERE owner_id = ? AND status = ? ORDER BY recorded_at ASC",
            (owner_id, OutcomeStatus.PENDING.value),
        ).fetchall()
        return [_row_to_outcome(row) for row in rows]

    def success_rate(self, owner_id: str) -> float | None:
        """Milestone 42's raw material: fraction of resolved outcomes that
        actually achieved their intended purpose. None if nothing resolved
        yet, never 0.0 by default — an unmeasured system should never look
        like a failing one either."""
        rows = self._conn.execute(
            "SELECT status FROM outcomes WHERE owner_id = ? AND status != ?",
            (owner_id, OutcomeStatus.PENDING.value),
        ).fetchall()
        if not rows:
            return None
        achieved = sum(1 for r in rows if r["status"] == OutcomeStatus.ACHIEVED.value)
        return achieved / len(rows)


def _row_to_outcome(row: sqlite3.Row) -> Outcome:
    return Outcome(
        outcome_id=row["outcome_id"], action_id=row["action_id"], owner_id=row["owner_id"],
        expected_result=row["expected_result"], status=OutcomeStatus(row["status"]),
        actual_result=row["actual_result"], recorded_at=datetime.fromisoformat(row["recorded_at"]),
        resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
    )
