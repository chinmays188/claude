import json
import sqlite3
import uuid
from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

DETECT_PROMPT = """Identify any commitments in this text — things the user
promised to do, or things someone promised the user. Do not invent
commitments not actually stated or clearly implied in the text below.

Text: {text}

Respond with ONLY a JSON object:
{{"commitments": [{{"description": "<what was committed>", "owner": "user" | "other_party", "due_date": "<YYYY-MM-DD or null if not stated>"}}]}}
"""


class CommitmentOwner(str, Enum):
    USER = "user"
    OTHER_PARTY = "other_party"


class CommitmentStatus(str, Enum):
    OPEN = "open"
    FOLLOWED_UP = "followed_up"
    FULFILLED = "fulfilled"
    OVERDUE = "overdue"


class Commitment(BaseModel):
    commitment_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    owner_id: str
    description: str
    owner: CommitmentOwner
    due_date: date | None = None
    status: CommitmentStatus = CommitmentStatus.OPEN
    source_text: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class _DetectedCommitment(BaseModel):
    description: str
    owner: CommitmentOwner
    due_date: date | None = None


class _DetectionResult(BaseModel):
    commitments: list[_DetectedCommitment]


def detect_commitments(llm: LLMProvider, owner_id: str, text: str) -> list[Commitment]:
    """Milestone 33: 'Commitment detection.' Uses an LLM since recognizing a
    commitment in natural language ("I'll get back to you by Friday") is a
    judgment call, not a deterministic pattern match — but every returned
    commitment is grounded in the source text via source_text, not fabricated."""
    if not text or not text.strip():
        raise ValueError("Text must not be empty.")

    generator = RepairableGenerator(llm, _DetectionResult)
    result = generator.generate(DETECT_PROMPT.format(text=text))
    return [
        Commitment(owner_id=owner_id, description=c.description, owner=c.owner, due_date=c.due_date, source_text=text)
        for c in result.commitments
    ]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS commitments (
    commitment_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    description TEXT NOT NULL,
    owner TEXT NOT NULL,
    due_date TEXT,
    status TEXT NOT NULL,
    source_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class CommitmentNotFoundError(Exception):
    pass


class CommitmentStore:
    """SQLite-backed, same durability pattern as Phase 2/3's stores — a
    follow-up manager that forgets commitments on restart defeats its own purpose."""

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def save(self, commitment: Commitment) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO commitments
               (commitment_id, owner_id, description, owner, due_date, status, source_text, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                commitment.commitment_id, commitment.owner_id, commitment.description, commitment.owner.value,
                commitment.due_date.isoformat() if commitment.due_date else None,
                commitment.status.value, commitment.source_text, commitment.created_at.isoformat(),
            ),
        )
        self._conn.commit()

    def get(self, commitment_id: str) -> Commitment:
        row = self._conn.execute("SELECT * FROM commitments WHERE commitment_id = ?", (commitment_id,)).fetchone()
        if row is None:
            raise CommitmentNotFoundError(f"No commitment with id '{commitment_id}'.")
        return _row_to_commitment(row)

    def list_by_owner(self, owner_id: str) -> list[Commitment]:
        rows = self._conn.execute(
            "SELECT * FROM commitments WHERE owner_id = ? ORDER BY created_at DESC", (owner_id,)
        ).fetchall()
        return [_row_to_commitment(row) for row in rows]

    def update_status(self, commitment_id: str, status: CommitmentStatus) -> Commitment:
        commitment = self.get(commitment_id)
        commitment.status = status
        self.save(commitment)
        return commitment

    def overdue(self, owner_id: str, as_of: date | None = None) -> list[Commitment]:
        """Milestone 33's follow-up half: a commitment past its due date and
        still open/followed-up (not fulfilled) needs the user's attention."""
        as_of = as_of or date.today()
        return [
            c for c in self.list_by_owner(owner_id)
            if c.due_date is not None and c.due_date < as_of
            and c.status in (CommitmentStatus.OPEN, CommitmentStatus.FOLLOWED_UP)
        ]


def _row_to_commitment(row: sqlite3.Row) -> Commitment:
    return Commitment(
        commitment_id=row["commitment_id"], owner_id=row["owner_id"], description=row["description"],
        owner=CommitmentOwner(row["owner"]), due_date=date.fromisoformat(row["due_date"]) if row["due_date"] else None,
        status=CommitmentStatus(row["status"]), source_text=row["source_text"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
