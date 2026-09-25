from datetime import date

from app.domains.cross_domain.goal_agent import GoalAgent
from app.domains.cross_domain.models import Goal, GoalStatus
from app.proactive.events import Event, EventType


class GoalMonitor:
    """Milestone 34: bridges Phase 3's GoalAgent/GoalStore to Phase 4's event
    system. 'Goal-risk detection' (Phase 4 core concept) means turning goal
    state into GOAL_UPDATED events the TriggerEngine's
    GoalDeadlineApproachingTrigger (Milestone 30-31) can then act on — this
    class does not duplicate risk-scoring logic, it only computes the payload
    fields (days_remaining, progress) that trigger already expects."""

    def __init__(self, goal_agent: GoalAgent):
        self._goal_agent = goal_agent

    def check_goals(self, owner_id: str, as_of: date | None = None) -> list[Event]:
        as_of = as_of or date.today()
        goals = self._goal_agent.recommend_priorities(owner_id)  # active goals only, already excludes completed/abandoned

        events = []
        for goal in goals:
            events.append(self._to_event(goal, as_of))
        return events

    def _to_event(self, goal: Goal, as_of: date) -> Event:
        days_remaining = (goal.deadline - as_of).days if goal.deadline else None
        return Event(
            type=EventType.GOAL_UPDATED,
            owner_id=goal.owner_id,
            payload={
                "goal_id": goal.goal_id,
                "title": goal.title,
                "progress": goal.progress,
                "days_remaining": days_remaining,
                "status": goal.status.value,
                "domain": goal.domain.value,
                # Added so a deadline-less goal (days_remaining is None) can
                # still be evaluated for staleness by a trigger that doesn't
                # depend on a deadline -- see StalledGoalTrigger.
                "updated_at": goal.updated_at.isoformat(),
            },
            source="goal_monitor",
        )
