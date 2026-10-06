"""Mermaid source for the Caching page's dedicated architecture diagram.
Every box/edge traces to real code, verified by reading it directly.

Built while investigating "AI Cost & Latency Engineering" ("what is still
missing"). Checked first, honestly: app/caching/prompt_cache.py and
app/caching/semantic_cache.py both existed, real and tested since Phase
1 -- but NEITHER was ever wired into Orchestrator or trace_request.py.
This diagram shows the semantic cache's real wiring, and the real
threshold finding from building scripts/generate_cache_examples.py: the
existing unit tests passed a FAKE embedding that hand-picked a 0.98
similarity for a lexical paraphrase -- the REAL all-MiniLM-L6-v2 model
scores that same pair at only 0.089, so the real cache uses a real,
re-measured 0.85 threshold and real example questions chosen to actually
separate on the real model, not the fake's hand-picked vectors.
"""

CACHING_DIAGRAM = r"""
flowchart TB
    REQUEST["Agent generation request\n(Orchestrator's agent_llm)"]
    REQUEST --> SEMCACHE

    subgraph SEMCACHE["SemanticCachingProvider -- wraps the real LLM"]
        direction TB
        FRESH{"looks_time_sensitive()?\n(today/now/latest/recent/\nchanged/updated marker words)"}
        FRESH -->|yes| SKIPCACHE["Never read or write cache --\nalways a real LLM call"]
        FRESH -->|no| LOOKUP{"Real cosine similarity vs\nevery cached (query, response)\npair, via real sentence-transformer\nembeddings >= 0.85?"}
        LOOKUP -->|"yes (HIT)"| CACHED["Return cached response\nzero LLM call, zero tokens,\nzero cost"]
        LOOKUP -->|"no (MISS)"| REALCALL["Real LLM call, result\ncached for future similar queries"]
    end

    SKIPCACHE --> LLM["Real GeminiProvider"]
    REALCALL --> LLM

    FINDING["Real finding while building this:\ntests/test_semantic_cache.py's FakeSemanticEmbedding\nhand-picks 0.98 similarity for a lexical paraphrase --\nthe REAL model scores that same pair at only 0.089.\nReal threshold (0.85) + real example questions\nre-measured against the real model, not the fake."]
    LOOKUP -.-> FINDING

    STATS["SemanticCacheStats\nreal calls / cache_hits / hit_rate\n(found missing -- PromptCachingProvider\nalready had this, SemanticCachingProvider didn't)"]
    SEMCACHE -.-> STATS
    STATS --> CACHEEXAMPLES["app/dashboard_ui/cache_examples.json\ngenerate_cache_examples.py --\n4 real live Gemini calls,\n1 real genuine cache hit"]
"""
