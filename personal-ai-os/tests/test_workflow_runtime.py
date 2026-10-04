import pytest

from app.db.connection import get_connection
from app.platform.queue import JobQueue, JobStatus
from app.platform.workflow_runtime import WorkflowHandler, WorkflowRuntime
from app.tasks.models import TaskState
from app.tasks.store import TaskStore


class EchoHandler(WorkflowHandler):
    def run(self, payload: dict) -> str:
        return f"echoed: {payload.get('message')}"


class FailingHandler(WorkflowHandler):
    def run(self, payload: dict) -> str:
        raise RuntimeError("handler blew up")


def _runtime(handlers: dict) -> WorkflowRuntime:
    return WorkflowRuntime(JobQueue(get_connection(":memory:")), TaskStore(get_connection(":memory:")), handlers)


def test_submit_creates_task_and_enqueues_job():
    runtime = _runtime({"echo": EchoHandler()})

    task = runtime.submit("alice", "echo", {"message": "hi"})

    assert task.state == TaskState.PENDING


def test_submit_rejects_unregistered_workflow_type():
    runtime = _runtime({})

    with pytest.raises(ValueError):
        runtime.submit("alice", "unknown_workflow", {})


def test_process_one_completes_task_on_success():
    queue = JobQueue(get_connection(":memory:"))
    task_store = TaskStore(get_connection(":memory:"))
    runtime = WorkflowRuntime(queue, task_store, {"echo": EchoHandler()})
    task = runtime.submit("alice", "echo", {"message": "hi"})

    job = runtime.process_one()

    assert job is not None
    completed_task = task_store.get(task.task_id)
    assert completed_task.state == TaskState.COMPLETED
    assert "echoed: hi" in completed_task.result


def test_process_one_marks_task_failed_on_handler_error():
    queue = JobQueue(get_connection(":memory:"))
    task_store = TaskStore(get_connection(":memory:"))
    runtime = WorkflowRuntime(queue, task_store, {"broken": FailingHandler()})
    task = runtime.submit("alice", "broken", {})

    runtime.process_one()

    failed_task = task_store.get(task.task_id)
    assert failed_task.state == TaskState.FAILED


def test_process_one_returns_the_real_post_completion_job_status():
    """Real bug fixed: process_one() used to return the stale local `job`
    captured before self._queue.complete() ran, so .status still read
    IN_PROGRESS even though the real row in the database was SUCCEEDED --
    found while running a real job through this runtime for the first
    time (scripts/run_production_drills.py)."""
    queue = JobQueue(get_connection(":memory:"))
    task_store = TaskStore(get_connection(":memory:"))
    runtime = WorkflowRuntime(queue, task_store, {"echo": EchoHandler()})
    runtime.submit("alice", "echo", {"message": "hi"})

    job = runtime.process_one()

    assert job.status == JobStatus.SUCCEEDED
    # Confirm it's not just a local mutation -- the real row agrees too.
    assert queue.get(job.job_id).status == JobStatus.SUCCEEDED


def test_process_one_returns_the_real_post_failure_job_status():
    queue = JobQueue(get_connection(":memory:"))
    task_store = TaskStore(get_connection(":memory:"))
    runtime = WorkflowRuntime(queue, task_store, {"broken": FailingHandler()})
    runtime.submit("alice", "broken", {})

    job = runtime.process_one()

    # A single failure with the default max_attempts=3 goes back to QUEUED
    # (real retry semantics), not straight to FAILED/DEAD_LETTER.
    assert job.status == JobStatus.QUEUED
    assert job.error == "handler blew up"


def test_process_one_returns_none_when_nothing_queued():
    runtime = _runtime({"echo": EchoHandler()})

    assert runtime.process_one() is None
