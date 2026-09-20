from datetime import datetime, timezone

import pytest

from app.domains.pm.prd import critique_prd, draft_and_critique_prd, draft_prd
from app.evaluation.pm_eval import check_critic_challenged_the_prd
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.retrieval.vector_search import VectorStore
from tests.fakes.fake_embedding import FakeEmbeddingModel

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _empty_retriever() -> SecureRetriever:
    return SecureRetriever(VectorStore(FakeEmbeddingModel()), {})


def test_draft_prd_returns_structured_sections():
    llm = ScriptedProvider(
        ['{"problem_statement": "Refunds take too long.", "customer_context": "All refund-seeking customers.", '
         '"hypothesis": "Automation reduces time to under an hour.", "solution": "Automated refund engine.", '
         '"metrics": ["avg refund time"], "experiment": "Pilot with 10% of refund requests."}']
    )

    prd = draft_prd(llm, "Automate refunds.", _empty_retriever(), requester_id="alice", requester_tenant_id="t1")

    assert prd.problem_statement == "Refunds take too long."
    assert "avg refund time" in prd.metrics


def test_draft_prd_rejects_empty_idea():
    llm = ScriptedProvider([])

    with pytest.raises(ValueError):
        draft_prd(llm, "", _empty_retriever(), requester_id="alice", requester_tenant_id="t1")


def test_critique_prd_answers_all_critic_questions():
    llm = ScriptedProvider(
        ['{"is_actually_a_problem": "Yes, refund delays are a top customer complaint per support data.", '
         '"is_ai_required": "No, rule-based automation would suffice for most cases.", '
         '"is_solution_over_engineered": "Yes, a full AI engine is overkill for simple refund rules.", '
         '"supporting_evidence": "No hard data cited yet, only anecdote.", '
         '"falsification_criteria": "If refund time does not drop after the pilot, hypothesis is false.", '
         '"simplest_alternative": "A rules engine for common refund cases.", "verdict": "revise"}']
    )
    prd = draft_prd(
        ScriptedProvider(['{"problem_statement": "p", "customer_context": "c", "hypothesis": "h", "solution": "s", "metrics": [], "experiment": "e"}']),
        "idea", _empty_retriever(), requester_id="alice", requester_tenant_id="t1",
    )

    critique = critique_prd(llm, prd)

    assert critique.verdict == "revise"
    assert check_critic_challenged_the_prd(critique).passed


def test_check_critic_fails_for_non_committal_answers():
    from app.domains.pm.models import PrdCriticFeedback

    trivial_critique = PrdCriticFeedback(
        is_actually_a_problem="yes", is_ai_required="ok", is_solution_over_engineered="fine",
        supporting_evidence="ok", falsification_criteria="ok", simplest_alternative="ok", verdict="proceed",
    )

    result = check_critic_challenged_the_prd(trivial_critique)

    assert not result.passed


def test_draft_and_critique_prd_returns_both():
    llm = ScriptedProvider(
        [
            '{"problem_statement": "p", "customer_context": "c", "hypothesis": "h", "solution": "s", "metrics": [], "experiment": "e"}',
            '{"is_actually_a_problem": "This is a real, evidenced problem.", "is_ai_required": "Not strictly required.", '
            '"is_solution_over_engineered": "Somewhat.", "supporting_evidence": "Limited evidence so far.", '
            '"falsification_criteria": "No improvement after pilot.", "simplest_alternative": "Manual triage improvements.", "verdict": "revise"}',
        ]
    )

    outcome = draft_and_critique_prd(llm, "idea", _empty_retriever(), requester_id="alice", requester_tenant_id="t1")

    assert outcome.prd.problem_statement == "p"
    assert outcome.critique.verdict == "revise"
