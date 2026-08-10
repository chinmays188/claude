# Retrieval (RAG Pipeline)

## Example 1 — Ingest and retrieve

Input:
A document about RAG is ingested (chunked, embedded, stored). Query: "What is RAG?"

Expected:
- Document is split into chunks carrying `source`, `created_at`, `updated_at` (Section 25)
- `VectorStore.search()` returns the chunk(s) most relevant to the query
- Each result includes a score and the originating chunk id (for citation)

## Example 2 — Empty knowledge base

Input:
Query against a `VectorStore` with zero ingested chunks.

Expected:
- `search()` returns an empty list, not an error
- `RetrievalTool` reports "No relevant documents found." rather than crashing

## Example 3 — Agent grounds an answer in retrieval

Input:
`ResearchAgent` constructed with a populated `VectorStore`; user asks a question
the store has relevant chunks for.

Expected:
- Agent's tool-decision step may choose the `retrieve` tool (Milestone 3/5's loop)
- Retrieved chunks are cited by id in the final answer
- If the store has no relevant match, the agent says so rather than fabricating
  an answer (Section 18: don't evaluate RAG only by "was the final answer good")

## Example 4 — Chunking size/overlap experiment

Input:
Same document chunked with `chunk_size=250` vs `chunk_size=1000`; `overlap=0` vs `overlap=20%`.

Expected:
- Different chunk counts and boundaries per configuration
- `chunk_document()` accepts both parameters so this can be measured (Section 21)
- No single chunking strategy is hardcoded as "correct"

## Failure case — Invalid chunking parameters

Condition:
`chunk_size <= 0`, or `overlap >= chunk_size`.

Expected:
- `ValueError` raised immediately, not a silent no-op or infinite loop
