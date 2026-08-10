# Model Adaptation Experiment

Sample task: **"Answer questions about this project's own spec document
(`Personal AI Operating System.md`) accurately, citing the relevant section."**

This task was chosen because it's a real capability already partially built in
this codebase (RAG pipeline from Milestones 7-10) and because a spec document is
exactly the kind of "our own private, evolving knowledge" content that makes the
tradeoffs between these four approaches concrete rather than abstract.

## Comparison

| Approach | Cost | Latency | Quality (for this task) | Maintenance | Freshness | Data requirement | Failure modes |
|---|---|---|---|---|---|---|---|
| **In-context learning** (paste the doc into the prompt) | Low per-call, but scales with doc size — grows linearly as the spec grows | Higher prefill latency as doc grows; no extra infra | Good if doc fits in context; degrades with lost-in-the-middle on a long doc | None — just re-paste the current doc | Perfect (always current doc) | None — zero-shot | Breaks silently once the doc exceeds context window; no citation grounding without extra prompting |
| **RAG** (what Milestones 7-10 built) | Low — embedding + local vector search, no training cost | Adds a retrieval step (~10s of ms locally), but avoids sending the whole doc every call | Good, with citations, and scales to documents far larger than any context window | Re-ingest on doc changes (one function call: `ingest()`) | Excellent — freshness metadata built in (Section 25), just re-ingest changed sections | A chunked, embedded copy of the doc | Retrieval miss (wrong chunk retrieved) if chunking/embedding is poor; mitigated by Milestone 9's hybrid search |
| **Fine-tuning** | High — GPU training cost, plus this project has zero training infrastructure | Fast at inference (no retrieval step) | Poor fit for this task — the doc changes as the project evolves, and fine-tuning bakes in a frozen snapshot | High — must retrain on every meaningful doc change | Poor — knowledge is frozen at training time, exactly wrong for a document that's still being written | A labeled Q&A dataset derived from the doc — doesn't exist, would need to be authored | Silently confident wrong answers about outdated sections after the doc changes; no built-in citation mechanism |
| **Distillation** | Very high — requires both a teacher model and a training pipeline; not applicable here at all | N/A — not implemented | N/A | N/A | N/A | A large volume of teacher-generated examples | N/A — see verdict below |

## Verdict for this specific task

**RAG is the correct choice, and this is exactly why Milestones 7-10 built it.**
The spec document changes as the project evolves (we've been actively adding
milestones), answers need to cite which section they come from, and there's no
labeled training dataset — every one of Section 57's RAG-favoring signals
(`needs_fresh_external_knowledge`) applies directly.

## When each approach would be the WRONG choice (Section 57's real point)

- **RAG would be wrong** if the task were "always respond in this exact JSON
  schema" or "always use this specific tone/persona" — that's a formatting/style
  constraint RAG doesn't reliably enforce; see `system_prompt` + fine-tuning
  territory instead (Milestone 2's agents already lean on system prompts for
  this, which is the ICL-flavored version of that same fix).
- **Fine-tuning would be wrong** here specifically *because* the underlying
  document is still changing — baking in a snapshot mid-development guarantees
  stale answers within days. Fine-tuning is right when behavior needs to be
  stable and the underlying facts are NOT changing (e.g. "always format numbers
  as ₹X,XXX" is a stable behavioral constraint; "what does section 12 currently
  say" is not).
- **In-context learning would be wrong** once the spec document (or a real
  knowledge base) exceeds the context window, or when the same document needs
  to be reused across many independent requests — repeatedly pasting the full
  doc into every prompt is exactly the "same large context, different requests"
  case Section 41 flags as a prompt-caching candidate, not a reason to skip RAG.
- **Distillation would be wrong** for this task entirely — there's no smaller
  model here needing to reproduce a stronger model's behavior; distillation
  solves a cost/latency problem for a *different* task shape (see
  `app/evaluation/adaptation_advisor.py`'s `needs_smaller_model_to_match_larger_model`
  signal), not a freshness or knowledge-grounding problem.

## What's implemented vs. documented here

- **RAG**: fully implemented (Milestones 7-10) — this experiment's verdict is
  literally what the codebase already does.
- **In-context learning**: implemented implicitly via agent `system_prompt`s
  (Milestone 2) for behavioral framing, not exercised here for the full-document
  case — no code changes needed to demonstrate it (just paste the doc into a
  prompt), so it isn't given a dedicated module.
- **Fine-tuning / distillation**: not implemented — no training infrastructure
  exists in this project, and per Section 56 the objective is to understand
  *when* each is the wrong tool, not to implement all four. `recommend_approach()`
  in `app/evaluation/adaptation_advisor.py` codifies the decision logic
  (Section 57) as a testable function, which is the actionable artifact from
  this milestone.
