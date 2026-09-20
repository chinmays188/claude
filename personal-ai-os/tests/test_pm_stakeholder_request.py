from datetime import datetime, timezone

import pytest

from app.domains.pm.models import StakeholderRecommendation
from app.domains.pm.stakeholder_request import analyze_stakeholder_request
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


def test_analyze_returns_recommendation_and_reasoning():
    llm = ScriptedProvider(
        ['{"request": "Can we add automated refunds?", "problem_extracted": "Manual refunds are slow", '
         '"user_impact": "All customers requesting refunds", "recommendation": "BUILD", '
         '"reasoning": "Already planned in the Q3 roadmap, confirming demand."}']
    )
    retriever = _retriever_with_roadmap()

    result = analyze_stakeholder_request(llm, "Can we add automated refunds?", retriever, requester_id="alice", requester_tenant_id="t1")

    assert result.recommendation == StakeholderRecommendation.BUILD
    assert result.reasoning


def test_analyze_rejects_empty_request():
    llm = ScriptedProvider([])
    retriever = _retriever_with_roadmap()

    with pytest.raises(ValueError):
        analyze_stakeholder_request(llm, "", retriever, requester_id="alice", requester_tenant_id="t1")


def test_analyze_handles_no_evidence_found():
    llm = ScriptedProvider(
        ['{"request": "Add feature X", "problem_extracted": "unclear without more context", '
         '"user_impact": "unknown", "recommendation": "NEED_MORE_EVIDENCE", "reasoning": "No roadmap or feedback data available to assess this."}']
    )
    empty_retriever = SecureRetriever(VectorStore(FakeEmbeddingModel()), {})

    result = analyze_stakeholder_request(llm, "Add feature X", empty_retriever, requester_id="alice", requester_tenant_id="t1")

    assert result.recommendation == StakeholderRecommendation.NEED_MORE_EVIDENCE
