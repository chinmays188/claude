import json
import sqlite3
from datetime import date, datetime, timezone

from app.domains.cross_domain.models import Goal, GoalStatus
from app.domains.router import Domain

_SCHEMA = """
CREATE TABLE IF NOT EXISTS goals (
    goal_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    domain TEXT NOT NULL,
    priority REAL NOT NULL,
    deadline TEXT,
    status TEXT NOT NULL,
    progress REAL NOT NULL,
    dependencies_json TEXT NOT NULL,
    success_criteria_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class GoalNotFoundError(Exception):
    pass


class GoalStore:
    """SQLite-backed, same durability guarantee as Phase 2's TaskStore/
    GraphStore — goals must survive process restarts to be meaningfully
    "tracked" at all (Section 34's Goal Agent responsibilities assume this)."""

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def create(self, goal: Goal) -> None:
        self._save(goal)

    def get(self, goal_id: str) -> Goal:
        row = self._conn.execute("SELECT * FROM goals WHERE goal_id = ?", (goal_id,)).fetchone()
        if row is None:
            raise GoalNotFoundError(f"No goal with id '{goal_id}'.")
        return _row_to_goal(row)

    def list_by_owner(self, owner_id: str) -> list[Goal]:
        rows = self._conn.execute(
            "SELECT * FROM goals WHERE owner_id = ? ORDER BY priority DESC", (owner_id,)
        ).fetchall()
        return [_row_to_goal(row) for row in rows]

    def update_progress(self, goal_id: str, progress: float) -> Goal:
        goal = self.get(goal_id)
        goal.progress = max(0.0, min(1.0, progress))
        goal.updated_at = datetime.now(timezone.utc)
        if goal.progress >= 1.0:
            goal.status = GoalStatus.COMPLETED
        self._save(goal)
        return goal

    def update_status(self, goal_id: str, status: GoalStatus) -> Goal:
        goal = self.get(goal_id)
        goal.status = status
        self._save(goal)
        return goal

    def _save(self, goal: Goal) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO goals
               (goal_id, owner_id, title, description, domain, priority, deadline,
                status, progress, dependencies_json, success_criteria_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                goal.goal_id, goal.owner_id, goal.title, goal.description, goal.domain.value,
                goal.priority, goal.deadline.isoformat() if goal.deadline else None,
                goal.status.value, goal.progress, json.dumps(goal.dependencies),
                json.dumps(goal.success_criteria), goal.created_at.isoformat(), goal.updated_at.isoformat(),
            ),
        )
        self._conn.commit()


def _row_to_goal(row: sqlite3.Row) -> Goal:
    return Goal(
        goal_id=row["goal_id"], owner_id=row["owner_id"], title=row["title"], description=row["description"],
        domain=Domain(row["domain"]), priority=row["priority"],
        deadline=date.fromisoformat(row["deadline"]) if row["deadline"] else None,
        status=GoalStatus(row["status"]), progress=row["progress"],
        dependencies=json.loads(row["dependencies_json"]), success_criteria=json.loads(row["success_criteria_json"]),
        created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
    )
