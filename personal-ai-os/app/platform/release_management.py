import sqlite3
from datetime import datetime, timezone

from pydantic import BaseModel


class ReleaseRecord(BaseModel):
    """Milestone 54: a versioned record of a specific model/prompt
    configuration — e.g. 'research_agent system prompt v3' or 'model router
    tier config v2'. component identifies what changed; content is the
    actual value (prompt text, model name, config dict serialized as text)."""

    component: str
    version: int
    content: str
    created_at: datetime
    is_active: bool = False


_SCHEMA = """
CREATE TABLE IF NOT EXISTS releases (
    component TEXT NOT NULL,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_active INTEGER NOT NULL,
    PRIMARY KEY (component, version)
);
"""


class ReleaseNotFoundError(Exception):
    pass


class ReleaseManager:
    """Milestone 54: versions a component's content and tracks which version
    is currently active, with a real rollback operation — 'ship the previous
    version again' is a single call, not a manual find-and-restore. SQLite-
    backed for the same durability reasons as every other store in this project."""

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def publish(self, component: str, content: str) -> ReleaseRecord:
        """Creates a new version (auto-incremented) and makes it active,
        deactivating whatever was active before."""
        next_version = self._next_version(component)
        record = ReleaseRecord(component=component, version=next_version, content=content, created_at=datetime.now(timezone.utc), is_active=True)

        self._conn.execute("UPDATE releases SET is_active = 0 WHERE component = ?", (component,))
        self._save(record)
        return record

    def active(self, component: str) -> ReleaseRecord:
        row = self._conn.execute(
            "SELECT * FROM releases WHERE component = ? AND is_active = 1", (component,)
        ).fetchone()
        if row is None:
            raise ReleaseNotFoundError(f"No active release for component '{component}'.")
        return _row_to_record(row)

    def history(self, component: str) -> list[ReleaseRecord]:
        rows = self._conn.execute(
            "SELECT * FROM releases WHERE component = ? ORDER BY version DESC", (component,)
        ).fetchall()
        return [_row_to_record(row) for row in rows]

    def rollback(self, component: str) -> ReleaseRecord:
        """Milestone 54's rollback: reactivates the version immediately
        before the current active one. Raises if there's nothing to roll
        back to (only one version exists, or none at all) — rollback must
        never silently no-op and claim success."""
        history = self.history(component)
        if len(history) < 2:
            raise ReleaseNotFoundError(
                f"Cannot roll back component '{component}': fewer than 2 versions exist."
            )

        current_active = next((r for r in history if r.is_active), None)
        if current_active is None:
            raise ReleaseNotFoundError(f"No active release for component '{component}' to roll back from.")

        previous = next((r for r in history if r.version == current_active.version - 1), None)
        if previous is None:
            raise ReleaseNotFoundError(
                f"No version {current_active.version - 1} found for component '{component}' to roll back to."
            )

        self._conn.execute("UPDATE releases SET is_active = 0 WHERE component = ?", (component,))
        previous.is_active = True
        self._save(previous)
        return previous

    def _next_version(self, component: str) -> int:
        row = self._conn.execute(
            "SELECT MAX(version) AS max_version FROM releases WHERE component = ?", (component,)
        ).fetchone()
        return (row["max_version"] or 0) + 1

    def _save(self, record: ReleaseRecord) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO releases (component, version, content, created_at, is_active) VALUES (?, ?, ?, ?, ?)",
            (record.component, record.version, record.content, record.created_at.isoformat(), int(record.is_active)),
        )
        self._conn.commit()


def _row_to_record(row: sqlite3.Row) -> ReleaseRecord:
    return ReleaseRecord(
        component=row["component"], version=row["version"], content=row["content"],
        created_at=datetime.fromisoformat(row["created_at"]), is_active=bool(row["is_active"]),
    )
