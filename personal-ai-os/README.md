# Personal AI OS — Phase 1

An AI engineering learning lab, built milestone by milestone. See `../Personal AI Operating System.md` for the full spec and `../phase1-milestone1-plan.md` for the Milestone 1 plan.

- **Milestone 1**: Basic Agent (text → agent → response)
- **Milestone 2**: Multi-Agent Orchestration (text → classifier → Research/Analyst/Planner agent)
- **Milestone 3**: Tool Calling (agent → tool → result → agent)
- **Milestone 4**: Structured Output Reliability (repair loop, fallback chain)
- **Milestone 5**: Agent Guardrails (turn/tool/token/time budgets, stop conditions)
- **Milestone 6**: Voice — skipped for Phase 1 (CLI-only project; no browser frontend to host Web Speech API)
- **Milestone 7**: Retrieval (chunking, embeddings, FAISS vector search)
- **Milestone 8**: Retrieval Evaluation (recall, precision, grounding, citation quality)
- **Milestone 9**: Hybrid Retrieval (BM25 + vector search fusion, cross-encoder reranking)
- **Milestone 10**: Context Engineering (context builder, ordering, compression, lost-in-the-middle harness)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in GEMINI_API_KEY
```

## Run

```bash
python -m app.main "Explain RAG."
```

## Test

```bash
pytest
```

Tests use `FakeProvider`/fake embedding models and require no API key. Real-model integration
was manually verified for `SentenceTransformerEmbedding` and `CrossEncoderReranker` (they
download small models from Hugging Face on first use — not part of the automated suite to
keep it fast and offline).

## Design notes

- Agents never call a provider SDK directly — they call `llm.generate()` on an `LLMProvider` (see `app/providers/base.py`). This keeps model swapping/routing possible in later milestones.
- Behavior is specified by example in `specs/` (`basic_agent.md`, `orchestration.md`, `tool_calling.md`, `structured_output.md`, `guardrails.md`, `retrieval.md`, `retrieval_evaluation.md`, `hybrid_retrieval.md`, `context_engineering.md`), not prose requirements.
- Only Gemini is required to run; OpenRouter is optional and unused until Milestone 14 (Model Routing).
- `TaskClassifier` (`app/routing/classifier.py`) asks the LLM to return structured JSON and validates it with Pydantic — no keyword/regex matching. Low-confidence or malformed output does not fall back to a guess; it raises (`ClassificationError`) or routes to `unclear`.
- `Orchestrator` (`app/agents/orchestrator.py`) never guesses an agent for ambiguous input — it returns `ClarificationNeeded` instead, per Section 3's ambiguous-request example.
- `app/agents/basic_agent.py` (Milestone 1) is kept as-is; `app/agents/base.py` is the new shared base the specialized agents use.
- `Tool` (`app/tools/base.py`) contracts declare `args_schema`, `permissions`, and `retry_safe` per Section 30. Arguments are Pydantic-validated before execution (Section 32).
- `ToolRegistry` (`app/tools/registry.py`) is the only source of truth for callable tools — a hallucinated tool name is rejected, not executed (Section 58: tool hallucination → registry validation → reject).
- `ToolAgent` (`app/agents/tool_agent.py`) asks the LLM to decide tool-or-no-tool via structured JSON, executes at most one tool call, then does a final LLM turn with the tool result. `ResearchAgent` is now a `ToolAgent` wired with `CalculatorTool`.
- `RepairableGenerator` (`app/structured/repair.py`) wraps any `LLMProvider` + Pydantic schema: on validation failure it sends a repair prompt (previous output + error + schema) back to the LLM, up to `max_repair_attempts` (default 2, per Section 35). If still invalid, raises `StructuredOutputError` — never silently returns a guessed/default value. `TaskClassifier` now uses this instead of hand-rolled JSON parsing.
- `FallbackProvider` (`app/providers/fallback_provider.py`) wraps multiple `LLMProvider`s in priority order. If a provider fails, the next is tried; `fallback_occurred` is recorded and logged so a fallback is never silent (Section 36). If all fail, raises `AllProvidersFailedError`. Not yet wired into `main.py` — only Gemini is required per Section 8, so a real second provider (OpenRouter) is deferred to Milestone 14.
- `AgentBudget`/`BudgetTracker` (`app/guardrails/budgets.py`) enforce `max_turns`, `max_tool_calls`, `max_tokens`, `max_retries`, `timeout_seconds` per Section 59. `ToolAgent` (`app/agents/tool_agent.py`) was rewritten from a single-tool-call flow into a real bounded decide→act loop (`action: call_tool | final_answer`) so budgets are exercised against genuine runaway-loop scenarios (Section 15's "infinite planning" adversarial test), not just unit-tested in isolation. On budget exhaustion the agent returns a degraded response that says so explicitly (Section 38) rather than silently truncating — `AgentResponse.stop_reason` records why the loop ended (`task_completed`, `max_turns_reached`, `max_tool_calls_reached`, `timeout`).
- `app/retrieval/` implements the RAG pipeline (Section 20): `Document`/`Chunk` (with `source`/`created_at`/`updated_at`/`version` per Section 25), `chunk_document()` (configurable `chunk_size`/`overlap`, Section 21), `SentenceTransformerEmbedding` (`all-MiniLM-L6-v2`, free/local), `VectorStore` (FAISS flat L2 index), and `ingest()` tying them together. `RetrievalTool` (`app/tools/retrieval_tool.py`) exposes search to agents; `ResearchAgent` accepts an optional `VectorStore` and cites chunk ids when it retrieves.
- `app/evaluation/retrieval_eval.py` computes recall/precision against a labeled `RetrievalCase` (query → relevant chunk ids), independent of whether the final LLM answer looks good (Section 18). `app/evaluation/grounding_eval.py` uses an LLM-as-judge (via `RepairableGenerator`) to score groundedness and validate that citations point to chunks that were actually retrieved (`citation_quality()`), catching fabricated citations.
- `app/retrieval/keyword_search.py` (BM25) and `app/retrieval/hybrid_search.py` (`HybridSearch`, reciprocal rank fusion) implement Section 23's hybrid retrieval — fusion avoids needing to normalize BM25 scores against FAISS L2 distances, which live on incompatible scales. `app/retrieval/reranker.py` (`CrossEncoderReranker`, `cross-encoder/ms-marco-MiniLM-L-6-v2`) implements Section 24's retrieve-then-rerank pattern.
- `app/context/builder.py` (`ContextBuilder`) assembles prompts from named, prioritized sections in a configurable `order` (Section 27) — sections outside the configured order are dropped, empty sections are omitted, and when `max_tokens` is set, lowest-priority sections are dropped first until the budget fits (Section 29), never blindly concatenating everything (Section 26). `app/context/lost_in_middle.py` provides a harness for placing a critical fact at the start/middle/end of filler content (Section 28) — the harness is built and tested here; running it against Gemini to measure actual position-dependent quality loss is a follow-up experiment, not something a unit test can assert.
- Neither the hybrid-retrieval nor context-engineering modules are wired into `ResearchAgent`/`main.py` yet — they exist as standalone, tested components ready for that integration, consistent with the doc's milestone-by-milestone build order (wiring into the live agent loop / adding a real ingested corpus is natural follow-up work, not scoped into this batch).

## Bug found and fixed during manual verification (Milestone 5 rewrite)

Real Gemini output occasionally wraps JSON in a markdown code fence and writes
literal (unescaped) newlines inside a JSON string value when producing multi-paragraph
prose — technically invalid JSON per spec, but a common LLM failure mode. Before the fix,
`ToolAgent._decide` caught the resulting `JSONDecodeError` and silently treated the
**entire raw response** (fence, broken JSON, and all) as the final answer, leaking it
straight to the user. Fixed in two places:
- `app/utils/json_extract.py:loads_lenient()` — escapes literal control characters found
  inside JSON string literals before parsing, fixing this exact failure mode with zero
  extra LLM calls.
- `app/agents/tool_agent.py` — `_decide()` now goes through `RepairableGenerator`
  (Milestone 4) instead of a bare try/except, so any JSON `loads_lenient` still can't fix
  gets a real repair attempt instead of a silent, user-visible fallback.
Both fixes are covered by tests (`tests/test_json_extract.py`,
`tests/test_tool_agent.py::test_decision_json_with_literal_newlines_in_answer_is_recovered`)
and re-verified against the live Gemini API.
