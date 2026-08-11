import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RECOVERY = "RECOVERY"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"


# Section 30's state machine, expressed as an explicit adjacency list so
# invalid transitions can be rejected rather than silently allowed.
_VALID_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.PENDING: {TaskState.PLANNING, TaskState.CANCELLED},
    TaskState.PLANNING: {TaskState.RUNNING, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.RUNNING: {
        TaskState.WAITING, TaskState.EVALUATING, TaskState.FAILED,
        TaskState.PAUSED, TaskState.CANCELLED, TaskState.COMPLETED,
    },
    TaskState.WAITING: {TaskState.RUNNING, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.EVALUATING: {TaskState.COMPLETED, TaskState.RUNNING, TaskState.FAILED},
    TaskState.FAILED: {TaskState.RECOVERY, TaskState.CANCELLED},
    TaskState.RECOVERY: {TaskState.RUNNING, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.PAUSED: {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.COMPLETED: set(),
    TaskState.CANCELLED: set(),
}


class InvalidTransitionError(Exception):
    pass


def validate_transition(current: TaskState, target: TaskState) -> None:
    if target not in _VALID_TRANSITIONS[current]:
        raise InvalidTransitionError(f"Cannot transition from {current.value} to {target.value}.")


class LongRunningTask(BaseModel):
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    owner: str
    description: str
    state: TaskState = TaskState.PENDING
    checkpoint: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    max_retries: int = 3
    progress: float = 0.0  # 0.0-1.0
    dependencies: list[str] = Field(default_factory=list)
    result: str | None = None
