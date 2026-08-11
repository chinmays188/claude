import json
import sqlite3
from datetime import datetime, timezone

from app.tasks.models import LongRunningTask, TaskState, validate_transition

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    description TEXT NOT NULL,
    state TEXT NOT NULL,
    checkpoint_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    retry_count INTEGER NOT NULL,
    max_retries INTEGER NOT NULL,
    progress REAL NOT NULL,
    dependencies_json TEXT NOT NULL,
    result TEXT
);
"""


class TaskNotFoundError(Exception):
    pass


class MaxRetriesExceededError(Exception):
    pass


class TaskStore:
    """SQLite-backed task state machine (Section 30/31). Every state
    transition is validated against the state machine's adjacency list —
    a task can never silently jump from PENDING straight to COMPLETED, for
    instance. Checkpointing is a caller-supplied dict, persisted as-is, so a
    task's resumable progress survives a process restart."""

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def create(self, task: LongRunningTask) -> None:
        self._save(task)

    def get(self, task_id: str) -> LongRunningTask:
        row = self._conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            raise TaskNotFoundError(f"No task with id '{task_id}'.")
        return _row_to_task(row)

    def list_by_owner(self, owner: str) -> list[LongRunningTask]:
        rows = self._conn.execute("SELECT * FROM tasks WHERE owner = ? ORDER BY created_at DESC", (owner,)).fetchall()
        return [_row_to_task(row) for row in rows]

    def transition(self, task_id: str, target_state: TaskState, checkpoint: dict | None = None, result: str | None = None) -> LongRunningTask:
        task = self.get(task_id)
        validate_transition(task.state, target_state)

        task.state = target_state
        task.updated_at = datetime.now(timezone.utc)
        if checkpoint is not None:
            task.checkpoint = checkpoint
        if result is not None:
            task.result = result

        self._save(task)
        return task

    def pause(self, task_id: str) -> LongRunningTask:
        return self.transition(task_id, TaskState.PAUSED)

    def resume(self, task_id: str) -> LongRunningTask:
        return self.transition(task_id, TaskState.RUNNING)

    def cancel(self, task_id: str) -> LongRunningTask:
        return self.transition(task_id, TaskState.CANCELLED)

    def retry(self, task_id: str) -> LongRunningTask:
        task = self.get(task_id)
        if task.retry_count >= task.max_retries:
            raise MaxRetriesExceededError(
                f"Task '{task_id}' has exhausted its retry budget ({task.retry_count}/{task.max_retries})."
            )
        task.retry_count += 1
        self._save(task)
        return self.transition(task_id, TaskState.RECOVERY)

    def update_progress(self, task_id: str, progress: float) -> LongRunningTask:
        task = self.get(task_id)
        task.progress = max(0.0, min(1.0, progress))
        task.updated_at = datetime.now(timezone.utc)
        self._save(task)
        return task

    def _save(self, task: LongRunningTask) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO tasks
               (task_id, owner, description, state, checkpoint_json, created_at,
                updated_at, retry_count, max_retries, progress, dependencies_json, result)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.task_id, task.owner, task.description, task.state.value,
                json.dumps(task.checkpoint), task.created_at.isoformat(), task.updated_at.isoformat(),
                task.retry_count, task.max_retries, task.progress,
                json.dumps(task.dependencies), task.result,
            ),
        )
        self._conn.commit()


def _row_to_task(row: sqlite3.Row) -> LongRunningTask:
    return LongRunningTask(
        task_id=row["task_id"], owner=row["owner"], description=row["description"],
        state=TaskState(row["state"]), checkpoint=json.loads(row["checkpoint_json"]),
        created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
        retry_count=row["retry_count"], max_retries=row["max_retries"], progress=row["progress"],
        dependencies=json.loads(row["dependencies_json"]), result=row["result"],
    )
