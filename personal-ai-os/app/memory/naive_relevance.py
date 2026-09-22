"""Naive keyword-overlap relevance matching over PersistentMemoryStore.

This is deliberately NOT semantic/embedding-based retrieval -- there is no
vector index over memories anywhere in this codebase (checked: only
app/retrieval/vector_search.py's VectorStore does embeddings, and it's used
for documents/achievements, never for MemoryRecord). Before this module,
neither DomainRouter nor ToolAgent/Orchestrator ever consulted memory at
all during a request.

Built specifically to give scripts/trace_request.py an honest, real (if
simple) answer to "how much memory was used for this trace": which stored
memories share words with the request text, ranked by overlap count. Good
enough to show real memory content was considered; not a claim of semantic
understanding.
"""

import re

from app.memory.models import MemoryRecord
from app.memory.persistent_store import PersistentMemoryStore

_WORD_RE = re.compile(r"[a-z0-9]+")

# Common words that would otherwise dominate overlap counts without
# indicating real topical relevance.
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "for", "and", "or", "my", "i", "me", "it",
    "this", "that", "what", "how", "do", "does", "did", "should", "will",
    "with", "at", "by", "as", "if", "so", "not", "can", "could", "would",
}


def _keywords(text: str) -> set[str]:
    words = _WORD_RE.findall(text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def find_relevant_memories(
    store: PersistentMemoryStore, tenant_id: str, user_id: str, query_text: str, top_k: int = 5
) -> list[tuple[MemoryRecord, int]]:
    """Returns up to top_k (memory, overlap_word_count) pairs, ranked by how
    many non-stopword keywords the memory's content shares with query_text.
    A memory with zero overlapping keywords is never returned (no fabricated
    relevance)."""
    query_keywords = _keywords(query_text)
    if not query_keywords:
        return []

    scored = []
    for memory in store.list_all(tenant_id, user_id):
        memory_keywords = _keywords(memory.content)
        overlap = len(query_keywords & memory_keywords)
        if overlap > 0:
            scored.append((memory, overlap))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]
