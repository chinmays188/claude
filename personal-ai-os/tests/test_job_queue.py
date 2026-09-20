import pytest

from app.db.connection import get_connection
from app.platform.queue import JobNotFoundError, JobQueue, JobStatus


def _queue() -> JobQueue:
    return JobQueue(get_connection(":memory:"))


def test_enqueue_and_dequeue():
    queue = _queue()
    queue.enqueue("emails", {"to": "a@b.com"})

    job = queue.dequeue("emails")

    assert job is not None
    assert job.status == JobStatus.IN_PROGRESS
    assert job.attempts == 1


def test_dequeue_empty_queue_returns_none():
    queue = _queue()

    assert queue.dequeue("emails") is None


def test_dequeue_respects_queue_name():
    queue = _queue()
    queue.enqueue("emails", {"to": "a@b.com"})

    assert queue.dequeue("other_queue") is None


def test_dequeue_fifo_order():
    queue = _queue()
    queue.enqueue("emails", {"order": 1})
    queue.enqueue("emails", {"order": 2})

    first = queue.dequeue("emails")
    queue.complete(first.job_id)
    second = queue.dequeue("emails")

    assert first.payload["order"] == 1
    assert second.payload["order"] == 2


def test_complete_marks_succeeded():
    queue = _queue()
    job = queue.enqueue("emails", {})
    queue.dequeue("emails")

    completed = queue.complete(job.job_id)

    assert completed.status == JobStatus.SUCCEEDED


def test_fail_requeues_when_attempts_remain():
    queue = _queue()
    job = queue.enqueue("emails", {}, max_attempts=3)
    queue.dequeue("emails")

    failed = queue.fail(job.job_id, "temporary error")

    assert failed.status == JobStatus.QUEUED
    assert failed.error == "temporary error"


def test_fail_moves_to_dead_letter_after_max_attempts():
    queue = _queue()
    job = queue.enqueue("emails", {}, max_attempts=1)
    queue.dequeue("emails")

    failed = queue.fail(job.job_id, "permanent error")

    assert failed.status == JobStatus.DEAD_LETTER


def test_dead_letter_jobs_lists_only_dead_letters():
    queue = _queue()
    job1 = queue.enqueue("emails", {}, max_attempts=1)
    queue.dequeue("emails")
    queue.fail(job1.job_id, "fatal")
    queue.enqueue("emails", {})  # still queued

    dead = queue.dead_letter_jobs("emails")

    assert len(dead) == 1
    assert dead[0].job_id == job1.job_id


def test_get_missing_job_raises():
    queue = _queue()

    with pytest.raises(JobNotFoundError):
        queue.get("does-not-exist")


def test_job_survives_across_queue_instances():
    conn = get_connection(":memory:")
    queue1 = JobQueue(conn)
    job = queue1.enqueue("emails", {"x": 1})

    queue2 = JobQueue(conn)
    result = queue2.get(job.job_id)

    assert result.payload == {"x": 1}
