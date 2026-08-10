from datetime import datetime, timezone

from app.evaluation.retrieval_eval import (
    RetrievalCase,
    average_metrics,
    evaluate_retrieval,
)
from app.retrieval.document import Chunk
from app.retrieval.vector_search import ScoredChunk

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _scored(id_: str) -> ScoredChunk:
    chunk = Chunk(
        id=id_, document_id="doc1", text="text", source="test",
        created_at=NOW, updated_at=NOW, chunk_index=0,
    )
    return ScoredChunk(chunk=chunk, score=0.1)


def test_perfect_recall_and_precision():
    case = RetrievalCase(query="q", relevant_chunk_ids=["c1", "c2"])
    results = [_scored("c1"), _scored("c2")]

    metrics = evaluate_retrieval(case, results)

    assert metrics.recall == 1.0
    assert metrics.precision == 1.0


def test_partial_recall():
    case = RetrievalCase(query="q", relevant_chunk_ids=["c1", "c2", "c3", "c4", "c5"])
    results = [_scored("c1"), _scored("c2"), _scored("c3"), _scored("c9")]

    metrics = evaluate_retrieval(case, results)

    assert metrics.recall == 0.6  # 3 of 5 relevant found
    assert metrics.precision == 0.75  # 3 of 4 retrieved were relevant


def test_no_relevant_chunks_retrieved():
    case = RetrievalCase(query="q", relevant_chunk_ids=["c1"])
    results = [_scored("c9"), _scored("c10")]

    metrics = evaluate_retrieval(case, results)

    assert metrics.recall == 0.0
    assert metrics.precision == 0.0


def test_empty_relevant_set_yields_perfect_recall_by_convention():
    case = RetrievalCase(query="q", relevant_chunk_ids=[])
    results = [_scored("c1")]

    metrics = evaluate_retrieval(case, results)

    assert metrics.recall == 1.0


def test_no_results_retrieved():
    case = RetrievalCase(query="q", relevant_chunk_ids=["c1"])

    metrics = evaluate_retrieval(case, [])

    assert metrics.recall == 0.0
    assert metrics.precision == 0.0


def test_average_metrics_across_cases():
    case1 = RetrievalCase(query="q1", relevant_chunk_ids=["c1"])
    case2 = RetrievalCase(query="q2", relevant_chunk_ids=["c2"])
    m1 = evaluate_retrieval(case1, [_scored("c1")])
    m2 = evaluate_retrieval(case2, [_scored("c9")])

    avg = average_metrics([m1, m2])

    assert avg["recall"] == 0.5
    assert avg["n"] == 2


def test_average_metrics_empty_list():
    avg = average_metrics([])

    assert avg["n"] == 0
