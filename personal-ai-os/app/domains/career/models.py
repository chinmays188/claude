from pydantic import BaseModel


class JdRequirements(BaseModel):
    """Section 9: 'JD Parser -> Requirements extraction -> Skill mapping.'"""

    role_title: str
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    responsibilities: list[str] = []
    seniority_signal: str = ""  # e.g. "senior", "lead", "individual contributor"


class JdAnalysisResult(BaseModel):
    """Section 9's exact output field list."""

    overall_fit: float  # 0.0-1.0
    technical_fit: float
    ai_fit: float
    pm_fit: float
    domain_fit: float
    leadership_fit: float
    major_gaps: list[str] = []
    recommended_resume_changes: list[str] = []
    interview_risks: list[str] = []


class ResumeOptimizationResult(BaseModel):
    """Section 10. Suggestions only — never rewrites the resume unilaterally,
    and every suggestion must trace back to something already in the
    candidate's real achievements (Section 10 rule 6: 'Never invent
    achievements')."""

    missing_keywords: list[str] = []
    suggested_bullet_changes: list[str] = []
    grounding_achievement_ids: list[str] = []  # which retrieved achievements each suggestion is based on


class InterviewStory(BaseModel):
    """Section 11's STAR structure."""

    situation: str
    task: str
    action: str
    result: str
    source_achievement_id: str  # traces back to a real retrieved experience, never fabricated
