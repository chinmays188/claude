"""Structural tests on the committed app/dashboard_ui/rag_examples.json --
does NOT re-run scripts/generate_rag_examples.py (that makes real,
paid Gemini calls and loads a real embedding model; slow and non-free,
appropriate for a one-off local generation run, not the test suite).
Instead verifies the shape and internal consistency of what was
committed, so a hand-edit or partial regeneration can't silently corrupt
the page's data."""

import json
from pathlib import Path

RAG_EXAMPLES_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "rag_examples.json"


def _load():
    return json.loads(RAG_EXAMPLES_PATH.read_text())


def test_rag_examples_file_exists_and_parses():
    data = _load()
    assert isinstance(data, dict)


def test_has_all_expected_top_level_sections():
    data = _load()
    expected = {
        "documents", "chunks", "question", "vector_search_results",
        "keyword_search_results", "fused_results", "reranked_results",
        "retrieval_ground_truth", "retrieval_metrics", "final_answer",
        "citations", "memory_used", "grounding", "citation_quality_score",
    }
    assert expected.issubset(data.keys())


def test_chunks_reference_real_documents():
    data = _load()
    document_ids = {d["id"] for d in data["documents"]}
    for chunk in data["chunks"]:
        assert chunk["document_id"] in document_ids


def test_retrieval_metrics_are_valid_fractions():
    data = _load()
    metrics = data["retrieval_metrics"]
    assert 0.0 <= metrics["recall"] <= 1.0
    assert 0.0 <= metrics["precision"] <= 1.0


def test_grounding_score_is_valid_fraction():
    data = _load()
    assert 0.0 <= data["grounding"]["groundedness_score"] <= 1.0


def test_citation_quality_score_is_valid_fraction():
    data = _load()
    assert 0.0 <= data["citation_quality_score"] <= 1.0


def test_every_cited_chunk_id_exists_among_chunks():
    """The whole point of citation_quality() -- verify it was actually
    computed against real chunk ids, not placeholders."""
    data = _load()
    chunk_ids = {c["id"] for c in data["chunks"]}
    for citation in data["citations"]:
        assert citation["chunk_id"] in chunk_ids


def test_final_answer_is_nonempty_real_text():
    data = _load()
    assert len(data["final_answer"]) > 20  # a real generated answer, not a stub
