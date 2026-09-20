import uuid
from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.domains.router import Domain


class GoalStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Goal(BaseModel):
    """Section 33's exact field list."""

    goal_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    owner_id: str
    title: str
    description: str = ""
    domain: Domain
    priority: float = 0.5  # 0.0-1.0
    deadline: date | None = None
    status: GoalStatus = GoalStatus.NOT_STARTED
    progress: float = 0.0  # 0.0-1.0
    dependencies: list[str] = Field(default_factory=list)  # other goal_ids
    success_criteria: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GoalConflict(BaseModel):
    goal_id_a: str
    goal_id_b: str
    reason: str
