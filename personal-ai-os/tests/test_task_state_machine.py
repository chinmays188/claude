import pytest

from app.tasks.models import InvalidTransitionError, TaskState, validate_transition


def test_pending_to_planning_is_valid():
    validate_transition(TaskState.PENDING, TaskState.PLANNING)  # should not raise


def test_running_to_completed_is_valid():
    validate_transition(TaskState.RUNNING, TaskState.COMPLETED)


def test_failed_to_recovery_is_valid():
    validate_transition(TaskState.FAILED, TaskState.RECOVERY)


def test_recovery_to_running_is_valid():
    validate_transition(TaskState.RECOVERY, TaskState.RUNNING)


def test_pending_to_completed_is_invalid():
    with pytest.raises(InvalidTransitionError):
        validate_transition(TaskState.PENDING, TaskState.COMPLETED)


def test_completed_is_terminal():
    with pytest.raises(InvalidTransitionError):
        validate_transition(TaskState.COMPLETED, TaskState.RUNNING)


def test_cancelled_is_terminal():
    with pytest.raises(InvalidTransitionError):
        validate_transition(TaskState.CANCELLED, TaskState.RUNNING)


def test_running_to_paused_and_back_is_valid():
    validate_transition(TaskState.RUNNING, TaskState.PAUSED)
    validate_transition(TaskState.PAUSED, TaskState.RUNNING)
