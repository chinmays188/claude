from datetime import datetime, timedelta, timezone

import pytest

from app.proactive.scheduler import ScheduledJob, ScheduleKind, Scheduler


def test_interval_job_due_when_never_run():
    scheduler = Scheduler()
    job = ScheduledJob(name="daily_brief", kind=ScheduleKind.INTERVAL, interval_seconds=3600)
    scheduler.register(job, callback=lambda: None)

    due = scheduler.due_jobs()

    assert len(due) == 1


def test_interval_job_not_due_before_interval_elapsed():
    scheduler = Scheduler()
    now = datetime.now(timezone.utc)
    job = ScheduledJob(name="daily_brief", kind=ScheduleKind.INTERVAL, interval_seconds=3600, last_run_at=now)
    scheduler.register(job, callback=lambda: None)

    due = scheduler.due_jobs(now=now + timedelta(minutes=10))

    assert due == []


def test_interval_job_due_after_interval_elapsed():
    scheduler = Scheduler()
    now = datetime.now(timezone.utc)
    job = ScheduledJob(name="daily_brief", kind=ScheduleKind.INTERVAL, interval_seconds=3600, last_run_at=now)
    scheduler.register(job, callback=lambda: None)

    due = scheduler.due_jobs(now=now + timedelta(hours=2))

    assert len(due) == 1


def test_disabled_job_never_due():
    scheduler = Scheduler()
    job = ScheduledJob(name="daily_brief", kind=ScheduleKind.INTERVAL, interval_seconds=3600, enabled=False)
    scheduler.register(job, callback=lambda: None)

    assert scheduler.due_jobs() == []


def test_tick_runs_due_jobs_and_marks_last_run():
    scheduler = Scheduler()
    calls = []
    job = ScheduledJob(name="daily_brief", kind=ScheduleKind.INTERVAL, interval_seconds=3600)
    scheduler.register(job, callback=lambda: calls.append(1))

    ran = scheduler.tick()

    assert ran == [job.job_id]
    assert len(calls) == 1
    assert scheduler._jobs[job.job_id].last_run_at is not None


def test_tick_does_not_rerun_job_before_interval():
    scheduler = Scheduler()
    calls = []
    job = ScheduledJob(name="daily_brief", kind=ScheduleKind.INTERVAL, interval_seconds=3600)
    scheduler.register(job, callback=lambda: calls.append(1))

    now = datetime.now(timezone.utc)
    scheduler.tick(now=now)
    scheduler.tick(now=now + timedelta(minutes=5))

    assert len(calls) == 1


def test_event_driven_job_runs_on_notify_not_on_tick():
    scheduler = Scheduler()
    calls = []
    job = ScheduledJob(name="urgent_email", kind=ScheduleKind.EVENT_DRIVEN)
    scheduler.register(job, callback=lambda: calls.append(1))

    scheduler.tick()  # should not run event-driven jobs
    assert calls == []

    ran = scheduler.notify_event("urgent_email")
    assert ran == [job.job_id]
    assert len(calls) == 1


def test_interval_job_requires_interval_seconds():
    scheduler = Scheduler()
    job = ScheduledJob(name="bad_job", kind=ScheduleKind.INTERVAL, interval_seconds=None)

    with pytest.raises(ValueError):
        scheduler.register(job, callback=lambda: None)


def test_disable_and_enable_job():
    scheduler = Scheduler()
    job = ScheduledJob(name="daily_brief", kind=ScheduleKind.INTERVAL, interval_seconds=3600)
    scheduler.register(job, callback=lambda: None)

    scheduler.disable(job.job_id)
    assert scheduler.due_jobs() == []

    scheduler.enable(job.job_id)
    assert len(scheduler.due_jobs()) == 1
