import json
import sqlite3
import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"  # exhausted retries — needs manual attention


class Job(BaseModel):
    job_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    queue_name: str
    payload: dict
    status: JobStatus = JobStatus.QUEUED
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    queue_name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    max_attempts INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error TEXT
);
"""


class JobNotFoundError(Exception):
    pass


class JobQueue:
    """Milestone 46: 'Async Jobs & Queues.' SQLite-backed, in-process queue —
    real enqueue/dequeue/retry/dead-letter semantics, tested and durable
    across restarts, but not a real external broker (Redis/RabbitMQ/SQS).
    The interface (enqueue/dequeue/complete/fail) is exactly what a real
    broker-backed implementation would need to satisfy, so swapping the
    backend later doesn't require changing callers."""

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def enqueue(self, queue_name: str, payload: dict, max_attempts: int = 3) -> Job:
        job = Job(queue_name=queue_name, payload=payload, max_attempts=max_attempts)
        self._save(job)
        return job

    def dequeue(self, queue_name: str) -> Job | None:
        """Claims the oldest QUEUED job in this queue, marking it
        IN_PROGRESS. Returns None if nothing is queued — callers poll or
        back off, rather than blocking (no real broker to push to this
        in-process implementation)."""
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE queue_name = ? AND status = ? ORDER BY created_at ASC LIMIT 1",
            (queue_name, JobStatus.QUEUED.value),
        ).fetchone()
        if row is None:
            return None

        job = _row_to_job(row)
        job.status = JobStatus.IN_PROGRESS
        job.attempts += 1
        job.updated_at = datetime.now(timezone.utc)
        self._save(job)
        return job

    def complete(self, job_id: str) -> Job:
        job = self.get(job_id)
        job.status = JobStatus.SUCCEEDED
        job.updated_at = datetime.now(timezone.utc)
        self._save(job)
        return job

    def fail(self, job_id: str, error: str) -> Job:
        """Milestone 46's retry/dead-letter semantics: a failed job goes back
        to QUEUED if it hasn't exhausted max_attempts, otherwise DEAD_LETTER —
        never silently dropped, and never retried forever."""
        job = self.get(job_id)
        job.error = error
        job.updated_at = datetime.now(timezone.utc)
        if job.attempts >= job.max_attempts:
            job.status = JobStatus.DEAD_LETTER
        else:
            job.status = JobStatus.QUEUED
        self._save(job)
        return job

    def get(self, job_id: str) -> Job:
        row = self._conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise JobNotFoundError(f"No job with id '{job_id}'.")
        return _row_to_job(row)

    def dead_letter_jobs(self, queue_name: str) -> list[Job]:
        rows = self._conn.execute(
            "SELECT * FROM jobs WHERE queue_name = ? AND status = ? ORDER BY updated_at DESC",
            (queue_name, JobStatus.DEAD_LETTER.value),
        ).fetchall()
        return [_row_to_job(row) for row in rows]

    def _save(self, job: Job) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO jobs
               (job_id, queue_name, payload_json, status, attempts, max_attempts, created_at, updated_at, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job.job_id, job.queue_name, json.dumps(job.payload), job.status.value,
                job.attempts, job.max_attempts, job.created_at.isoformat(), job.updated_at.isoformat(), job.error,
            ),
        )
        self._conn.commit()


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        job_id=row["job_id"], queue_name=row["queue_name"], payload=json.loads(row["payload_json"]),
        status=JobStatus(row["status"]), attempts=row["attempts"], max_attempts=row["max_attempts"],
        created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
        error=row["error"],
    )
