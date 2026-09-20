from datetime import date, datetime, timedelta, timezone

import pytest

from app.db.connection import get_connection
from app.domains.cross_domain.goal_agent import GoalAgent
from app.domains.cross_domain.goal_store import GoalStore
from app.domains.cross_domain.models import Goal, GoalStatus
from app.domains.router import Domain
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _agent(llm=None) -> GoalAgent:
    return GoalAgent(GoalStore(get_connection(":memory:")), llm=llm)


def _goal(owner="alice", title="Goal", domain=Domain.CAREER, priority=0.5, deadline=None, dependencies=None) -> Goal:
    return Goal(owner_id=owner, title=title, domain=domain, priority=priority, deadline=deadline, dependencies=dependencies or [])


def test_track_persists_goal():
    agent = _agent()
    goal = _goal()

    agent.track(goal)

    assert agent._store.get(goal.goal_id).title == "Goal"


def test_dependency_status_all_complete():
    agent = _agent()
    dep1 = _goal(title="Resume complete")
    agent.track(dep1)
    agent._store.update_status(dep1.goal_id, GoalStatus.COMPLETED)
    main_goal = _goal(title="Prepare for interviews", dependencies=[dep1.goal_id])
    agent.track(main_goal)

    status = agent.dependency_status(main_goal.goal_id)

    assert status.all_dependencies_complete is True
    assert status.dependency_goals[0].title == "Resume complete"


def test_dependency_status_not_all_complete():
    agent = _agent()
    dep1 = _goal(title="Incomplete dep")
    agent.track(dep1)
    main_goal = _goal(title="Main goal", dependencies=[dep1.goal_id])
    agent.track(main_goal)

    status = agent.dependency_status(main_goal.goal_id)

    assert status.all_dependencies_complete is False


def test_detect_conflict_requires_llm():
    agent = _agent(llm=None)
    g1 = _goal(title="Goal A")
    g2 = _goal(title="Goal B")
    agent.track(g1)
    agent.track(g2)

    with pytest.raises(ValueError):
        agent.detect_conflict(g1.goal_id, g2.goal_id)


def test_detect_conflict_returns_conflict_when_llm_says_so():
    llm = ScriptedProvider(['{"conflicts": true, "reason": "Both require the same weekend hours."}'])
    agent = _agent(llm=llm)
    g1 = _goal(title="Weekend interview prep")
    g2 = _goal(title="Weekend Kubernetes course")
    agent.track(g1)
    agent.track(g2)

    conflict = agent.detect_conflict(g1.goal_id, g2.goal_id)

    assert conflict is not None
    assert "weekend" in conflict.reason.lower()


def test_detect_conflict_returns_none_when_no_conflict():
    llm = ScriptedProvider(['{"conflicts": false, "reason": "They do not compete for the same time or resources."}'])
    agent = _agent(llm=llm)
    g1 = _goal(title="Learn Docker")
    g2 = _goal(title="Save for a house")
    agent.track(g1)
    agent.track(g2)

    conflict = agent.detect_conflict(g1.goal_id, g2.goal_id)

    assert conflict is None


def test_recommend_priorities_sorts_by_priority_and_deadline():
    agent = _agent()
    today = date.today()
    low_priority = _goal(title="Low", priority=0.2)
    high_priority_far_deadline = _goal(title="HighFar", priority=0.9, deadline=today + timedelta(days=90))
    high_priority_near_deadline = _goal(title="HighNear", priority=0.9, deadline=today + timedelta(days=5))
    agent.track(low_priority)
    agent.track(high_priority_far_deadline)
    agent.track(high_priority_near_deadline)

    ranked = agent.recommend_priorities("alice")

    assert ranked[0].title == "HighNear"
    assert ranked[1].title == "HighFar"
    assert ranked[2].title == "Low"


def test_recommend_priorities_excludes_completed_and_abandoned():
    agent = _agent()
    done = _goal(title="Done", priority=0.9)
    agent.track(done)
    agent._store.update_status(done.goal_id, GoalStatus.COMPLETED)
    active = _goal(title="Active", priority=0.1)
    agent.track(active)

    ranked = agent.recommend_priorities("alice")

    assert [g.title for g in ranked] == ["Active"]


def test_neglected_goals_flags_stale_in_progress_goal():
    agent = _agent()
    stale_goal = _goal(title="Stale goal")
    stale_goal.status = GoalStatus.IN_PROGRESS
    stale_goal.updated_at = datetime.now(timezone.utc) - timedelta(days=40)
    agent.track(stale_goal)

    neglected = agent.neglected_goals("alice", staleness_days=30)

    assert len(neglected) == 1
    assert neglected[0].title == "Stale goal"


def test_neglected_goals_ignores_recently_updated_goal():
    agent = _agent()
    fresh_goal = _goal(title="Fresh goal")
    fresh_goal.status = GoalStatus.IN_PROGRESS
    agent.track(fresh_goal)

    neglected = agent.neglected_goals("alice", staleness_days=30)

    assert neglected == []


def test_neglected_goals_ignores_completed_goals():
    agent = _agent()
    old_completed = _goal(title="Old completed")
    old_completed.status = GoalStatus.COMPLETED
    old_completed.updated_at = datetime.now(timezone.utc) - timedelta(days=100)
    agent.track(old_completed)

    neglected = agent.neglected_goals("alice", staleness_days=30)

    assert neglected == []
