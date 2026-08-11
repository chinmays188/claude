import pytest

from app.db.connection import get_connection
from app.tasks.models import (
    InvalidTransitionError,
    LongRunningTask,
    TaskState,
)
from app.tasks.store import MaxRetriesExceededError, TaskNotFoundError, TaskStore


def _store() -> TaskStore:
    return TaskStore(get_connection(":memory:"))


def _task(owner="alice", description="Research top AI PM companies") -> LongRunningTask:
    return LongRunningTask(owner=owner, description=description)


def test_create_and_get():
    store = _store()
    task = _task()
    store.create(task)

    result = store.get(task.task_id)

    assert result.description == "Research top AI PM companies"
    assert result.state == TaskState.PENDING


def test_get_missing_task_raises():
    store = _store()

    with pytest.raises(TaskNotFoundError):
        store.get("does-not-exist")


def test_valid_transition_updates_state():
    store = _store()
    task = _task()
    store.create(task)

    updated = store.transition(task.task_id, TaskState.PLANNING)

    assert updated.state == TaskState.PLANNING


def test_invalid_transition_raises_and_does_not_mutate_state():
    store = _store()
    task = _task()
    store.create(task)

    with pytest.raises(InvalidTransitionError):
        store.transition(task.task_id, TaskState.COMPLETED)

    assert store.get(task.task_id).state == TaskState.PENDING


def test_checkpoint_persists_across_transitions():
    store = _store()
    task = _task()
    store.create(task)
    store.transition(task.task_id, TaskState.PLANNING)
    store.transition(task.task_id, TaskState.RUNNING, checkpoint={"step": 2, "found": ["companyA", "companyB"]})

    result = store.get(task.task_id)

    assert result.checkpoint == {"step": 2, "found": ["companyA", "companyB"]}


def test_pause_and_resume():
    store = _store()
    task = _task()
    store.create(task)
    store.transition(task.task_id, TaskState.PLANNING)
    store.transition(task.task_id, TaskState.RUNNING)

    paused = store.pause(task.task_id)
    assert paused.state == TaskState.PAUSED

    resumed = store.resume(task.task_id)
    assert resumed.state == TaskState.RUNNING


def test_cancel_from_pending():
    store = _store()
    task = _task()
    store.create(task)

    cancelled = store.cancel(task.task_id)

    assert cancelled.state == TaskState.CANCELLED


def test_retry_increments_count_and_moves_to_recovery():
    store = _store()
    task = _task()
    store.create(task)
    store.transition(task.task_id, TaskState.PLANNING)
    store.transition(task.task_id, TaskState.RUNNING)
    store.transition(task.task_id, TaskState.FAILED)

    retried = store.retry(task.task_id)

    assert retried.state == TaskState.RECOVERY
    assert retried.retry_count == 1


def test_retry_exhausted_raises():
    store = _store()
    task = _task()
    task.max_retries = 1
    store.create(task)
    store.transition(task.task_id, TaskState.PLANNING)
    store.transition(task.task_id, TaskState.RUNNING)
    store.transition(task.task_id, TaskState.FAILED)
    store.retry(task.task_id)
    store.transition(task.task_id, TaskState.RUNNING)
    store.transition(task.task_id, TaskState.FAILED)

    with pytest.raises(MaxRetriesExceededError):
        store.retry(task.task_id)


def test_update_progress_clamped_to_0_1_range():
    store = _store()
    task = _task()
    store.create(task)

    store.update_progress(task.task_id, 1.5)
    assert store.get(task.task_id).progress == 1.0

    store.update_progress(task.task_id, -0.5)
    assert store.get(task.task_id).progress == 0.0


def test_list_by_owner_scoped_correctly():
    store = _store()
    store.create(_task(owner="alice"))
    store.create(_task(owner="bob"))

    results = store.list_by_owner("alice")

    assert len(results) == 1
    assert results[0].owner == "alice"


def test_task_survives_across_store_instances_with_same_connection():
    conn = get_connection(":memory:")
    store1 = TaskStore(conn)
    task = _task()
    store1.create(task)

    store2 = TaskStore(conn)
    result = store2.get(task.task_id)

    assert result.task_id == task.task_id
