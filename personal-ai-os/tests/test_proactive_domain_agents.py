from datetime import date

from app.db.connection import get_connection
from app.domains.cross_domain.goal_agent import GoalAgent
from app.domains.cross_domain.goal_store import GoalStore
from app.domains.cross_domain.models import Goal
from app.domains.router import Domain
from app.proactive.commitments import Commitment, CommitmentOwner, CommitmentStore
from app.proactive.goal_monitor import GoalMonitor
from app.proactive.proactive_domain_agents import ProactiveCommitmentAgent, ProactiveDomainAgent


def test_proactive_domain_agent_filters_to_one_domain():
    store = GoalStore(get_connection(":memory:"))
    store.create(Goal(owner_id="alice", title="Career goal", domain=Domain.CAREER))
    store.create(Goal(owner_id="alice", title="Learning goal", domain=Domain.LEARNING))
    monitor = GoalMonitor(GoalAgent(store))
    agent = ProactiveDomainAgent(monitor, domain="CAREER")

    events = agent.check("alice")

    assert len(events) == 1
    assert events[0].payload["title"] == "Career goal"


def test_proactive_domain_agent_returns_empty_for_domain_with_no_goals():
    store = GoalStore(get_connection(":memory:"))
    store.create(Goal(owner_id="alice", title="Career goal", domain=Domain.CAREER))
    monitor = GoalMonitor(GoalAgent(store))
    agent = ProactiveDomainAgent(monitor, domain="FINANCE")

    assert agent.check("alice") == []


def test_proactive_commitment_agent_surfaces_overdue_commitments():
    store = CommitmentStore(get_connection(":memory:"))
    store.save(Commitment(owner_id="alice", description="Send report", owner=CommitmentOwner.USER, due_date=date(2026, 1, 1)))
    agent = ProactiveCommitmentAgent(store)

    events = agent.check("alice", as_of=date(2026, 1, 15))

    assert len(events) == 1
    assert events[0].payload["overdue"] is True


def test_proactive_commitment_agent_no_events_when_nothing_overdue():
    store = CommitmentStore(get_connection(":memory:"))
    agent = ProactiveCommitmentAgent(store)

    assert agent.check("alice") == []
