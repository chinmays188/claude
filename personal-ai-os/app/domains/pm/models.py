from enum import Enum

from pydantic import BaseModel, Field


class FeedbackTheme(BaseModel):
    theme: str
    frequency: int
    severity: float  # 0.0-1.0
    customer_impact: str
    trend: str  # "emerging" | "declining" | "stable"


class FeedbackIntelligenceResult(BaseModel):
    """Section 15's exact output fields."""

    top_themes: list[FeedbackTheme] = Field(default_factory=list)
    emerging_themes: list[str] = Field(default_factory=list)
    declining_themes: list[str] = Field(default_factory=list)
    critical_issues: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class StakeholderRecommendation(str, Enum):
    """Section 16's exact possible outputs."""

    BUILD = "BUILD"
    INVESTIGATE = "INVESTIGATE"
    REJECT = "REJECT"
    DEFER = "DEFER"
    NEED_MORE_EVIDENCE = "NEED_MORE_EVIDENCE"


class StakeholderRequestAnalysis(BaseModel):
    request: str
    problem_extracted: str
    user_impact: str
    recommendation: StakeholderRecommendation
    reasoning: str  # Section 16: "The system should explain why."


class PrdCriticFeedback(BaseModel):
    """Section 17's Critic Agent — every question it must ask, answered."""

    is_actually_a_problem: str
    is_ai_required: str
    is_solution_over_engineered: str
    supporting_evidence: str
    falsification_criteria: str
    simplest_alternative: str
    verdict: str  # "proceed" | "revise" | "reject"


class Prd(BaseModel):
    """Section 17's pipeline output, before critique."""

    problem_statement: str
    customer_context: str
    hypothesis: str
    solution: str
    metrics: list[str] = Field(default_factory=list)
    experiment: str


class SprintItem(BaseModel):
    title: str
    source: str  # "stakeholder_request" | "backlog" | "bug" | "commitment"
    priority: float  # 0.0-1.0
    owner: str = ""
    dependencies: list[str] = Field(default_factory=list)
    risk: str = ""


class SprintPlan(BaseModel):
    """Section 18's exact output shape."""

    prioritized_work: list[SprintItem] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    suggested_sprint_scope: list[str] = Field(default_factory=list)
