import time

import pytest

from app.guardrails.budgets import AgentBudget, BudgetExceededError, BudgetTracker


def test_records_within_budget_without_error():
    tracker = BudgetTracker(AgentBudget(max_turns=3, max_tool_calls=3))

    tracker.record_turn()
    tracker.record_tool_call()

    assert tracker.turns == 1
    assert tracker.tool_calls == 1


def test_exceeding_max_turns_raises():
    tracker = BudgetTracker(AgentBudget(max_turns=2))

    tracker.record_turn()
    tracker.record_turn()
    with pytest.raises(BudgetExceededError):
        tracker.record_turn()


def test_exceeding_max_tool_calls_raises():
    tracker = BudgetTracker(AgentBudget(max_tool_calls=1))

    tracker.record_tool_call()
    with pytest.raises(BudgetExceededError):
        tracker.record_tool_call()


def test_exceeding_max_tokens_raises():
    tracker = BudgetTracker(AgentBudget(max_tokens=100))

    tracker.record_tokens(60)
    with pytest.raises(BudgetExceededError):
        tracker.record_tokens(60)


def test_no_token_limit_by_default():
    tracker = BudgetTracker(AgentBudget())

    tracker.record_tokens(1_000_000)  # should not raise


def test_exceeding_max_retries_raises():
    tracker = BudgetTracker(AgentBudget(max_retries=1))

    tracker.record_retry()
    with pytest.raises(BudgetExceededError):
        tracker.record_retry()


def test_timeout_raises_after_elapsed_time():
    tracker = BudgetTracker(AgentBudget(timeout_seconds=0.05))

    time.sleep(0.1)
    with pytest.raises(BudgetExceededError):
        tracker.record_turn()
