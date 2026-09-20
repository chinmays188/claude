from pydantic import BaseModel

from app.domains.learning.models import AnswerEvaluation, Explanation


class LearningCheckResult(BaseModel):
    name: str
    passed: bool
    reason: str


def check_evaluation_scores_in_range(evaluation: AnswerEvaluation) -> LearningCheckResult:
    """Section 30's 5 dimensions must each be a valid 0-10 score."""
    scores = {
        "conceptual_understanding": evaluation.conceptual_understanding,
        "technical_depth": evaluation.technical_depth,
        "application": evaluation.application,
        "system_thinking": evaluation.system_thinking,
        "pm_translation": evaluation.pm_translation,
    }
    out_of_range = {name: value for name, value in scores.items() if not (0 <= value <= 10)}
    if out_of_range:
        return LearningCheckResult(
            name="evaluation_scores_in_range", passed=False,
            reason=f"Score(s) out of [0, 10] range: {out_of_range}",
        )
    return LearningCheckResult(name="evaluation_scores_in_range", passed=True, reason="All scores in range.")


def check_content_kind_labeled(explanation: Explanation) -> LearningCheckResult:
    """Section 38: content must be tagged factual/analogy/speculation — this
    check simply verifies the tag is actually set to one of the valid kinds
    (Pydantic's enum validation already guarantees this at construction time,
    but this check exists so a caller can assert the property explicitly in
    an eval report rather than relying on it being implicit)."""
    from app.domains.learning.models import ContentKind

    if explanation.kind not in ContentKind:
        return LearningCheckResult(
            name="content_kind_labeled", passed=False, reason=f"Invalid kind: {explanation.kind}"
        )
    return LearningCheckResult(
        name="content_kind_labeled", passed=True, reason=f"Content correctly labeled as '{explanation.kind.value}'."
    )
