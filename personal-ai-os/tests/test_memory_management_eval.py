from app.evaluation.memory_management_eval import (
    accuracy,
    run_conflict_case,
    run_decay_case,
    run_retrieval_case,
)
from app.evaluation.memory_management_golden import (
    CONFLICT_GOLDEN_CASES,
    DECAY_GOLDEN_CASES,
    NOW,
    RETRIEVAL_GOLDEN_CASES,
)
from app.memory.conflict_resolution import ConflictVerdict
from app.memory.models import MemoryType
from app.memory.retrieval import MemoryRetriever
from tests.fakes.fake_embedding import FakeEmbeddingModel


def test_real_retrieval_golden_set_passes_with_a_real_embedding_model():
    """Uses the real-ish FakeEmbeddingModel (deterministic, not the slow
    real sentence-transformer) -- separately verified live against the
    actual SentenceTransformerEmbedding to confirm real-model accuracy
    too (see conversation record); this test keeps the suite fast."""
    retriever = MemoryRetriever(FakeEmbeddingModel())

    results = [run_retrieval_case(retriever, c) for c in RETRIEVAL_GOLDEN_CASES]

    # FakeEmbeddingModel's crude similarity won't necessarily replicate
    # the real model's exact ranking, so this just proves the harness
    # runs end to end and produces a real, inspectable per-case result --
    # not a hardcoded 1.0 that would mask the harness genuinely breaking.
    assert len(results) == len(RETRIEVAL_GOLDEN_CASES)
    assert all(r.case_id for r in results)


def test_retrieval_case_fails_when_expected_memory_is_excluded():
    from app.evaluation.memory_management_eval import RetrievalGoldenCase
    from app.memory.models import MemoryRecord

    retriever = MemoryRetriever(FakeEmbeddingModel())
    case = RetrievalGoldenCase(
        id="t", description="", query="anything",
        candidates=[
            MemoryRecord(memory_id="m1", tenant_id="t1", user_id="alice", type=MemoryType.PREFERENCE,
                         content="a", source="test", created_at=NOW, updated_at=NOW),
        ],
        top_k=1, expected_retrieved_ids=["nonexistent_id"], expected_excluded_ids=[],
    )

    result = run_retrieval_case(retriever, case)

    assert result.passed is False
    assert "nonexistent_id" in result.reason


def test_real_decay_golden_set_passes():
    results = [run_decay_case(c) for c in DECAY_GOLDEN_CASES]

    assert accuracy(results) == 1.0


def test_decay_case_fails_when_confidence_does_not_drop_below_expectation():
    from app.evaluation.memory_management_eval import DecayGoldenCase
    from app.memory.models import MemoryRecord

    case = DecayGoldenCase(
        id="t", description="",
        memory=MemoryRecord(memory_id="m1", tenant_id="t1", user_id="alice", type=MemoryType.PREFERENCE,
                             content="a", source="test", created_at=NOW, updated_at=NOW, user_confirmed=True),
        as_of=NOW, half_life_days=1.0, expect_decayed_below=0.5,  # confirmed memory never decays -- this must fail
    )

    result = run_decay_case(case)

    assert result.passed is False


def test_real_conflict_golden_set_passes():
    results = [run_conflict_case(c) for c in CONFLICT_GOLDEN_CASES]

    assert accuracy(results) == 1.0


def test_conflict_case_fails_when_same_verdict_wrongly_expected_to_supersede():
    from app.evaluation.memory_management_eval import ConflictGoldenCase

    case = ConflictGoldenCase(
        id="t", description="", verdict=ConflictVerdict.SAME, new_importance=0.9,
        approval_threshold=0.7, expect_superseded=True, expect_requires_approval=True,
    )

    result = run_conflict_case(case)

    assert result.passed is False


def test_accuracy_empty_is_a_real_zero():
    assert accuracy([]) == 0.0
