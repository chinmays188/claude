from datetime import datetime, timezone

import pytest

from app.domains.career.interview_prep import NoRelevantExperienceError, build_interview_story
from app.evaluation.career_eval import check_star_completeness
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


def test_builds_star_story_grounded_in_real_achievement():
    llm = ScriptedProvider(
        ['{"situation": "Engineering and support disagreed on incident ownership.", '
         '"task": "Resolve the ownership conflict.", "action": "Proposed a shared on-call rotation.", '
         '"result": "Both teams adopted it within a month.", "source_achievement_id": "achv2::c0"}']
    )
    retriever = _retriever_with_achievements()

    story = build_interview_story(llm, "Give me a conflict-management story.", retriever, requester_id="alice", requester_tenant_id="t1")

    assert story.source_achievement_id == "achv2::c0"
    assert check_star_completeness(story).passed


def test_raises_when_source_id_is_fabricated():
    llm = ScriptedProvider(
        ['{"situation": "s", "task": "t", "action": "a", "result": "r", "source_achievement_id": "made_up_id"}']
    )
    retriever = _retriever_with_achievements()

    with pytest.raises(NoRelevantExperienceError):
        build_interview_story(llm, "Give me a story.", retriever, requester_id="alice", requester_tenant_id="t1")


def test_raises_when_no_experience_retrieved_at_all():
    llm = ScriptedProvider([])
    empty_retriever = SecureRetriever(VectorStore(FakeEmbeddingModel()), {})

    with pytest.raises(NoRelevantExperienceError):
        build_interview_story(llm, "Give me a story.", empty_retriever, requester_id="alice", requester_tenant_id="t1")


def test_rejects_empty_request():
    llm = ScriptedProvider([])
    retriever = _retriever_with_achievements()

    with pytest.raises(ValueError):
        build_interview_story(llm, "", retriever, requester_id="alice", requester_tenant_id="t1")


def test_star_completeness_fails_on_empty_field():
    from app.domains.career.models import InterviewStory

    story = InterviewStory(situation="s", task="", action="a", result="r", source_achievement_id="x")

    result = check_star_completeness(story)

    assert not result.passed
    assert "task" in result.reason
