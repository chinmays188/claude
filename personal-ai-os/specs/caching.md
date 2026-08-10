# Caching

## Example 1 — Prompt caching: identical prompt hits cache

Input:
The exact same prompt sent twice through `PromptCachingProvider`.

Expected:
- The underlying LLM is called only once
- `stats.hit_rate` reflects the cache hit

## Example 2 — Prompt caching: different prompts both call the LLM

Input:
Two different prompts.

Expected:
- No false-positive cache hit; underlying LLM called for each

## Example 3 — Semantic caching: paraphrase hits cache

Input:
"What is RAG?" cached, then queried again as "Can you explain retrieval augmented
generation?"

Expected:
- `SemanticCache.get()` returns the cached answer despite no shared keywords —
  matches the paraphrase example in Section 40

## Example 4 — Semantic caching: unrelated query misses

Input:
A query with no semantic relation to anything cached.

Expected:
- Returns `None`, not a wrong cached answer forced into a similarity threshold

## Example 5 — Time-sensitive queries are never cached (Section 41)

Input:
"What is RAG today?" / "What changed in RAG recently?"

Expected:
- `looks_time_sensitive()` flags these via marker words (today/now/latest/recent/
  changed/updated/this week/this month)
- Such queries are neither written to nor read from the semantic cache — even if
  a highly similar cached entry exists, it is never returned for a time-sensitive
  query (`test_time_sensitive_query_never_reads_from_cache_even_if_similar`)

## Prompt vs. semantic caching — when each applies (Section 41)

- **Prompt caching** (`prompt_cache.py`): same large context/instructions, different
  requests. Local implementation here does full-response exact-match caching as a
  stand-in — real provider-side prompt caching (Gemini/Anthropic) caches at the
  token/prefill level server-side and reduces latency+cost even on a cache miss
  for the shared prefix; this distinction is noted in the module docstring, not
  glossed over.
- **Semantic caching** (`semantic_cache.py`): different wording, same underlying
  stable question. Must never apply to live/personalized/rapidly-changing/
  explicitly-latest-data requests (enforced via `looks_time_sensitive()`).
