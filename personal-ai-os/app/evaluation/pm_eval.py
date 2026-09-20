from pydantic import BaseModel

from app.domains.pm.models import FeedbackIntelligenceResult, PrdCriticFeedback


class PmCheckResult(BaseModel):
    name: str
    passed: bool
    reason: str


def check_feedback_themes_grounded(result: FeedbackIntelligenceResult, raw_feedback_items: list[str]) -> PmCheckResult:
    """Section 38: never fabricate customer data. A cheap, auditable proxy —
    every theme's customer_impact text should be substantively derived from
    the raw feedback, not entirely disconnected from it. Checks that at least
    one raw feedback item shares meaningful word overlap with each theme,
    rather than trusting the model's self-report."""
    if not result.top_themes:
        return PmCheckResult(name="feedback_themes_grounded", passed=True, reason="No themes to check.")

    raw_text = " ".join(raw_feedback_items).lower()
    ungrounded = []
    for theme in result.top_themes:
        theme_words = {w for w in theme.theme.lower().split() if len(w) > 3}
        if theme_words and not any(word in raw_text for word in theme_words):
            ungrounded.append(theme.theme)

    if ungrounded:
        return PmCheckResult(
            name="feedback_themes_grounded", passed=False,
            reason=f"Theme(s) with no apparent basis in raw feedback: {ungrounded}",
        )
    return PmCheckResult(name="feedback_themes_grounded", passed=True, reason="Themes trace back to raw feedback.")


def check_critic_challenged_the_prd(critique: PrdCriticFeedback) -> PmCheckResult:
    """Section 17: the Critic must actually challenge, not rubber-stamp.
    Flags an obviously non-committal critique (all fields trivially short)."""
    fields = [
        critique.is_actually_a_problem, critique.is_ai_required, critique.is_solution_over_engineered,
        critique.supporting_evidence, critique.falsification_criteria, critique.simplest_alternative,
    ]
    trivial = [f for f in fields if len(f.strip()) < 10]
    if trivial:
        return PmCheckResult(
            name="critic_challenged_the_prd", passed=False,
            reason=f"{len(trivial)} critic field(s) look non-committal/too short to be a real challenge.",
        )
    return PmCheckResult(name="critic_challenged_the_prd", passed=True, reason="Critic gave substantive answers to all questions.")
