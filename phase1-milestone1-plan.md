# Phase 1 — Milestone 1 Plan: Basic Agent

Source: `Personal AI Operating System.md` (Section 62, Milestone 1)

## Goal

Get a minimal working loop:

```text
Text → Agent → Response
```

While learning: API calls, prompts, model interface, structured output.

## Why start here

- Every later milestone (multi-agent, tools, RAG, guardrails, voice) depends on a working provider abstraction and response loop.
- Section 7 requires agents to never call a provider (e.g. Gemini) directly — they call `llm.generate()`. Getting this abstraction right now avoids rework in Milestones 2–17.
- Section 10 requires spec-by-example instead of prose requirements — so behavior for even this simple agent should be captured as examples, not "the system shall..." statements.

## Scope (in)

1. **Repo skeleton** (subset of Section 9 structure):
   ```text
   personal-ai-os/
   ├── app/
   │   ├── main.py
   │   ├── config.py
   │   └── agents/
   │       └── basic_agent.py
   ├── specs/
   │   └── basic_agent.md
   ├── tests/
   │   └── test_basic_agent.py
   ├── .env.example
   ├── .gitignore
   └── README.md
   ```

2. **Provider abstraction** (Section 7):
   - `LLMProvider` interface (abstract base)
   - `GeminiProvider` implementing it (Gemini 2.5 Flash-Lite, free tier)
   - Config loads `GEMINI_API_KEY` from `.env` (Section 8) — no keys committed

3. **Basic agent**:
   - Takes text input
   - Calls `llm.generate(prompt)` — never touches the Gemini SDK directly
   - Returns a structured response (see below)

4. **Structured output** (Section 34):
   - Minimal Pydantic schema, e.g.:
     ```python
     class AgentResponse(BaseModel):
         input: str
         output: str
         model: str
     ```
   - No repair loop yet (that's Milestone 4) — just validate the shape

5. **Spec-by-example** (`specs/basic_agent.md`, Sections 10–11 format):
   - 2–3 examples: a normal input, an empty/blank input, a very long input
   - Each with: Input / Expected output / Edge cases / Failure cases

6. **One test file**:
   - `pytest` test(s) that exercise the examples from the spec file

## Scope (out — deferred to later milestones)

- Multi-agent orchestration / classifier (Milestone 2)
- Tool calling (Milestone 3)
- Repair/fallback loops (Milestone 4)
- Guardrails/budgets (Milestone 5)
- Voice I/O (Milestone 6)
- Retrieval/RAG (Milestones 7–10)
- Evaluation framework, observability, cost, caching, safety, model adaptation (Milestones 11–17)

## Definition of done for Milestone 1

- Running `python app/main.py "Explain RAG"` (or equivalent) returns a validated `AgentResponse`
- Swapping `GeminiProvider` for a stub/fake provider requires no changes to `basic_agent.py`
- `pytest` passes against the example cases in `specs/basic_agent.md`
- No API key committed to git; `.env.example` documents required vars

## Open questions for you

- Where should the actual `personal-ai-os/` project live — new folder under `Project/`, or a separate repo?
- Confirm: Gemini 2.5 Flash-Lite as the only required provider for M1 (OpenRouter optional, per Section 8)?
