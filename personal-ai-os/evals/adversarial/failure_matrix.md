# Production Failure Matrix

Per Section 58 of the spec. Each row is a known failure mode this codebase detects
and recovers from, with a pointer to where it's implemented and tested.

| Failure | Detection | Recovery | Implemented in |
|---|---|---|---|
| Malformed JSON | Schema validation | Repair (max 2 attempts) | `app/structured/repair.py` |
| Tool hallucination | Tool registry validation | Reject, fall back to no-tool answer | `app/tools/registry.py` |
| Invalid arguments | Pydantic | Repair / reject (`ArgumentValidationError`) | `app/tools/base.py` |
| Tool timeout | — | Not implemented (tools here are synchronous/local; no network tool exists yet) | — |
| Search failure | — | Not implemented (no external search tool integrated yet — `retrieve` tool is local FAISS, not network-dependent) | — |
| Stale retrieval | Freshness metadata (`created_at`/`updated_at`) | Not yet actioned — metadata exists but no re-retrieval policy built | `app/retrieval/document.py` |
| Retrieval miss | Recall/precision eval | Query expansion not implemented; hybrid search + reranking mitigate | `app/evaluation/retrieval_eval.py`, `app/retrieval/hybrid_search.py` |
| Infinite loop | Loop budget (`max_turns`) | Stop, return degraded response | `app/guardrails/budgets.py`, `app/agents/tool_agent.py` |
| Too many tools | Tool budget (`max_tool_calls`) | Stop, return degraded response | `app/guardrails/budgets.py` |
| Context overflow | Token budget | Compress (drop lowest-priority sections) | `app/context/builder.py` |
| Prompt injection | Untrusted-content framing | Reject/ignore embedded instructions | `app/evaluation/adversarial.py`, `app/safety/injection.py` |
| Data leakage | Permission layer / tenant scoping | Block cross-tenant access | `app/safety/permissions.py`, `app/memory/store.py` |
| Model unavailable | Provider error | Fallback to next provider | `app/providers/fallback_provider.py` |
| Silent regression | Regression eval | Block release (report only — no CI wiring in Phase 1) | `app/evaluation/regression.py` |

Rows marked "Not implemented" are honest gaps for this phase — noted here rather than
silently omitted, consistent with Section 66's philosophy of tracking what's actually
been verified vs. what's aspirational.
