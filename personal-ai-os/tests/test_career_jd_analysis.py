from datetime import datetime, timezone

import pytest

from app.domains.career.jd_analysis import analyze_jd, parse_jd
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


def _retriever_with_achievements(owner="alice", tenant="t1") -> SecureRetriever:
    store = VectorStore(FakeEmbeddingModel())
    metadata = {}
    for achv_id, text in EXAMPLE_ACHIEVEMENTS:
        store.add([Chunk(id=f"{achv_id}::c0", document_id=achv_id, text=text, source="resume", created_at=NOW, updated_at=NOW, chunk_index=0)])
        metadata[achv_id] = PersonalDocumentMetadata(
            document_id=achv_id, source="resume", title="Achievements", created_at=NOW, updated_at=NOW,
            owner_id=owner, tenant_id=tenant, sensitivity=Sensitivity.PERSONAL,
        )
    return SecureRetriever(store, metadata)


def test_parse_jd_extracts_requirements():
    llm = ScriptedProvider(
        ['{"role_title": "AI PM", "required_skills": ["RAG", "LLMs"], "preferred_skills": ["voice"], '
         '"responsibilities": ["own AI roadmap"], "seniority_signal": "senior"}']
    )

    requirements = parse_jd(llm, "We are hiring a Senior AI PM with RAG and LLM experience.")

    assert requirements.role_title == "AI PM"
    assert "RAG" in requirements.required_skills


def test_parse_jd_rejects_empty_text():
    llm = ScriptedProvider([])

    with pytest.raises(ValueError):
        parse_jd(llm, "")


def test_analyze_jd_returns_fit_scores():
    llm = ScriptedProvider(
        [
            '{"role_title": "AI PM", "required_skills": ["AI", "leadership"], "preferred_skills": [], "responsibilities": [], "seniority_signal": "senior"}',
            '{"overall_fit": 0.8, "technical_fit": 0.7, "ai_fit": 0.9, "pm_fit": 0.85, "domain_fit": 0.6, '
            '"leadership_fit": 0.75, "major_gaps": ["no MLOps experience"], '
            '"recommended_resume_changes": ["highlight AI triage system"], "interview_risks": ["depth of AI knowledge"]}',
        ]
    )
    retriever = _retriever_with_achievements()

    result = analyze_jd(llm, "Senior AI PM role requiring AI and leadership.", retriever, requester_id="alice", requester_tenant_id="t1")

    assert result.overall_fit == 0.8
    assert "no MLOps experience" in result.major_gaps


def test_analyze_jd_handles_no_retrieved_documents_gracefully():
    llm = ScriptedProvider(
        [
            '{"role_title": "AI PM", "required_skills": [], "preferred_skills": [], "responsibilities": [], "seniority_signal": ""}',
            '{"overall_fit": 0.1, "technical_fit": 0.1, "ai_fit": 0.1, "pm_fit": 0.1, "domain_fit": 0.1, '
            '"leadership_fit": 0.1, "major_gaps": ["no resume on file"], "recommended_resume_changes": [], "interview_risks": []}',
        ]
    )
    empty_retriever = SecureRetriever(VectorStore(FakeEmbeddingModel()), {})

    result = analyze_jd(llm, "Some role.", empty_retriever, requester_id="alice", requester_tenant_id="t1")

    assert result.overall_fit == 0.1
