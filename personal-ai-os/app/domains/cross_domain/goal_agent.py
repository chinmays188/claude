from datetime import date, datetime, timezone

from pydantic import BaseModel

from app.domains.cross_domain.goal_store import GoalStore
from app.domains.cross_domain.models import Goal, GoalConflict, GoalStatus
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

CONFLICT_PROMPT = """Two of this user's goals may conflict (competing for the
same time/resources, or working against each other). Analyze ONLY the two
goals below — do not invent details not present in their descriptions.

Goal A: {goal_a}
Goal B: {goal_b}

Respond with ONLY a JSON object:
{{"conflicts": true | false, "reason": "<why they conflict, or why they don't>"}}
"""


class _ConflictCheck(BaseModel):
    conflicts: bool
    reason: str


class GoalDependencyStatus(BaseModel):
    goal: Goal
    dependency_goals: list[Goal]
    all_dependencies_complete: bool


class GoalAgent:
    """Section 34's responsibilities: track goals, detect conflicts, identify
    dependencies, track progress, recommend priorities, surface neglected
    goals. Wraps GoalStore rather than duplicating persistence."""

    def __init__(self, store: GoalStore, llm: LLMProvider | None = None):
        self._store = store
        self._llm = llm

    def track(self, goal: Goal) -> None:
        self._store.create(goal)

    def dependency_status(self, goal_id: str) -> GoalDependencyStatus:
        """Section 34: 'Identify dependencies.' Resolves a goal's declared
        dependency ids into full Goal objects and reports whether all of them
        are complete."""
        goal = self._store.get(goal_id)
        dependency_goals = [self._store.get(dep_id) for dep_id in goal.dependencies]
        all_complete = all(dep.status == GoalStatus.COMPLETED for dep in dependency_goals)
        return GoalDependencyStatus(
            goal=goal, dependency_goals=dependency_goals, all_dependencies_complete=all_complete
        )

    def detect_conflict(self, goal_id_a: str, goal_id_b: str) -> GoalConflict | None:
        """Section 34: 'Detect conflicts.' Requires an LLM (goal conflicts are
        a judgment call about competing time/resources, not a deterministic
        check) — raises if none was configured."""
        if self._llm is None:
            raise ValueError("detect_conflict requires an LLMProvider to be configured on this GoalAgent.")

        goal_a = self._store.get(goal_id_a)
        goal_b = self._store.get(goal_id_b)

        generator = RepairableGenerator(self._llm, _ConflictCheck)
        prompt = CONFLICT_PROMPT.format(
            goal_a=f"{goal_a.title}: {goal_a.description}", goal_b=f"{goal_b.title}: {goal_b.description}"
        )
        result = generator.generate(prompt)

        if not result.conflicts:
            return None
        return GoalConflict(goal_id_a=goal_id_a, goal_id_b=goal_id_b, reason=result.reason)

    def recommend_priorities(self, owner_id: str) -> list[Goal]:
        """Section 34: 'Recommend priorities.' Deterministic ranking by
        declared priority and deadline proximity — not an LLM call, since
        this is a sortable, auditable ranking, not a judgment call."""
        goals = self._store.list_by_owner(owner_id)
        active = [g for g in goals if g.status not in (GoalStatus.COMPLETED, GoalStatus.ABANDONED)]

        def sort_key(g: Goal) -> tuple:
            days_to_deadline = (g.deadline - date.today()).days if g.deadline else 9999
            return (-g.priority, days_to_deadline)

        return sorted(active, key=sort_key)

    def neglected_goals(self, owner_id: str, staleness_days: int = 30) -> list[Goal]:
        """Section 34: 'Surface neglected goals.' A goal not updated in
        staleness_days and still in progress is neglected — deterministic,
        auditable definition rather than an LLM judgment call."""
        now = datetime.now(timezone.utc)
        goals = self._store.list_by_owner(owner_id)
        neglected = []
        for goal in goals:
            if goal.status not in (GoalStatus.IN_PROGRESS, GoalStatus.NOT_STARTED, GoalStatus.BLOCKED):
                continue
            updated_at = goal.updated_at if goal.updated_at.tzinfo else goal.updated_at.replace(tzinfo=timezone.utc)
            age_days = (now - updated_at).total_seconds() / 86400
            if age_days >= staleness_days:
                neglected.append(goal)
        return neglected
