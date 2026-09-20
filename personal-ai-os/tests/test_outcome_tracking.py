import pytest

from app.db.connection import get_connection
from app.proactive.outcome_tracking import (
    Outcome,
    OutcomeNotFoundError,
    OutcomeStatus,
    OutcomeStore,
)


def _store() -> OutcomeStore:
    return OutcomeStore(get_connection(":memory:"))


def test_record_and_get():
    store = _store()
    outcome = Outcome(action_id="a1", owner_id="alice", expected_result="stakeholder replies")
    store.record(outcome)

    result = store.get(outcome.outcome_id)

    assert result.status == OutcomeStatus.PENDING


def test_get_missing_raises():
    store = _store()

    with pytest.raises(OutcomeNotFoundError):
        store.get("does-not-exist")


def test_resolve_updates_status_and_result():
    store = _store()
    outcome = Outcome(action_id="a1", owner_id="alice", expected_result="stakeholder replies")
    store.record(outcome)

    resolved = store.resolve(outcome.outcome_id, OutcomeStatus.ACHIEVED, "Stakeholder replied within a day.")

    assert resolved.status == OutcomeStatus.ACHIEVED
    assert resolved.resolved_at is not None


def test_list_pending_excludes_resolved():
    store = _store()
    pending = Outcome(action_id="a1", owner_id="alice", expected_result="x")
    resolved = Outcome(action_id="a2", owner_id="alice", expected_result="y")
    store.record(pending)
    store.record(resolved)
    store.resolve(resolved.outcome_id, OutcomeStatus.ACHIEVED, "done")

    pending_list = store.list_pending("alice")

    assert len(pending_list) == 1
    assert pending_list[0].outcome_id == pending.outcome_id


def test_success_rate_none_when_nothing_resolved():
    store = _store()
    store.record(Outcome(action_id="a1", owner_id="alice", expected_result="x"))

    assert store.success_rate("alice") is None


def test_success_rate_computed_correctly():
    store = _store()
    o1 = Outcome(action_id="a1", owner_id="alice", expected_result="x")
    o2 = Outcome(action_id="a2", owner_id="alice", expected_result="y")
    store.record(o1)
    store.record(o2)
    store.resolve(o1.outcome_id, OutcomeStatus.ACHIEVED, "worked")
    store.resolve(o2.outcome_id, OutcomeStatus.FAILED, "did not work")

    assert store.success_rate("alice") == 0.5
