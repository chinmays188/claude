from datetime import datetime, timezone

from app.evaluation.personal_golden import (
    PersonalEvalCategory,
    PersonalGoldenCase,
    pass_rate_by_category,
    run_personal_golden_case,
    run_personal_golden_set,
)
from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.memory.retrieval import MemoryRetriever
from app.personal_rag.pipeline import PersonalRagPipeline
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


def _pipeline(llm_response: str, chunk_text: str = None, doc_id: str = "resume1"):
    llm = ScriptedProvider([llm_response])
    store = VectorStore(FakeEmbeddingModel())
    metadata = {}
    if chunk_text:
        store.add([Chunk(id=f"{doc_id}::c0", document_id=doc_id, text=chunk_text, source="upload", created_at=NOW, updated_at=NOW, chunk_index=0)])
        metadata[doc_id] = PersonalDocumentMetadata(
            document_id=doc_id, source="upload", title="t", created_at=NOW, updated_at=NOW,
            owner_id="alice", tenant_id="t1", sensitivity=Sensitivity.PERSONAL,
        )
    secure_retriever = SecureRetriever(store, metadata)
    memory_retriever = MemoryRetriever(FakeEmbeddingModel())
    return PersonalRagPipeline(llm, secure_retriever, memory_retriever)


def test_career_case_passes_with_expected_content():
    pipeline = _pipeline("You worked at Acme Corp as a PM for 3 years.", chunk_text="Worked at Acme Corp as PM.", doc_id="resume1")
    case = PersonalGoldenCase(
        id="career_001", category=PersonalEvalCategory.CAREER, question="Where did I work?",
        requester_id="alice", requester_tenant_id="t1",
        expected_answer_contains=["Acme Corp"], expected_citation_document_ids=["resume1"],
    )

    result = run_personal_golden_case(pipeline, case)

    assert result.passed


def test_case_fails_when_expected_content_missing():
    pipeline = _pipeline("Some unrelated answer.")
    case = PersonalGoldenCase(
        id="career_001", category=PersonalEvalCategory.CAREER, question="Where did I work?",
        requester_id="alice", requester_tenant_id="t1", expected_answer_contains=["Acme Corp"],
    )

    result = run_personal_golden_case(pipeline, case)

    assert not result.passed
    assert "Acme Corp" in result.reason


def test_case_fails_when_expected_citation_missing():
    pipeline = _pipeline("You worked at Acme Corp.")
    case = PersonalGoldenCase(
        id="career_001", category=PersonalEvalCategory.CAREER, question="Where did I work?",
        requester_id="alice", requester_tenant_id="t1",
        expected_answer_contains=["Acme Corp"], expected_citation_document_ids=["resume1"],
    )

    result = run_personal_golden_case(pipeline, case)

    assert not result.passed
    assert "citation" in result.reason.lower()


def test_pass_rate_by_category_reports_independently():
    results = [
        run_personal_golden_case(
            _pipeline("Acme Corp"),
            PersonalGoldenCase(id="c1", category=PersonalEvalCategory.CAREER, question="q", requester_id="a", requester_tenant_id="t1", expected_answer_contains=["Acme Corp"]),
        ),
        run_personal_golden_case(
            _pipeline("wrong answer"),
            PersonalGoldenCase(id="c2", category=PersonalEvalCategory.CAREER, question="q", requester_id="a", requester_tenant_id="t1", expected_answer_contains=["Acme Corp"]),
        ),
        run_personal_golden_case(
            _pipeline("Docker basics"),
            PersonalGoldenCase(id="l1", category=PersonalEvalCategory.LEARNING, question="q", requester_id="a", requester_tenant_id="t1", expected_answer_contains=["Docker"]),
        ),
    ]

    rates = pass_rate_by_category(results)

    assert rates["career"] == 0.5
    assert rates["learning"] == 1.0
