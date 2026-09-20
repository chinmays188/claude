from pydantic import BaseModel, Field

from app.domains.cross_domain.goal_store import GoalStore
from app.domains.router import Domain


class CareerDashboard(BaseModel):
    """Section 48's exact fields."""

    applications: int = 0
    resume_readiness: float | None = None  # 0.0-1.0
    interview_readiness: float | None = None
    skill_gaps: list[str] = Field(default_factory=list)
    career_goals_count: int = 0


class PmDashboard(BaseModel):
    """Section 49's exact fields."""

    feedback_themes: list[str] = Field(default_factory=list)
    open_requests: int = 0
    sprint_status: str = "unknown"
    commitments_count: int = 0
    project_risks: list[str] = Field(default_factory=list)


class FinanceDashboard(BaseModel):
    """Section 50's exact fields."""

    portfolio_value: float | None = None
    allocation: dict[str, float] = Field(default_factory=dict)
    goals_count: int = 0
    loans_count: int = 0
    risk_indicators: list[str] = Field(default_factory=list)


class LearningDashboard(BaseModel):
    """Section 51's exact fields."""

    current_subjects: list[str] = Field(default_factory=list)
    progress: dict[str, float] = Field(default_factory=dict)  # concept -> average_score/10
    knowledge_gaps: list[str] = Field(default_factory=list)
    exercises_completed: int = 0
    assessment_scores: dict[str, float] = Field(default_factory=dict)
    learning_goals_count: int = 0


def get_career_dashboard(
    goal_store: GoalStore, owner_id: str,
    applications: int = 0, resume_readiness: float | None = None,
    interview_readiness: float | None = None, skill_gaps: list[str] | None = None,
) -> CareerDashboard:
    """Section 48. Goal count is pulled from the shared GoalStore (Section 33-34);
    applications/readiness/gaps are supplied by the caller since those come
    from Career OS's own workflows (jd_analysis, resume_optimization), not
    something this dashboard module computes itself."""
    goals = goal_store.list_by_owner(owner_id)
    career_goals = [g for g in goals if g.domain == Domain.CAREER]
    return CareerDashboard(
        applications=applications, resume_readiness=resume_readiness,
        interview_readiness=interview_readiness, skill_gaps=skill_gaps or [],
        career_goals_count=len(career_goals),
    )


def get_pm_dashboard(
    feedback_themes: list[str] | None = None, open_requests: int = 0,
    sprint_status: str = "unknown", commitments_count: int = 0, project_risks: list[str] | None = None,
) -> PmDashboard:
    """Section 49. All fields are caller-supplied from PM OS's own workflow
    outputs (feedback_intelligence, stakeholder_request, sprint_planner) —
    this function's only job is shaping them into the dashboard's schema."""
    return PmDashboard(
        feedback_themes=feedback_themes or [], open_requests=open_requests,
        sprint_status=sprint_status, commitments_count=commitments_count,
        project_risks=project_risks or [],
    )


def get_finance_dashboard(
    goal_store: GoalStore, owner_id: str,
    portfolio_value: float | None = None, allocation: dict[str, float] | None = None,
    loans_count: int = 0, risk_indicators: list[str] | None = None,
) -> FinanceDashboard:
    """Section 50. portfolio_value/allocation should come from
    calculations.py's deterministic output (Section 24), never an LLM
    estimate — this function does not compute them, only displays them."""
    goals = goal_store.list_by_owner(owner_id)
    finance_goals = [g for g in goals if g.domain == Domain.FINANCE]
    return FinanceDashboard(
        portfolio_value=portfolio_value, allocation=allocation or {},
        goals_count=len(finance_goals), loans_count=loans_count,
        risk_indicators=risk_indicators or [],
    )


def get_learning_dashboard(
    goal_store: GoalStore, owner_id: str,
    current_subjects: list[str] | None = None, progress: dict[str, float] | None = None,
    knowledge_gaps: list[str] | None = None, exercises_completed: int = 0,
    assessment_scores: dict[str, float] | None = None,
) -> LearningDashboard:
    """Section 51. progress/knowledge_gaps are naturally sourced from
    AdaptiveLoop's LearningProgress per concept (Milestone Learning OS,
    Section 29) — passed in by the caller rather than recomputed here."""
    goals = goal_store.list_by_owner(owner_id)
    learning_goals = [g for g in goals if g.domain == Domain.LEARNING]
    return LearningDashboard(
        current_subjects=current_subjects or [], progress=progress or {},
        knowledge_gaps=knowledge_gaps or [], exercises_completed=exercises_completed,
        assessment_scores=assessment_scores or {}, learning_goals_count=len(learning_goals),
    )
