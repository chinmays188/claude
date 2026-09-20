from datetime import date

from app.dashboard.chief_of_staff_data import get_chief_of_staff_snapshot
from app.db.connection import get_connection
from app.proactive.commitments import Commitment, CommitmentOwner, CommitmentStatus, CommitmentStore
from app.proactive.outcome_tracking import Outcome, OutcomeStatus, OutcomeStore


def test_snapshot_counts_open_and_overdue_commitments():
    commitment_store = CommitmentStore(get_connection(":memory:"))
    outcome_store = OutcomeStore(get_connection(":memory:"))
    commitment_store.save(Commitment(owner_id="alice", description="Send report", owner=CommitmentOwner.USER, due_date=date(2026, 1, 1)))
    commitment_store.save(Commitment(owner_id="alice", description="Future task", owner=CommitmentOwner.USER, due_date=date(2027, 1, 1)))

    snapshot = get_chief_of_staff_snapshot(commitment_store, outcome_store, "alice")

    assert snapshot.open_commitments == 2
    assert snapshot.overdue_commitments == 1


def test_snapshot_reports_none_success_rate_when_nothing_resolved():
    commitment_store = CommitmentStore(get_connection(":memory:"))
    outcome_store = OutcomeStore(get_connection(":memory:"))

    snapshot = get_chief_of_staff_snapshot(commitment_store, outcome_store, "alice")

    assert snapshot.outcome_success_rate is None
    assert snapshot.pending_outcomes == 0


def test_snapshot_reports_pending_and_success_rate():
    commitment_store = CommitmentStore(get_connection(":memory:"))
    outcome_store = OutcomeStore(get_connection(":memory:"))
    outcome_store.record(Outcome(action_id="a1", owner_id="alice", expected_result="x"))
    resolved = Outcome(action_id="a2", owner_id="alice", expected_result="y")
    outcome_store.record(resolved)
    outcome_store.resolve(resolved.outcome_id, OutcomeStatus.ACHIEVED, "worked")

    snapshot = get_chief_of_staff_snapshot(commitment_store, outcome_store, "alice")

    assert snapshot.pending_outcomes == 1
    assert snapshot.outcome_success_rate == 1.0
