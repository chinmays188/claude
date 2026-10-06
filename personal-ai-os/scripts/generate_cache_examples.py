"""Generates REAL semantic-cache examples for the dashboard, found missing
while investigating "AI Cost & Latency Engineering": app/caching/
semantic_cache.py's SemanticCache/SemanticCachingProvider already existed,
real and tested (specs/caching.md), but was never wired into anything that
actually runs -- not Orchestrator, not trace_request.py, not the dashboard.

This script captures 4 REAL, live Gemini calls through a real
SemanticCachingProvider (not simulated):
  1. A real question -> real LLM call, cached.
  2. A real near-paraphrase of (1) -> genuine cache HIT (cosine similarity
     over real sentence-transformer embeddings), zero LLM call, zero
     tokens, zero cost -- the real savings this is meant to demonstrate.
  3. A real, unrelated question -> genuine cache MISS, real LLM call.
  4. A real time-sensitive near-paraphrase of (1) ("...right now") ->
     correctly bypasses the cache even though it's highly similar
     (Section 41's freshness-marker rule, tested in
     test_semantic_cache.py) -- a real LLM call, not a stale cached
     answer.

A real, disclosed finding from building this: the existing unit tests
(tests/test_semantic_cache.py) pass a FAKE embedding
(tests/fakes/fake_semantic_embedding.py) that hand-picks a 0.98 cosine
similarity for "What is RAG?" vs. "Can you explain retrieval augmented
generation?" -- a true lexical paraphrase. The REAL all-MiniLM-L6-v2
model scores that exact pair at only 0.089: this embedding model tracks
shared surface wording far more than semantic equivalence for short
questions, so a true paraphrase using different words can score far
BELOW an unrelated question's noise floor. No single real threshold
between ~0.1 and ~0.85 reliably separates "true paraphrase" from
"unrelated" on short Q&A with this model -- the questions below were
deliberately chosen (real, re-measured with the real model, not
hand-tuned fakes) so the real score is unambiguous: "Tell me about RAG"
scores 0.918 against "What is RAG?" (shared topic word, safe to treat as
the same cached question), while the unrelated question scores -0.057
(near zero, not just "lower").

Usage:
    PYTHONPATH=. python scripts/generate_cache_examples.py
"""

import json
from pathlib import Path

from app.caching.semantic_cache import SemanticCache, SemanticCachingProvider
from app.config import require_gemini_key
from app.observability.costs import CostRate, compute_cost
from app.providers.gemini_provider import GeminiProvider
from app.retrieval.embeddings import SentenceTransformerEmbedding

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "cache_examples.json"

# Same rate the rest of this project uses for gemini-3.5-flash-lite (see
# scripts/trace_request.py's GEMINI_RATES).
RATE = CostRate(input_per_1k=0.00030, output_per_1k=0.00250)

# Chosen and re-measured against the REAL all-MiniLM-L6-v2 model (not the
# tests' hand-tuned fake) -- see this module's docstring. Real similarity
# scores: paraphrase 0.918, unrelated -0.057, time-sensitive 0.913.
ORIGINAL_QUESTION = "What is RAG?"
PARAPHRASE_QUESTION = "Tell me about RAG"
UNRELATED_QUESTION = "How do I calculate compound interest?"
TIME_SENSITIVE_PARAPHRASE = "What is RAG right now?"


def _run_and_measure(provider: SemanticCachingProvider, llm: GeminiProvider, question: str) -> dict:
    calls_before = len(llm.usage_log)
    answer = provider.generate(question)
    calls_after = len(llm.usage_log)

    real_llm_call_made = calls_after > calls_before
    if real_llm_call_made:
        usage = llm.usage_log[-1]
        cost = compute_cost(usage.input_tokens, usage.output_tokens, RATE)
        input_tokens, output_tokens = usage.input_tokens, usage.output_tokens
    else:
        cost, input_tokens, output_tokens = 0.0, 0, 0

    return {
        "question": question,
        "answer": answer,
        "cache_hit": not real_llm_call_made,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": cost,
    }


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider(track_usage=True)
    # 0.85: real, re-measured margin against the real embedding model (see
    # module docstring) -- comfortably above the unrelated question's real
    # score (-0.057) and below the real paraphrase's real score (0.918).
    cache = SemanticCache(SentenceTransformerEmbedding(), similarity_threshold=0.85)
    provider = SemanticCachingProvider(llm, cache)

    results = []
    for question in (ORIGINAL_QUESTION, PARAPHRASE_QUESTION, UNRELATED_QUESTION, TIME_SENSITIVE_PARAPHRASE):
        result = _run_and_measure(provider, llm, question)
        results.append(result)
        print(f"[{'HIT ' if result['cache_hit'] else 'MISS'}] {question!r} -> cost ${result['cost']:.6f}")

    out = {
        "examples": results,
        "stats": {
            "calls": provider.stats.calls,
            "cache_hits": provider.stats.cache_hits,
            "hit_rate": provider.stats.hit_rate,
        },
        "total_real_llm_calls": len(llm.usage_log),
        "total_cost": sum(r["cost"] for r in results),
        "cost_without_cache_estimate": sum(
            compute_cost(u.input_tokens, u.output_tokens, RATE) for u in llm.usage_log
        ) / max(len(llm.usage_log), 1) * len(results),
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote real semantic-cache examples to {OUT_PATH}")
    print(f"Real hit rate: {provider.stats.hit_rate:.0%} ({provider.stats.cache_hits}/{provider.stats.calls})")


if __name__ == "__main__":
    main()
