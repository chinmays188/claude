# Personal RAG

## Example 1 — Combines memory and documents, keeps them distinguishable

Input:
"What did I learn about RAG last month?"

Expected:
- `PersonalRagPipeline.answer()` retrieves relevant memories (`MemoryRetriever`)
  AND relevant documents (`SecureRetriever`) as two SEPARATE context sections
  (Section 2, capability #4: "distinguish memory from retrieved knowledge") —
  never merged into one undifferentiated blob before reaching the LLM

## Example 2 — Answers cite specific document chunks

Input:
A question matched by an ingested document chunk.

Expected:
- `PersonalRagResult.citations` lists the chunk id(s) actually used, reusing
  Phase 1's citation pattern (Section 21's `ResearchAgent`) rather than
  reinventing it

## Example 3 — Security is enforced even inside personal RAG

Input:
A document owned by a different user in the same tenant.

Expected:
- Never appears in `citations` or reaches the LLM's context — `SecureRetriever`
  (Milestone 19) is reused here unmodified, so the access-control guarantee
  ("the LLM must never enforce access control") holds for personal RAG too,
  not just for the raw retrieval API

## Example 4 — Memory precision / recall (Section 16)

Input:
A labeled `MemoryRetrievalCase` (query + which memory ids should be retrieved).

Expected:
- `evaluate_memory_retrieval()` computes precision/recall the same way Phase 1's
  `retrieval_eval.py` did for document chunks — this milestone extends that
  pattern to memory rather than replacing it

## Example 5 — Personalization score

Input:
An answer and a list of expected personal markers (specific facts only this
user's memory/documents would know — e.g. a project name, a real decision).

Expected:
- `personalization_score()` measures what fraction of those specific markers
  actually appear in the answer — a literal presence check, not a vague "does
  this feel personalized" judgment, so the metric stays auditable

## Example 6 — Temporal correctness

Input:
Retrieved items' timestamps compared against an expected time window (e.g.
"last month").

Expected:
- `temporal_correctness()` reports what fraction of retrieved items actually
  fall inside the expected period — catches the specific failure mode where
  semantically-relevant-but-wrong-era content gets retrieved (e.g. an old
  version of a decision that was later reversed)

## Non-goals for this milestone

- Query understanding (Section 14's first pipeline stage) is not a separate
  component here — the question is passed through as-is to both retrievers.
  A dedicated query-rewriting/expansion step is future work.
- Hybrid search + reranking (`HybridSearch`, `CrossEncoderReranker` from
  Phase 1 Milestone 9) are not wired into this pipeline yet — `SecureRetriever`
  currently wraps plain vector search only; combining it with hybrid retrieval
  is straightforward follow-up work, not done in this pass.
