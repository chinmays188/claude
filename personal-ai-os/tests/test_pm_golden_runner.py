from datetime import datetime, timezone

from app.evaluation.domain_golden import DomainGoldenCase
from app.evaluation.pm_golden_runner import run_pm_golden_case, run_pm_golden_suite
from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.retrieval.document import Chunk
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


def _retriever_with_roadmap() -> SecureRetriever:
    store = VectorStore(FakeEmbeddingModel())
    store.add([Chunk(id="roadmap1::c0", document_id="roadmap1", text="Q3 roadmap: refund automation is already planned.", source="roadmap", created_at=NOW, updated_at=NOW, chunk_index=0)])
    metadata = {"roadmap1": PersonalDocumentMetadata(document_id="roadmap1", source="roadmap", title="Roadmap", created_at=NOW, updated_at=NOW, owner_id="alice", tenant_id="t1", sensitivity=Sensitivity.PERSONAL)}
    return SecureRetriever(store, metadata)


def test_feedback_intelligence_case_passes_with_grounded_themes():
    llm = ScriptedProvider(
        ['{"top_themes": [{"theme": "refunds", "frequency": 3, "severity": 0.7, '
         '"customer_impact": "Refunds are slow for customers.", "trend": "stable"}], '
         '"emerging_themes": [], "declining_themes": [], "critical_issues": [], "recommended_actions": []}'],
    )
    case = DomainGoldenCase(
        id="pm_001", category="feedback_intelligence",
        input=["My refund is taking forever.", "Refunds are too slow."],
    )

    result = run_pm_golden_case(llm, _retriever_with_roadmap(), "alice", "t1", case)

    assert result.passed is True
    assert result.category == "feedback_intelligence"


def test_feedback_intelligence_case_fails_on_ungrounded_theme():
    llm = ScriptedProvider(
        ['{"top_themes": [{"theme": "unicorns", "frequency": 3, "severity": 0.7, '
         '"customer_impact": "Customers want unicorns.", "trend": "stable"}], '
         '"emerging_themes": [], "declining_themes": [], "critical_issues": [], "recommended_actions": []}'],
    )
    case = DomainGoldenCase(id="pm_001", category="feedback_intelligence", input=["My refund is taking forever."])

    result = run_pm_golden_case(llm, _retriever_with_roadmap(), "alice", "t1", case)

    assert result.passed is False


def test_stakeholder_request_case_passes_with_reasoned_recommendation():
    llm = ScriptedProvider(
        ['{"request": "Can we add automated refunds?", "problem_extracted": "Manual refunds are slow", '
         '"user_impact": "All customers", "recommendation": "BUILD", '
         '"reasoning": "Already planned in the Q3 roadmap, confirming demand."}'],
    )
    case = DomainGoldenCase(id="pm_002", category="stakeholder_request", input="Can we add automated refunds?")

    result = run_pm_golden_case(llm, _retriever_with_roadmap(), "alice", "t1", case)

    assert result.passed is True
    assert result.category == "stakeholder_request"


def test_prd_generation_case_passes_with_real_critic_challenge():
    llm = ScriptedProvider(
        [
            '{"problem_statement": "Manual refund approval is slow", "customer_context": "Support agents", '
            '"hypothesis": "Automation reduces turnaround", "solution": "Auto-approve under $50", '
            '"metrics": ["turnaround time"], "experiment": "Pilot with 10% of refunds"}',
            '{"is_actually_a_problem": "Yes, refund delays are a real, measured pain point for support.", '
            '"is_ai_required": "A deterministic rule (amount < $50) would work just as well, no AI needed.", '
            '"is_solution_over_engineered": "Using an AI agent for a simple threshold check is over-engineered.", '
            '"supporting_evidence": "No data shown on refund volume under $50 specifically.", '
            '"falsification_criteria": "If fraud rate increases after auto-approval, the hypothesis is wrong.", '
            '"simplest_alternative": "A simple rule-based auto-approval, no LLM involved.", "verdict": "revise"}',
        ],
    )
    case = DomainGoldenCase(id="pm_003", category="prd_generation", input="Build an AI agent to automatically approve refunds under $50.")

    result = run_pm_golden_case(llm, _retriever_with_roadmap(), "alice", "t1", case)

    assert result.passed is True
    assert result.category == "prd_generation"


def test_unknown_category_fails_honestly():
    case = DomainGoldenCase(id="pm_999", category="not_real", input="anything")

    result = run_pm_golden_case(ScriptedProvider([]), _retriever_with_roadmap(), "alice", "t1", case)

    assert result.passed is False
    assert "Unknown category" in result.reason


def test_run_pm_golden_suite_runs_every_case():
    llm = ScriptedProvider(
        ['{"request": "Can we add automated refunds?", "problem_extracted": "Manual refunds are slow", '
         '"user_impact": "All customers", "recommendation": "BUILD", '
         '"reasoning": "Already planned in the Q3 roadmap, confirming demand."}'],
    )
    cases = [DomainGoldenCase(id="pm_002", category="stakeholder_request", input="Can we add automated refunds?")]

    results = run_pm_golden_suite(llm, _retriever_with_roadmap(), "alice", "t1", cases)

    assert len(results) == 1
