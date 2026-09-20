from pydantic import BaseModel

from app.proactive.commitments import CommitmentStore
from app.proactive.outcome_tracking import OutcomeStore


class ChiefOfStaffSnapshot(BaseModel):
    """Milestone 43. Same 'data layer only' scope as Phase 2 Milestone 29 and
    Phase 3's dashboard extensions — no Streamlit/web UI, just the queryable
    numbers a Chief of Staff dashboard view would render."""

    open_commitments: int
    overdue_commitments: int
    pending_outcomes: int
    outcome_success_rate: float | None


def get_chief_of_staff_snapshot(
    commitment_store: CommitmentStore, outcome_store: OutcomeStore, owner_id: str
) -> ChiefOfStaffSnapshot:
    all_commitments = commitment_store.list_by_owner(owner_id)
    from app.proactive.commitments import CommitmentStatus

    open_commitments = sum(
        1 for c in all_commitments if c.status in (CommitmentStatus.OPEN, CommitmentStatus.FOLLOWED_UP)
    )
    overdue = len(commitment_store.overdue(owner_id))
    pending_outcomes = len(outcome_store.list_pending(owner_id))
    success_rate = outcome_store.success_rate(owner_id)

    return ChiefOfStaffSnapshot(
        open_commitments=open_commitments, overdue_commitments=overdue,
        pending_outcomes=pending_outcomes, outcome_success_rate=success_rate,
    )
