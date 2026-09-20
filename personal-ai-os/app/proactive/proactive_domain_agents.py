from datetime import date

from app.proactive.commitments import CommitmentStore
from app.proactive.events import Event, EventType
from app.proactive.goal_monitor import GoalMonitor


class ProactiveDomainAgent:
    """Milestone 40: a proactive check scoped to one domain, built on top of
    GoalMonitor (Milestone 34) rather than duplicating goal-risk logic per
    domain. GoalMonitor's events carry `payload['domain']`, so filtering to a
    single domain is a real, verifiable filter, not a stub."""

    def __init__(self, goal_monitor: GoalMonitor, domain: str):
        self._goal_monitor = goal_monitor
        self._domain = domain

    def check(self, owner_id: str, as_of: date | None = None) -> list[Event]:
        all_events = self._goal_monitor.check_goals(owner_id, as_of)
        return [e for e in all_events if e.payload.get("domain") == self._domain]


class ProactiveCommitmentAgent:
    """Milestone 40: reuses Milestone 33's CommitmentStore to surface overdue
    commitments as events, so they flow through the same trigger/attention
    pipeline as everything else rather than a separate notification path."""

    def __init__(self, commitment_store: CommitmentStore):
        self._store = commitment_store

    def check(self, owner_id: str, as_of: date | None = None) -> list[Event]:
        overdue = self._store.overdue(owner_id, as_of)
        return [
            Event(
                type=EventType.COMMITMENT_DETECTED, owner_id=owner_id,
                payload={"commitment_id": c.commitment_id, "description": c.description, "overdue": True},
                source="proactive_commitment_agent",
            )
            for c in overdue
        ]


def all_domains_agent(goal_monitor: GoalMonitor) -> GoalMonitor:
    """Milestone 40: when a caller wants every domain's goal-risk events
    unfiltered (e.g. a Chief of Staff orchestrator combining all domains,
    Milestone 41), GoalMonitor itself is already exactly that — this function
    exists only so the intent ('give me the all-domains proactive check') is
    named explicitly at call sites, without a redundant wrapper class around
    a single delegating method."""
    return goal_monitor
