from app.evaluation.domain_golden import DomainGoldenCase
from app.evaluation.learning_golden_runner import run_learning_golden_case, run_learning_golden_suite
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_explain_concept_case_passes_with_valid_content_kind():
    llm = ScriptedProvider(['{"concept": "Docker", "content": "Docker packages an app with its dependencies.", "kind": "factual"}'])
    case = DomainGoldenCase(id="learning_001", category="explain_concept", input="Docker")

    result = run_learning_golden_case(llm, case)

    assert result.passed is True
    assert result.category == "explain_concept"


def test_adaptive_evaluation_case_passes_with_in_range_scores():
    llm = ScriptedProvider(
        ['{"conceptual_understanding": 3, "technical_depth": 2, "application": 2, '
         '"system_thinking": 1, "pm_translation": 2, "feedback": "Too vague, lacks technical detail."}'],
    )
    case = DomainGoldenCase(id="learning_002", category="adaptive_evaluation", input="What does a Dockerfile do?")

    result = run_learning_golden_case(llm, case)

    assert result.passed is True
    assert result.category == "adaptive_evaluation"


def test_unknown_category_fails_honestly():
    case = DomainGoldenCase(id="learning_999", category="not_real", input="anything")

    result = run_learning_golden_case(ScriptedProvider([]), case)

    assert result.passed is False
    assert "Unknown category" in result.reason


def test_run_learning_golden_suite_runs_every_case():
    llm = ScriptedProvider(['{"concept": "Docker", "content": "Docker packages an app with its dependencies.", "kind": "factual"}'])
    cases = [DomainGoldenCase(id="learning_001", category="explain_concept", input="Docker")]

    results = run_learning_golden_suite(llm, cases)

    assert len(results) == 1
