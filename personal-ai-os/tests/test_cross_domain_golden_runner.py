from app.evaluation.cross_domain_golden_runner import run_cross_domain_golden_case, run_cross_domain_golden_suite
from app.evaluation.domain_golden import DomainGoldenCase
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_cross_domain_case_passes_with_correct_domains():
    llm = ScriptedProvider(['{"domains": ["CAREER", "LEARNING"], "confidence": 0.9}'])
    case = DomainGoldenCase(id="cross_001", input="Should I learn Kubernetes for my career?", expected_domains=["CAREER", "LEARNING"])

    result = run_cross_domain_golden_case(llm, case)

    assert result.passed is True


def test_cross_domain_case_fails_on_missing_domain():
    llm = ScriptedProvider(['{"domains": ["CAREER"], "confidence": 0.9}'])
    case = DomainGoldenCase(id="cross_001", input="Should I learn Kubernetes for my career?", expected_domains=["CAREER", "LEARNING"])

    result = run_cross_domain_golden_case(llm, case)

    assert result.passed is False


def test_run_cross_domain_golden_suite_runs_every_case():
    llm = ScriptedProvider(['{"domains": ["CAREER", "LEARNING"], "confidence": 0.9}'])
    cases = [DomainGoldenCase(id="cross_001", input="Should I learn Kubernetes for my career?", expected_domains=["CAREER", "LEARNING"])]

    results = run_cross_domain_golden_suite(llm, cases)

    assert len(results) == 1
