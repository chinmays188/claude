import pytest

from app.domains.pm.feedback_intelligence import analyze_feedback
from app.evaluation.pm_eval import check_feedback_themes_grounded
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_analyze_feedback_returns_themes():
    llm = ScriptedProvider(
        ['{"top_themes": [{"theme": "refund delays", "frequency": 5, "severity": 0.7, "customer_impact": "customers wait too long", "trend": "emerging"}], '
         '"emerging_themes": ["refund delays"], "declining_themes": [], "critical_issues": ["refund SLA breach"], '
         '"recommended_actions": ["speed up refund processing"]}']
    )

    result = analyze_feedback(llm, ["My refund is taking forever.", "Refunds are too slow."])

    assert result.top_themes[0].theme == "refund delays"
    assert "refund delays" in result.emerging_themes


def test_analyze_feedback_rejects_empty_list():
    llm = ScriptedProvider([])

    with pytest.raises(ValueError):
        analyze_feedback(llm, [])


def test_check_feedback_themes_grounded_passes_for_real_theme():
    llm = ScriptedProvider(
        ['{"top_themes": [{"theme": "refund delays", "frequency": 2, "severity": 0.5, "customer_impact": "x", "trend": "stable"}], '
         '"emerging_themes": [], "declining_themes": [], "critical_issues": [], "recommended_actions": []}']
    )
    raw_feedback = ["My refund is taking forever.", "Refunds are too slow."]

    result = analyze_feedback(llm, raw_feedback)
    check = check_feedback_themes_grounded(result, raw_feedback)

    assert check.passed


def test_check_feedback_themes_grounded_fails_for_fabricated_theme():
    llm = ScriptedProvider(
        ['{"top_themes": [{"theme": "pricing complaints", "frequency": 10, "severity": 0.9, "customer_impact": "x", "trend": "emerging"}], '
         '"emerging_themes": [], "declining_themes": [], "critical_issues": [], "recommended_actions": []}']
    )
    raw_feedback = ["My refund is taking forever.", "Refunds are too slow."]

    result = analyze_feedback(llm, raw_feedback)
    check = check_feedback_themes_grounded(result, raw_feedback)

    assert not check.passed
