"""The user's REAL career and finance goals -- given directly by the user,
not fabricated demo data (same convention as
app/dashboard_ui/user_learning_goals.py's 15 real learning goals; see that
module's docstring for why real content is kept in its own clearly-labeled
file rather than mixed into scripts/seed_demo_data.py's fabricated content).

Before this module, GoalStore only held the 15 LEARNING goals -- the
Career and Finance dashboard pages showed separate, unrelated FABRICATED
demo data (app/dashboard_ui/demo_workflow_outputs.py), and Chief of Staff
(app/proactive/chief_of_staff.py, scripts/run_chief_of_staff.py) only ever
watched LEARNING goals. This closes that real gap: Chief of Staff's own
stated role ("track my career, finance (real goals)") requires real Goal
records to track, which didn't exist.

progress/status here are honest, conservative defaults (0.0 / NOT_STARTED)
since these were just created from the user's own stated goals, not
derived from any project artifact -- unlike the learning goals'
code-coverage-proxy scores, there is no project evidence to grade progress
against here. Progress should only change when the user reports real
progress, not when project code changes (these goals are not about this
project).
"""

from app.domains.cross_domain.goal_store import GoalStore
from app.domains.cross_domain.models import Goal, GoalStatus
from app.domains.router import Domain

USER_ID = "demo_user"  # matches scripts/seed_demo_data.py's USER_ID

# (goal_id, title, description, domain, deadline_iso, priority)
CAREER_FINANCE_GOALS: list[tuple[str, str, str, Domain, str | None, float]] = [
    (
        "career_senior_pm_ai_agents",
        "Move to a senior PM role handling AI-agent products",
        "Transition into a senior Product Manager role owning AI-agent products "
        "(not just AI-feature products) -- given directly by the user as their "
        "real, current career goal.",
        Domain.CAREER,
        "2027-06-30",
        0.9,
    ),
    (
        "finance_payoff_education_loan",
        "Pay off education loan",
        "Fully pay off the remaining education loan balance -- given directly by "
        "the user as a real, current finance goal.",
        Domain.FINANCE,
        "2027-12-31",
        0.9,
    ),
    (
        "finance_first_savings_corpus",
        "Build first corpus of savings",
        "Build a first meaningful corpus of savings (the user's own framing: "
        "'my 1st corpus') -- given directly by the user as a real, current "
        "finance goal.",
        Domain.FINANCE,
        "2027-07-31",
        0.7,
    ),
]


def seed_career_finance_goals(store: GoalStore) -> list[Goal]:
    """Idempotent: fixed goal_ids, INSERT OR REPLACE via GoalStore.create()
    (same pattern as seed_learning_capability_goals())."""
    from datetime import date

    goals = []
    for goal_id, title, description, domain, deadline_iso, priority in CAREER_FINANCE_GOALS:
        deadline = date.fromisoformat(deadline_iso) if deadline_iso else None
        goal = Goal(
            goal_id=goal_id, owner_id=USER_ID, title=title, description=description,
            domain=domain, priority=priority, deadline=deadline,
            status=GoalStatus.NOT_STARTED, progress=0.0,
        )
        store.create(goal)
        goals.append(goal)
    return goals
