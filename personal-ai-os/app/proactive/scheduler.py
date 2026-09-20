import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ScheduleKind(str, Enum):
    INTERVAL = "interval"  # run every N seconds
    EVENT_DRIVEN = "event_driven"  # run whenever a matching event is published, not on a timer


class ScheduledJob(BaseModel):
    """Milestone 39. Scope decision: no real always-on process hosts this —
    `Scheduler.tick()` must be called by something external (a cron entry, a
    manual call, a test) to actually advance time and run due jobs. The
    scheduling *logic* (is this job due, has it run recently) is real and
    tested; only the 'who calls tick() every N seconds forever' part is
    deferred, per project scope decision."""

    job_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    kind: ScheduleKind
    interval_seconds: float | None = None  # required if kind == INTERVAL
    last_run_at: datetime | None = None
    enabled: bool = True


class Scheduler:
    def __init__(self):
        self._jobs: dict[str, ScheduledJob] = {}
        self._callbacks: dict[str, callable] = {}

    def register(self, job: ScheduledJob, callback: callable) -> None:
        if job.kind == ScheduleKind.INTERVAL and job.interval_seconds is None:
            raise ValueError("INTERVAL jobs require interval_seconds.")
        self._jobs[job.job_id] = job
        self._callbacks[job.job_id] = callback

    def due_jobs(self, now: datetime | None = None) -> list[ScheduledJob]:
        """Milestone 39: 'Scheduled agents.' A job is due if it's an INTERVAL
        job, enabled, and enough time has passed since last_run_at (or it has
        never run). EVENT_DRIVEN jobs are never 'due' by time — they run via
        `notify_event()` instead (Milestone 39: 'Event-driven agents')."""
        now = now or datetime.now(timezone.utc)
        due = []
        for job in self._jobs.values():
            if not job.enabled or job.kind != ScheduleKind.INTERVAL:
                continue
            if job.last_run_at is None:
                due.append(job)
                continue
            elapsed = (now - job.last_run_at).total_seconds()
            if elapsed >= job.interval_seconds:
                due.append(job)
        return due

    def tick(self, now: datetime | None = None) -> list[str]:
        """Runs every due INTERVAL job's callback once and marks it run.
        Returns the job_ids that ran."""
        now = now or datetime.now(timezone.utc)
        ran = []
        for job in self.due_jobs(now):
            self._callbacks[job.job_id]()
            job.last_run_at = now
            ran.append(job.job_id)
        return ran

    def notify_event(self, event_type_name: str) -> list[str]:
        """Milestone 39's event-driven half: runs every enabled EVENT_DRIVEN
        job registered under this event type name. Deliberately a plain
        string match (not importing EventType here) so this module has no
        dependency on app.proactive.events — a scheduler shouldn't need to
        know what kinds of events exist, only that a name matched."""
        ran = []
        for job in self._jobs.values():
            if job.kind == ScheduleKind.EVENT_DRIVEN and job.enabled and job.name == event_type_name:
                self._callbacks[job.job_id]()
                job.last_run_at = datetime.now(timezone.utc)
                ran.append(job.job_id)
        return ran

    def disable(self, job_id: str) -> None:
        self._jobs[job_id].enabled = False

    def enable(self, job_id: str) -> None:
        self._jobs[job_id].enabled = True
