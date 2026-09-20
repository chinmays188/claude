from datetime import datetime, timezone

import pytest

from app.domains.career.resume_optimization import (
    check_outcome_grounded,
    check_resume_suggestions_grounded,
    optimize_resume,
)
from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.retrieval.document import Chunk
from app.retrieval.vector_search import VectorStore
from tests.fakes.example_resume import EXAMPLE_ACHIEVEMENTS
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


def _retriever_with_achievements() -> SecureRetriever:
    store = VectorStore(FakeEmbeddingModel())
    metadata = {}
    for achv_id, text in EXAMPLE_ACHIEVEMENTS:
        store.add([Chunk(id=f"{achv_id}::c0", document_id=achv_id, text=text, source="resume", created_at=NOW, updated_at=NOW, chunk_index=0)])
        metadata[achv_id] = PersonalDocumentMetadata(
            document_id=achv_id, source="resume", title="Achievements", created_at=NOW, updated_at=NOW,
            owner_id="alice", tenant_id="t1", sensitivity=Sensitivity.PERSONAL,
        )
    return SecureRetriever(store, metadata)


def test_optimize_resume_returns_grounded_suggestions():
    llm = ScriptedProvider(
        ['{"missing_keywords": ["stakeholder management"], "suggested_bullet_changes": ["Emphasize the refund flow launch"], '
         '"grounding_achievement_ids": ["achv1::c0"]}']
    )
    retriever = _retriever_with_achievements()

    outcome = optimize_resume(llm, "Looking for a PM with refund experience.", retriever, requester_id="alice", requester_tenant_id="t1")

    assert "stakeholder management" in outcome.result.missing_keywords
    assert check_outcome_grounded(outcome)


def test_check_grounded_fails_for_fabricated_id():
    llm = ScriptedProvider(
        ['{"missing_keywords": [], "suggested_bullet_changes": ["Made up bullet"], "grounding_achievement_ids": ["nonexistent_id"]}']
    )
    retriever = _retriever_with_achievements()

    outcome = optimize_resume(llm, "some JD", retriever, requester_id="alice", requester_tenant_id="t1")

    assert not check_outcome_grounded(outcome)


def test_check_grounded_passes_for_bracket_wrapped_valid_id():
    """Regression test: found via a real live trace (scripts/trace_resume.py)
    against a real resume, where Gemini echoed a valid excerpt id back
    wrapped in brackets (e.g. "[achv1::c0]" instead of "achv1::c0") -- a
    formatting quirk, not a fabricated achievement. The grounding check must
    still pass for this, since the underlying achievement is real."""
    llm = ScriptedProvider(
        ['{"missing_keywords": [], "suggested_bullet_changes": ["Emphasize the refund flow launch"], '
         '"grounding_achievement_ids": ["[achv1::c0]"]}']
    )
    retriever = _retriever_with_achievements()

    outcome = optimize_resume(llm, "some JD", retriever, requester_id="alice", requester_tenant_id="t1")

    assert check_outcome_grounded(outcome)


def test_check_grounded_passes_when_no_suggestions_made():
    llm = ScriptedProvider(['{"missing_keywords": [], "suggested_bullet_changes": [], "grounding_achievement_ids": []}'])
    retriever = _retriever_with_achievements()

    outcome = optimize_resume(llm, "some JD", retriever, requester_id="alice", requester_tenant_id="t1")

    assert check_outcome_grounded(outcome)


def test_optimize_resume_rejects_empty_jd():
    llm = ScriptedProvider([])
    retriever = _retriever_with_achievements()

    with pytest.raises(ValueError):
        optimize_resume(llm, "", retriever, requester_id="alice", requester_tenant_id="t1")


def test_optimize_resume_never_sees_other_users_documents():
    llm = ScriptedProvider(['{"missing_keywords": [], "suggested_bullet_changes": [], "grounding_achievement_ids": []}'])
    retriever = _retriever_with_achievements()

    outcome = optimize_resume(llm, "some JD", retriever, requester_id="bob", requester_tenant_id="t1")

    assert outcome.valid_excerpt_ids == []  # bob owns none of alice's achievements
