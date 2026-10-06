import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ActionClass(str, Enum):
    READ = "READ"  # no approval
    WRITE = "WRITE"  # usually approval
    ACT = "ACT"  # approval required


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ActionProposal(BaseModel):
    action_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    action_class: ActionClass
    tool_name: str
    description: str
    args: dict
    risk_level: RiskLevel = RiskLevel.LOW
    proposed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_APPROVED = "AUTO_APPROVED"  # READ actions never need a human, but still logged
    UNDONE = "UNDONE"  # an executed action that was genuinely reversed via Tool.undo()


class AuditRecord(BaseModel):
    action_id: str
    proposal: ActionProposal
    approval_status: ApprovalStatus
    approved_by: str | None = None
    executed: bool = False
    execution_result: str | None = None
    verified: bool = False
    verification_note: str | None = None
    # Found missing while investigating "Human-in-the-Loop AI": an executed
    # action had no path back to "undone" at all. Set only after a real
    # Tool.undo() call genuinely succeeds -- never optimistically.
    undone: bool = False
    undo_result: str | None = None
    undone_by: str | None = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
