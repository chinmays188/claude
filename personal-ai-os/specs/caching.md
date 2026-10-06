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

## Example 6 — Wired into a real request path, with a real threshold finding

Input:
Investigating "AI Cost & Latency Engineering" ("what is still missing") found that
Examples 1-5 above were all real and tested, but neither `PromptCachingProvider` nor
`SemanticCachingProvider` was ever wired into `Orchestrator` or any real request path
-- the same "built but never wired in" pattern found repeatedly elsewhere in this
project (semantic memory retrieval, `PersonalContextEngine`, `PolicyEngine`).

Expected / what was built:
- `SemanticCachingProvider` can be passed as `Orchestrator`'s optional `agent_llm`,
  the same slot `RoutingLLMProvider` uses — no `Orchestrator` change needed.
- New `SemanticCacheStats` (calls/cache_hits/hit_rate) on `SemanticCachingProvider`,
  matching `PromptCachingProvider`'s existing `PromptCacheStats` — it previously had
  no hit-rate visibility at all.
- `scripts/generate_cache_examples.py` ran 4 real, live Gemini calls through a real
  `SemanticCachingProvider`: a question, a real near-paraphrase (genuine cache HIT —
  zero LLM call, zero tokens, zero cost), a real unrelated question (MISS), and a
  real time-sensitive near-paraphrase (correctly bypasses the cache per
  `looks_time_sensitive()`, even though it's similarity-close to the original).
- **A real, significant finding surfaced while building this**: Example 3 above
  passes only because `tests/fakes/fake_semantic_embedding.py` hand-picks a 0.98
  cosine similarity for `"What is RAG?"` vs. `"Can you explain retrieval augmented
  generation?"`. The REAL `all-MiniLM-L6-v2` model scores that exact pair at only
  **0.089** — real, measured, not assumed. This embedding model tracks shared
  surface wording far more than semantic equivalence for short questions: a
  different-worded true paraphrase can score far below an unrelated question's
  noise floor (real measured unrelated-question score: -0.057), while a
  lexically-similar rewording like `"Tell me about RAG"` scores 0.918. No single
  real threshold between ~0.1 and ~0.85 reliably separates "true paraphrase" from
  "unrelated" with this model on short Q&A. Fixed by re-measuring real similarity
  scores against the real model and picking a real, defensible threshold (0.85)
  and real example questions chosen to actually separate on the real model, not
  the fake's hand-picked vectors — this is a real, disclosed limitation of the
  semantic cache's practical hit rate for short, differently-worded questions,
  not something to paper over.

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
