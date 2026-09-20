from pydantic import BaseModel

from app.domains.career.models import InterviewStory, JdAnalysisResult


class CareerCheckResult(BaseModel):
    name: str
    passed: bool
    reason: str


def check_star_completeness(story: InterviewStory) -> CareerCheckResult:
    """Section 11: 'STAR completeness' — all four fields must be substantively
    filled, not blank or placeholder text."""
    empty_fields = [
        field for field in ("situation", "task", "action", "result")
        if not getattr(story, field) or not getattr(story, field).strip()
    ]
    if empty_fields:
        return CareerCheckResult(
            name="star_completeness", passed=False,
            reason=f"Missing or empty STAR field(s): {empty_fields}",
        )
    return CareerCheckResult(name="star_completeness", passed=True, reason="All STAR fields present.")


def check_jd_analysis_scores_in_range(result: JdAnalysisResult) -> CareerCheckResult:
    """All fit scores must be valid 0.0-1.0 probabilities — a score outside
    this range would indicate a broken/ungrounded analysis, not a real signal."""
    scores = {
        "overall_fit": result.overall_fit, "technical_fit": result.technical_fit,
        "ai_fit": result.ai_fit, "pm_fit": result.pm_fit,
        "domain_fit": result.domain_fit, "leadership_fit": result.leadership_fit,
    }
    out_of_range = {name: value for name, value in scores.items() if not (0.0 <= value <= 1.0)}
    if out_of_range:
        return CareerCheckResult(
            name="jd_analysis_scores_in_range", passed=False,
            reason=f"Score(s) out of [0.0, 1.0] range: {out_of_range}",
        )
    return CareerCheckResult(name="jd_analysis_scores_in_range", passed=True, reason="All scores in range.")
