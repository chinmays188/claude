from datetime import datetime, timezone

import pytest

from app.retrieval.chunking import chunk_document
from app.retrieval.document import Document

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _doc(text: str) -> Document:
    return Document(id="doc1", text=text, source="test", created_at=NOW, updated_at=NOW)


def test_chunks_short_document_into_one_chunk():
    doc = _doc("one two three")

    chunks = chunk_document(doc, chunk_size=10)

    assert len(chunks) == 1
    assert chunks[0].text == "one two three"
    assert chunks[0].document_id == "doc1"


def test_chunks_long_document_into_multiple_pieces():
    doc = _doc(" ".join(f"word{i}" for i in range(25)))

    chunks = chunk_document(doc, chunk_size=10, overlap=0)

    assert len(chunks) == 3
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


def test_overlap_repeats_words_across_chunks():
    doc = _doc(" ".join(f"word{i}" for i in range(20)))

    chunks = chunk_document(doc, chunk_size=10, overlap=5)

    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert first_words[-5:] == second_words[:5]


def test_empty_document_produces_no_chunks():
    doc = _doc("")

    chunks = chunk_document(doc, chunk_size=10)

    assert chunks == []


def test_invalid_chunk_size_raises():
    doc = _doc("some text")

    with pytest.raises(ValueError):
        chunk_document(doc, chunk_size=0)


def test_overlap_too_large_raises():
    doc = _doc("some text")

    with pytest.raises(ValueError):
        chunk_document(doc, chunk_size=5, overlap=5)


def test_chunks_carry_freshness_metadata():
    doc = _doc("some text here")

    chunks = chunk_document(doc, chunk_size=10)

    assert chunks[0].source == "test"
    assert chunks[0].created_at == NOW
    assert chunks[0].updated_at == NOW
