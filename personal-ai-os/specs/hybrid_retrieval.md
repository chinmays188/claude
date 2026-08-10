# Hybrid Retrieval

## Example 1 — Keyword match vector search misses

Input:
Query with an exact rare term (e.g. a product code) that a semantic embedding
might not weight highly, but that BM25 matches exactly.

Expected:
- `KeywordSearch.search()` ranks the exact-match chunk highly regardless of
  semantic similarity
- `HybridSearch` still surfaces it because keyword results are fused in

## Example 2 — Semantic match keyword search misses

Input:
Query phrased differently from the source text (paraphrase, no shared keywords).

Expected:
- `VectorStore.search()` finds it via semantic similarity
- `HybridSearch` still surfaces it because vector results are fused in

## Example 3 — Reciprocal rank fusion favors consensus

Input:
A chunk ranked #1 by both vector search and keyword search.

Expected:
- That chunk ranks first in the fused hybrid result (Example in
  `test_rrf_favors_chunk_ranked_high_in_both_lists`)

## Example 4 — Reranking narrows candidates

Input:
20 candidates retrieved by hybrid search; reranker asked for top 5.

Expected:
- `CrossEncoderReranker.rerank()` scores each (query, candidate) pair directly
  (more accurate than the bi-encoder/BM25 scores used for initial retrieval)
- Returns exactly `top_k` results, reordered by the cross-encoder score

## Non-goal for this milestone

- Latency measurement of the rerank step is not automated here (Section 24 flags
  it as important) — left as a manual experiment once real documents are ingested,
  since it depends on real hardware/model load time, not something a unit test
  can meaningfully assert.
