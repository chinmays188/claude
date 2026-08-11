from datetime import datetime, timezone

from app.evaluation.personal_rag_eval import (
    MemoryRetrievalCase,
    evaluate_memory_retrieval,
    personalization_score,
    temporal_correctness,
)
from app.memory.models import MemoryRecord, MemoryType
from app.memory.retrieval import RankedMemory

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _ranked(id_: str) -> RankedMemory:
    memory = MemoryRecord(
        memory_id=id_, tenant_id="t1", user_id="u1", type=MemoryType.GOAL,
        content="x", source="test", created_at=NOW, updated_at=NOW,
    )
    return RankedMemory(memory=memory, score=1.0)


def test_perfect_memory_recall_and_precision():
    case = MemoryRetrievalCase(query="q", relevant_memory_ids=["m1", "m2"])
    results = [_ranked("m1"), _ranked("m2")]

    metrics = evaluate_memory_retrieval(case, results)

    assert metrics.memory_recall == 1.0
    assert metrics.memory_precision == 1.0


def test_partial_memory_recall():
    case = MemoryRetrievalCase(query="q", relevant_memory_ids=["m1", "m2", "m3"])
    results = [_ranked("m1"), _ranked("m9")]

    metrics = evaluate_memory_retrieval(case, results)

    assert metrics.memory_recall == 1 / 3
    assert metrics.memory_precision == 0.5


def test_no_relevant_memories_defined_yields_perfect_recall():
    case = MemoryRetrievalCase(query="q", relevant_memory_ids=[])

    metrics = evaluate_memory_retrieval(case, [_ranked("m1")])

    assert metrics.memory_recall == 1.0


def test_personalization_score_all_markers_present():
    answer = "You are learning Docker and working on the Personal AI OS project."

    score = personalization_score(answer, ["Docker", "Personal AI OS"])

    assert score == 1.0


def test_personalization_score_partial_markers():
    answer = "You are learning Docker."

    score = personalization_score(answer, ["Docker", "Kubernetes"])

    assert score == 0.5


def test_personalization_score_no_markers_required():
    assert personalization_score("generic answer", []) == 1.0


def test_temporal_correctness_all_in_range():
    period_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    period_end = datetime(2026, 1, 31, tzinfo=timezone.utc)
    timestamps = [datetime(2026, 1, 15, tzinfo=timezone.utc), datetime(2026, 1, 20, tzinfo=timezone.utc)]

    score = temporal_correctness(timestamps, period_start, period_end)

    assert score == 1.0


def test_temporal_correctness_some_out_of_range():
    period_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    period_end = datetime(2026, 1, 31, tzinfo=timezone.utc)
    timestamps = [
        datetime(2026, 1, 15, tzinfo=timezone.utc),  # in range
        datetime(2025, 6, 1, tzinfo=timezone.utc),   # out of range
    ]

    score = temporal_correctness(timestamps, period_start, period_end)

    assert score == 0.5


def test_temporal_correctness_no_timestamps():
    period_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    period_end = datetime(2026, 1, 31, tzinfo=timezone.utc)

    assert temporal_correctness([], period_start, period_end) == 0.0
