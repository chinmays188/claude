from datetime import datetime, timezone

from app.retrieval.document import Chunk
from app.retrieval.keyword_search import KeywordSearch

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _chunk(id_: str, text: str) -> Chunk:
    return Chunk(
        id=id_, document_id="doc1", text=text, source="test",
        created_at=NOW, updated_at=NOW, chunk_index=0,
    )


def test_empty_index_returns_no_results():
    search = KeywordSearch()

    assert search.search("anything") == []


def test_exact_keyword_match_ranks_first():
    search = KeywordSearch()
    search.add(
        [
            _chunk("c1", "The Eiffel Tower is a famous landmark in Paris."),
            _chunk("c2", "Bananas are a good source of potassium."),
            _chunk("c3", "The stock market fell sharply on Tuesday."),
            _chunk("c4", "Cats sleep for most of the day."),
        ]
    )

    results = search.search("Eiffel Tower Paris")

    assert results[0].chunk.id == "c1"


def test_no_keyword_overlap_returns_no_results():
    search = KeywordSearch()
    search.add([_chunk("c1", "completely unrelated content about gardening")])

    results = search.search("quantum physics")

    assert results == []


def test_len_reflects_chunk_count():
    search = KeywordSearch()
    search.add([_chunk("c1", "a"), _chunk("c2", "b")])

    assert len(search) == 2
