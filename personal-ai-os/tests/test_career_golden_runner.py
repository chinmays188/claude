from datetime import datetime, timezone

from app.evaluation.career_golden_runner import run_career_golden_case, run_career_golden_suite
from app.evaluation.domain_golden import DomainGoldenCase
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


def test_jd_analysis_case_passes_with_valid_scores():
    llm = ScriptedProvider(
        [
            '{"role_title": "AI PM", "required_skills": ["RAG"], "preferred_skills": [], '
            '"responsibilities": [], "seniority_signal": "senior"}',
            '{"overall_fit": 0.8, "technical_fit": 0.7, "ai_fit": 0.9, "pm_fit": 0.8, '
            '"domain_fit": 0.6, "leadership_fit": 0.7, "major_gaps": [], '
            '"recommended_resume_changes": [], "interview_risks": []}',
        ]
    )
    retriever = _retriever_with_achievements()
    case = DomainGoldenCase(id="career_001", category="jd_analysis", input="Senior AI PM role")

    result = run_career_golden_case(llm, retriever, "alice", "t1", case)

    assert result.passed is True
    assert result.category == "jd_analysis"


def test_jd_analysis_case_fails_on_out_of_range_score():
    llm = ScriptedProvider(
        [
            '{"role_title": "AI PM", "required_skills": [], "preferred_skills": [], '
            '"responsibilities": [], "seniority_signal": "senior"}',
            '{"overall_fit": 1.5, "technical_fit": 0.7, "ai_fit": 0.9, "pm_fit": 0.8, '
            '"domain_fit": 0.6, "leadership_fit": 0.7, "major_gaps": [], '
            '"recommended_resume_changes": [], "interview_risks": []}',
        ]
    )
    retriever = _retriever_with_achievements()
    case = DomainGoldenCase(id="career_001", category="jd_analysis", input="Senior AI PM role")

    result = run_career_golden_case(llm, retriever, "alice", "t1", case)

    assert result.passed is False


def test_interview_prep_case_passes_with_complete_star_story():
    llm = ScriptedProvider(
        [
            '{"situation": "Teams disagreed on incident ownership.", "task": "Resolve the conflict.", '
            '"action": "Proposed a shared on-call rotation.", "result": "Both teams adopted it within a month.", '
            '"source_achievement_id": "achv2::c0"}',
        ]
    )
    retriever = _retriever_with_achievements()
    case = DomainGoldenCase(id="career_002", category="interview_prep", input="Give me a conflict-management story.")

    result = run_career_golden_case(llm, retriever, "alice", "t1", case)

    assert result.passed is True
    assert result.category == "interview_prep"


def test_interview_prep_case_handles_no_relevant_experience_honestly():
    retriever = SecureRetriever(VectorStore(FakeEmbeddingModel()), {})  # empty -- nothing to retrieve
    case = DomainGoldenCase(id="career_002", category="interview_prep", input="Tell me about a time you flew a plane.")

    result = run_career_golden_case(ScriptedProvider([]), retriever, "alice", "t1", case)

    assert result.passed is False
    assert "No relevant experience" in result.reason


def test_resume_optimization_case_passes_with_grounded_suggestions():
    llm = ScriptedProvider(
        [
            '{"missing_keywords": ["automation"], '
            '"suggested_bullet_changes": ["Emphasize refund automation experience"], '
            '"grounding_achievement_ids": ["achv1::c0"]}',
        ]
    )
    retriever = _retriever_with_achievements()
    case = DomainGoldenCase(id="career_003", category="resume_optimization", input="Optimize my resume for a refund-automation PM role.")

    result = run_career_golden_case(llm, retriever, "alice", "t1", case)

    assert result.passed is True
    assert result.category == "resume_optimization"


def test_resume_optimization_case_fails_on_ungrounded_suggestion():
    llm = ScriptedProvider(
        [
            '{"missing_keywords": [], "suggested_bullet_changes": ["Fabricated claim"], '
            '"grounding_achievement_ids": ["fake_id::c0"]}',
        ]
    )
    retriever = _retriever_with_achievements()
    case = DomainGoldenCase(id="career_003", category="resume_optimization", input="Optimize my resume.")

    result = run_career_golden_case(llm, retriever, "alice", "t1", case)

    assert result.passed is False


def test_unknown_category_fails_honestly_not_silently():
    case = DomainGoldenCase(id="career_999", category="not_a_real_category", input="anything")

    result = run_career_golden_case(ScriptedProvider([]), _retriever_with_achievements(), "alice", "t1", case)

    assert result.passed is False
    assert "Unknown category" in result.reason


def test_run_career_golden_suite_runs_every_case():
    llm = ScriptedProvider(
        [
            '{"role_title": "AI PM", "required_skills": [], "preferred_skills": [], '
            '"responsibilities": [], "seniority_signal": "senior"}',
            '{"overall_fit": 0.8, "technical_fit": 0.7, "ai_fit": 0.9, "pm_fit": 0.8, '
            '"domain_fit": 0.6, "leadership_fit": 0.7, "major_gaps": [], '
            '"recommended_resume_changes": [], "interview_risks": []}',
        ]
    )
    cases = [DomainGoldenCase(id="career_001", category="jd_analysis", input="Senior AI PM role")]

    results = run_career_golden_suite(llm, _retriever_with_achievements(), "alice", "t1", cases)

    assert len(results) == 1
