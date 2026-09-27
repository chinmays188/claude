# Dashboard UI (portfolio MVP)

## Scope decision

Streamlit, matching Section 5's original stack table ("Visualization:
Streamlit initially"). Built as a portfolio-facing MVP first (per project
decision), but designed to grow into daily use rather than be throwaway: it
reads the real SQLite stores directly, so real usage of the CLI/voice
interface naturally populates it over time, replacing/extending the seeded
demo data rather than requiring a separate "real" version later.

## What was built

- `scripts/seed_demo_data.py`: populates the real stores (`PersistentMemoryStore`,
  `GoalStore`, `GraphStore`, `TaskStore`, `AuditLog`, `CommitmentStore`,
  `OutcomeStore`) with fabricated, realistic demo data — consistent with the
  project's synthetic-data-only convention for domain workflows.
- `dashboard_app.py`: a Streamlit app with 6 pages (Overview, Career, PM,
  Finance, Learning, Chief of Staff), each backed directly by an existing,
  already-tested `app/dashboard/*.py` function. No new backend logic exists
  in this UI layer at all.
- `app/dashboard_ui/demo_workflow_outputs.py`: fabricated values for the
  dashboard fields that are caller-supplied from domain workflow outputs
  rather than persisted anywhere (e.g. `resume_readiness`, feedback themes,
  portfolio allocation) — kept in one clearly-labeled module, separate from
  the real persisted data the seed script writes.
- `.streamlit/config.toml`: binds the server to `localhost` only. Without
  this, Streamlit defaults to binding all interfaces (`0.0.0.0`) — caught
  during manual testing when the server printed a `Network URL`/`External
  URL` briefly reachable from the local network.

## Example 1 — Every page renders from real, already-tested functions

Input: `dashboard_app.py`'s six `render_*` functions.

Expected:
- Each calls exactly one `app/dashboard/*.py` function (e.g.
  `render_finance` calls `get_finance_dashboard`) and only formats the
  result — verified by running all 6 render functions directly (bypassing
  Streamlit's script-runner context) and confirming none raise

## Example 2 — The seed script populates data the dashboard functions can actually read back

Input: `scripts/seed_demo_data.py --db <path>`.

Expected:
- Writing memories, goals, graph nodes/decisions, a completed task, an
  audit-log entry, commitments, and outcomes, then reading them back through
  `get_memory_summary`/`get_todays_activity`/`get_career_dashboard`/
  `get_chief_of_staff_snapshot` returns non-zero/populated results
- A real inconsistency was caught while wiring this up: Phase 2's
  `get_memory_summary()` counts `NodeType.DECISION` graph *nodes*, while
  Phase 3's richer `Decision` model lives in a separate `decisions` table —
  the two are not the same underlying data. Fixed by having the seed script
  write both a `Decision` record (via `add_decision()`) and a matching
  `GraphNode(type=DECISION)` for each seeded decision, so both
  representations reflect real demo data rather than silently disagreeing.

## Example 3 — The server binds to localhost only

Input: `streamlit run dashboard_app.py`.

Expected:
- Server output shows a single `URL: http://localhost:<port>` line, with no
  `Network URL`/`External URL` — confirmed by actually starting the server
  and inspecting its own log output, both with and without
  `.streamlit/config.toml` present (the fix was verified against the actual
  problem it fixes, not assumed)

## Example 4 — Traces page reads real, persisted live-request traces

Input: `scripts/trace_request.py "<request>"`, followed by opening the
dashboard's Traces page.

Expected:
- `trace_request.py` now wraps its real run (router + tool agent, live
  Gemini calls) in `app/observability/traces.py`'s `TraceRecorder`, and
  persists the resulting `Trace` (routing decision, real tool-call
  input/output as span metadata, real per-call token usage, real summed
  cost) to `data/personal_ai.db` via the new `app/observability/trace_store.py`
  (`TraceStore`), keyed by `trace.execution_id` (the trace_id printed at the
  end of the run)
- The dashboard's Traces page lists every saved trace_id in the sidebar
  (newest first) and lets a trace_id be pasted directly into a search box;
  selecting one renders its full stored trace — status, latency, cost,
  token counts, and every span (with tool-call args/results as span
  metadata) — with no live LLM call made by the dashboard itself
- Verified live end-to-end: ran `trace_request.py` against a real request,
  confirmed the trace persisted with correct spans/cost via `TraceStore`
  directly, then confirmed the dashboard's listing + lookup-by-id logic
  returns the same data

## Example 5 — Traces page shows real content on the public deployment too, without a live key

The user asked for the Traces page to appear on the actual public
deployment, not just locally. Adding a live "run a trace" box to the public
dashboard was considered and explicitly rejected (it would need
`GEMINI_API_KEY` in Streamlit Cloud's secrets, exposing the key to the
public app's runtime, plus real per-visitor API cost with no rate limiting)
in favor of:

- `app/dashboard_ui/example_traces.json` + `example_traces.py`: 5 REAL
  trace records, captured once by actually running `scripts/trace_request.py`
  locally against varied inputs (CAREER+LEARNING cross-domain, PM, FINANCE
  with a real calculator tool call, a second CAREER+LEARNING example, and
  one UNCLEAR routing) — not fabricated, but a fixed snapshot of real
  Gemini/router/agent behavior from one specific run. `seed_all()` now also
  calls `seed_example_traces()`, so every fresh deploy (including Streamlit
  Community Cloud's first-load auto-seed) gets these 5 traces with zero
  Gemini key required at seed time
- Verified: seeding runs successfully with `GEMINI_API_KEY=""` (confirmed
  via a real test with the env var unset), and every seeded trace round-trips
  through `TraceStore` correctly — including the nested tool-call span's
  exact real args/result
- Explicitly disclosed limitation: these 5 traces are static. The public
  dashboard's Traces page will always show the same 5 example traces; it
  does not let a public visitor submit their own live query (that would be
  the rejected "add a key to Streamlit secrets" path above). Anyone wanting
  to trace their own real input still runs `scripts/trace_request.py`
  locally.

## Example 6 — Architecture page + trace_request.py's dual-router instrumentation

The user asked 7 specific questions after using the Traces page: whether the
router routes to domain OS vs. research/planner/analyst agents, what tools
exist, what documents are embedded, what synthetic/eval data exists, memory
usage per trace, what goals GoalAgent has defined, and how Chief of Staff
"listens." Answering these required reading the actual code end to end
rather than assuming, which surfaced a real, previously-undocumented
architectural fact:

**There are two separate, disconnected routers.** `DomainRouter`
(CAREER/PM/FINANCE/LEARNING/UNCLEAR) is used only by `scripts/trace_request.py`
and tests — no production entry point calls it. `TaskClassifier` +
`Orchestrator` (RESEARCH/ANALYSIS/PLANNING/UNCLEAR, dispatching to
`ResearchAgent`/`AnalystAgent`/`PlannerAgent`) is what `app/main.py` and
`app/api/voice_api.py` actually use. Neither calls the other; nothing
combines their outputs.

Changes made, in response:

- `app/agents/orchestrator.py`: `Orchestrator.__init__` gained optional
  `retrieval_store` and `on_tool_call` params (default `None`, fully
  backward-compatible — verified with a regression test asserting identical
  behavior to before the change). Lets `ResearchAgent`'s `retrieve` tool
  actually work when wired through `Orchestrator`, and lets a caller observe
  real tool-call I/O through this path too.
- `app/agents/research_agent.py`: forwards `on_tool_call` to its `ToolAgent`
  base (was previously dropped).
- `app/memory/naive_relevance.py`: new, explicitly-labeled-as-naive
  keyword-overlap matching against `PersistentMemoryStore` — NOT semantic
  search (no vector index over memories exists anywhere in this codebase).
  Built specifically to give an honest answer to "how much memory is used
  per trace," since neither router previously consulted memory at all.
- `scripts/trace_request.py`: rewritten to run a request through BOTH real
  routers independently (not picking one), report which stored memories
  shared keywords with the request, support `--index-file` to give the
  research path's `retrieve` tool something real to search (real chunking +
  real embeddings), and record all of it as trace spans exactly as before.
- `app/dashboard_ui/architecture_diagram.py` + a new dashboard
  **Architecture** page: a Mermaid diagram (rendered via `st.html(...,
  unsafe_allow_javascript=True)` loading Mermaid.js from
  `cdnjs.cloudflare.com` — no new Python/system dependency, since Streamlit
  has no native Mermaid support and the `graphviz_chart` alternative needs a
  system `dot` binary not guaranteed present on Streamlit Cloud) showing the
  router disconnect, all 5 real tools, where retrieval/embeddings are
  actually used, and Chief of Staff's real pull-based (not always-on)
  design — plus live counts (goals from `GoalStore`, eval case counts from
  `count_cases_by_domain()`) queried fresh on page load, still with no live
  LLM call.
- The 5 committed example traces (`app/dashboard_ui/example_traces.json`)
  were regenerated against the new `trace_request.py` to reflect the dual
  routing + memory-lookup spans, including one real example that
  demonstrates the router disconnect directly: `DomainRouter` classifies
  "What's the weather like today?" as UNCLEAR, while `Orchestrator`
  independently routes the same input to `research_agent`.

Verified: the Mermaid diagram source was validated by actually rendering it
with `@mermaid-js/mermaid-cli` (via `npx`) to a real PNG and visually
inspecting the output, not assumed correct from syntax alone. All new/changed
code paths (`Orchestrator` params, `naive_relevance.py`,
`trace_request.py`'s dual-router run, `--index-file`) were run live against
the real Gemini API at least once. 702 tests passing (was 693).

## Example 7 — Combining the two disconnected routers into one

The user's feedback on the Architecture page: "We can't have 2 routers,
there has to be one router with a combination of both existing routers."
Design decision confirmed with the user first: domain (career/pm/finance/
learning) and task-type (research/analysis/planning) are different axes,
not redundant labels, so the combined router classifies both as two stages
rather than collapsing them into one combinatorial label set. Scope was
also confirmed explicitly: the combined router only routes to the existing
3 generic agents (now domain-aware), NOT directly to domain workflows like
`analyze_jd`/`draft_prd`/`analyze_portfolio` — those need specific typed
inputs (a `Portfolio` object, extracted JD text) that a plain chat message
doesn't provide, and remain invoked separately with real structured inputs.

- New `app/routing/unified_router.py` (`UnifiedRouter`): wraps the existing,
  already-tested `DomainRouter` and `TaskClassifier` internally (2 real LLM
  calls, same as running both separately did before — no attempt to fuse
  them into one call, which would mean rewriting and re-validating both
  prompts at once) and returns one `UnifiedClassification` with both a
  domain (or `None` for GENERAL — a first-class outcome, not an error) and
  a task-type.
- `app/agents/orchestrator.py`: `Orchestrator` now uses `UnifiedRouter`
  internally instead of `TaskClassifier` directly, and injects the
  classified domain into the dispatched agent's prompt as literal context
  text (e.g. `"[Context: this request has been classified under the CAREER
  domain.]"`) rather than changing `Agent`/`ToolAgent`'s `run()` signature,
  which would have touched every agent and every existing test. `handle()`'s
  signature and return type are unchanged, so `app/main.py` and
  `app/api/voice_api.py` needed ZERO code changes — confirmed by actually
  running `python -m app.main "Should I learn Kubernetes for my career?"`
  and seeing the real injected domain context and a visibly domain-aware
  answer ("As an analyst agent... career development...").
- Also added an optional `on_classified` observer hook on `Orchestrator`
  (mirroring the existing `on_tool_call` pattern) so a caller like
  `scripts/trace_request.py` can observe the router's real decision without
  `handle()`'s return type changing for every other caller.
- `scripts/trace_request.py` simplified from running two routers side by
  side to running the one combined router via `Orchestrator`, reusing the
  same classification for the `--with-eval` golden-case lookup (no longer a
  second, wasted LLM call).
- The Architecture diagram and the dashboard's warning banner were updated
  to show one `UnifiedRouter` (two internal stages) instead of "two
  disconnected routers," and the 5 committed example traces were
  regenerated against the new single-router trace format.

Verified: all 3 agents (`research_agent`/`analyst_agent`/`planner_agent`)
were confirmed reachable via the 5 regenerated example traces (a dedicated
test asserts all three appear); the domain-context injection was verified
with a dedicated test asserting the classified domain literally appears in
the prompt text the agent receives, and a second test asserting no context
is injected for GENERAL (no domain) so as not to add noise to unrelated
requests; a routing failure (`UnifiedRoutingError`) was verified to degrade
to a `ClarificationNeeded` response rather than propagate as an unhandled
exception into `app/main.py`/`voice_api.py`. Every existing test file that
scripted `Orchestrator`'s LLM call sequence (`test_orchestrator.py`,
`test_golden.py`, `test_voice_session.py`, `test_voice_api.py`) was updated
to account for the router now making 2 classification calls instead of 1.
713 tests passing (was 702).

## Example 8 — All 3 agents get real tools, a domain-workflow bridge, a Tools page, and a readable journey

Four more pieces of user feedback, addressed together:

1. **"Why would only research agent do tool calling? Even analyst and
   planner can do tool calling?"** -- a real asymmetry: `AnalystAgent` and
   `PlannerAgent` were plain, single-shot `Agent` subclasses with
   structurally NO ability to ever call a tool, while `ResearchAgent`
   extended `ToolAgent`. Fixed: both now extend `ToolAgent` too, sharing
   tool construction via new `app/agents/agent_tools.py`'s
   `build_shared_tools()`. Confirmed with the user: tool use is never
   forced -- `ToolAgent`'s existing per-turn decision loop already lets the
   LLM pick `final_answer` directly with no tool call, for any of the 3
   agents, on any given input.
2. **"resume_optimization, jd_analysis, prd... why are these separate and
   not part of research, analyst, planner?"** -- corrected understanding by
   reading the actual functions: `analyze_jd`/`draft_prd` need a
   `SecureRetriever` (they ground output in the user's own retrieved
   documents), not just text; `analyze_feedback` needs only a list of
   strings. `analyze_portfolio`/`evaluate_answer` need a real stored
   `Portfolio`/`Exercise` object a chat message can't manufacture --
   confirmed out of scope with the user. New
   `app/tools/domain_workflow_tools.py` bridges the three that ARE
   reachable (`analyze_feedback` always available; `analyze_jd`/`draft_prd`
   available when a `SecureRetriever` is wired in, reusing the same
   retrieval infra `--index-file` already builds) as real tools any of the
   3 agents can call.
3. **"How to add more tools (when can each of these tools be called...
   with their request and response example)"** -- new
   `scripts/generate_tool_examples.py` actually RUNS every one of the 8
   registered tools (calculator, retrieve, calendar_day, email_summary,
   github_activity, analyze_feedback, analyze_jd, draft_prd) against small,
   synthetic fixture data (the same in-memory/mocked-HTTP pattern this
   codebase's own tests already use for calendar/github) and writes real
   request/response pairs plus each tool's real Pydantic `args_schema` to
   `app/dashboard_ui/tool_examples.json`. New dashboard **Tools** page
   reads this committed file (no live LLM call on page render) and
   documents how to add a new tool.
4. **"We need to show the journey till output, don't see how we are
   finally getting the output"** -- the Traces page's span rendering was a
   collapsed, nested raw-JSON tree with no linear narrative. New
   `_render_journey()` walks the same span data into numbered steps
   (Input -> Memory considered -> Routing -> Tool call(s) -> Final output),
   falling back gracefully when a step type is absent (e.g. an UNCLEAR
   trace has no agent output). The old raw span tree is kept as a
   collapsed "Raw spans" detail section, not removed.

Verified: `AnalystAgent` was confirmed live to actually call the calculator
tool on a real comparison question ("Which is cheaper... 1500/month or a
flat 20000/year?"); `analyze_feedback` and `analyze_jd` were both confirmed
live end to end (real tool call, real structured JSON output, correctly
routed via `UnifiedRouter` to `analyst_agent`) -- `analyze_jd`'s example
specifically showed real `SecureRetriever`-grounded output citing the
indexed fixture achievement. All 8 tool examples in `tool_examples.json`
are real generator output, not hand-written (verified by inspecting every
one). The new Traces page journey was visually confirmed in a real browser
(via `agent-browser`) to render a complete, readable input-to-output
narrative for a real trace. 4 new tests for `AnalystAgent`/`PlannerAgent`
tool-calling (and no-tool-needed) behavior, 7 for the domain-workflow
bridge tools, 2 for the tool-example generator. 726 tests passing (was
713).

## Non-goals for this MVP

- No interactivity beyond viewing — no in-UI action approval, no
  triggering a workflow from a button. The dashboard is read-only,
  consistent with every dashboard milestone across Phases 2-4 being
  "data layer only."
- No authentication on the dashboard itself — it's a local, single-user
  portfolio demo; Phase 5's `app/platform/auth.py` exists but isn't wired
  into this UI.
- Career/PM/Finance/Learning fields sourced from domain workflow outputs
  (resume readiness, feedback themes, etc.) use fabricated demo values
  rather than actually invoking each domain's real LLM-driven workflow on
  every page load — doing so would mean a live Gemini API call (and cost)
  every time the dashboard renders, which isn't the right tradeoff for a
  page that's refreshed frequently during a demo.

## Example 9 — GoalStore holds the user's real learning goals, not fabricated data

"Goal store needs to be updated - ask me all the inputs." The user described
this project as a learning vehicle for an AI PM career, giving a detailed
15-capability learning map (LLM Fundamentals through AI Product Strategy).
Clarified with the user directly rather than assumed: this capability map
is REAL personal content, distinct from a second, not-yet-specified set of
real personal domain goals (Career/PM/Finance/Learning life goals) the user
also mentioned but deferred to a later step.

- New `app/dashboard_ui/user_learning_goals.py`: kept deliberately separate
  from `scripts/seed_demo_data.py` (whose docstring says everything in it
  is fabricated demo data) for the same reason `example_traces.py` is kept
  separate from `demo_workflow_outputs.py` — real content should never be
  silently mixed into a file that says it's all fake. Seeds all 15
  capabilities as real `Goal` records (`domain=LEARNING`), with
  `success_criteria` drawn verbatim from the user's own bullet points, and
  the user's explicitly chosen defaults: `priority=0.5`, `progress=0.0`, no
  deadline — to be updated later as their actual learning progresses, not
  invented here.
- The 4 previously-seeded fabricated demo goals (one per domain — a fake
  career goal, a fake Kubernetes goal, a fake PM goal, a fake finance goal)
  were removed per the user's explicit choice ("Remove them — replace with
  the 15 learning goals only for now"), confirmed as an acceptable
  side-effect that the Career OS/Finance OS dashboard pages now show 0
  goals (honestly reflecting no real goals yet there) while Learning OS
  jumps to 15.
- `scripts/seed_demo_data.py`'s `seed_all()` now calls
  `seed_learning_capability_goals()` instead of the removed `seed_goals()`.

Verified: seeded and confirmed live (both via direct `GoalStore` query and
in a real browser via `agent-browser`) that all 15 goals appear correctly
on the Architecture page's live goal count and the Learning OS page's
"Active learning goals" metric (now 15); confirmed Career OS/Finance OS
show 0 goals as expected. 5 new tests (exact count, all LEARNING domain,
idempotent re-seeding, every goal has success criteria, defaults match the
user's explicit choices). 731 tests passing (was 726).

## Deferred

- Real personal domain goals (Career/PM/Finance/Learning life goals,
  distinct from the capability-tracking list above) — the user mentioned
  wanting these tracked too, but specifics weren't given; a separate,
  later step once the user provides them.

## Example 10 — Learning OS page was showing fabricated data instead of the real 15 goals

The user caught two things after the progress-value updates: "these %
are not updated in the streamlit UI, also the learning page in UI is not
updated." The first was the Architecture diagram going stale a second
time (fixed separately, see specs/orchestration.md). The second was a
real, previously-undetected bug in `render_learning()`: its "Progress by
concept" bar chart and "Knowledge gaps" list were sourced entirely from
`LEARNING_DEMO` — fabricated Kubernetes/Docker demo data — completely
disconnected from the real 15 `GoalStore` capability goals shown
everywhere else on the dashboard. Only the goal *count* was real; the
actual per-goal progress breakdown the user wanted was never wired to
real data at all.

Rewrote `render_learning()` to build its progress chart directly from
`stores["goals"].list_by_owner()` (the same real data source the
Architecture page's "Goals defined" section already uses) — no caching,
so it reflects the actual state after every commit, not a fixed
snapshot. Added a per-goal "Deep dive — what's done, what's left"
section: an expander per capability showing its real progress %, the
`[Progress basis]` evidence note, and its real `success_criteria`
checklist (split from the basis note by its distinguishing prefix).
"Exercises completed" was dropped from the page entirely rather than
kept with a fabricated number — there is no real store backing an
exercises-completed count for these capability goals (confirmed by
checking: `evaluate_answer`/`AdaptiveLoop` are per-call functions with no
persistence), so showing one would be inventing data, not reporting it.

Verified live in a real browser (`agent-browser`): confirmed the real
56% average progress, the real 65% for "Agents & Multi-Agent
Orchestration" (matching its just-updated GoalStore value) with its real
progress-basis text, and the full success-criteria checklist rendering
correctly per goal. 755 tests passing (pure dashboard rendering fix, no
logic changed, no new tests needed).

## Example 11 — A full, real RAG page (chunking, embedding, semantic search, eval, failure modes)

The user asked for a dedicated RAG page: "real input data and output
data along with RAG evaluation parameters... map a graph with the
values, show how they are chunked, show an input and output on semantic
search... RAG failure modes, what to do when retrieval fails, or
generation fails... an entire RAG focused architecture diagram."

Scope decided explicitly with the user: chunking/embedding/search are
genuinely LIVE and interactive (free, local, no LLM call), while
generation + LLM-judge evaluation use pre-generated real examples (same
pattern as `tool_examples.json`) since those cost a real Gemini call and
this dashboard has a standing rule of never making live LLM calls on
page render. This meant reversing an earlier deliberate constraint:
`requirements-dashboard.txt` had excluded `sentence-transformers`/
`faiss-cpu`/heavy deps to keep the deploy light — the user explicitly
accepted the real deploy-weight increase for genuine interactivity, so
`sentence-transformers`, `faiss-cpu`, `rank-bm25`, and `pandas` were
added back.

- New `app/dashboard_ui/rag_diagram.py`: a RAG-specific Mermaid diagram
  (input -> chunk -> embed/BM25 -> hybrid fusion -> rerank -> context
  build -> generate -> cite -> evaluate), including a real, honestly
  disclosed failure-modes subgraph.
- New `scripts/generate_rag_examples.py`: runs the REAL full pipeline
  once (real chunking, real `SentenceTransformerEmbedding`, real FAISS +
  BM25 hybrid search, real `CrossEncoderReranker`, a real Gemini
  generation call via `PersonalRagPipeline`, real `evaluate_grounding()`
  and `citation_quality()`) against small synthetic fixture achievements
  (reused from `tests/fakes/example_resume.py`'s convention), plus a
  real, human-constructed retrieval ground truth for `evaluate_retrieval()`
  — writes `app/dashboard_ui/rag_examples.json`.
- New dashboard **RAG** page: (1) live chunking + embedding on
  user-pasted text, with a real numpy-SVD PCA projection of the real
  384-dim vectors to 2D (no sklearn dependency needed); (2) live vector
  vs BM25 vs hybrid-fusion semantic search on the same live-indexed
  chunks; (3) the pre-generated full-pipeline example across 4 tabs
  (Retrieval, Generation + Citations, Evaluation, Failure modes), each
  with a plain-English explanation of what its metric measures and why.

**A real, honest gap was caught while building this**, not glossed over:
`specs/personal_rag.md`'s own "Non-goals" section states hybrid search +
reranking are NOT actually wired into `PersonalRagPipeline` yet —
`SecureRetriever` currently wraps plain vector search only. The page's
Retrieval tab originally implied the reranked results fed the generation
step; fixed with an explicit warning box, and the RAG diagram itself now
draws BOTH the real hybrid+rerank chain (marked "NOT wired into
PersonalRagPipeline yet") and the actual production path (a distinct,
thick arrow: `SecureRetriever.search() == plain vector search only`) so
the gap is visible in the diagram itself, not just in prose.

Verified live end-to-end (twice — once before, once after the honesty
fix) in a real browser (`agent-browser`): the RAG diagram rendered
correctly; live-typed text produced real chunks, real embeddings, and a
real 2D scatter plot; a live query produced real, correctly-ranked
vector/BM25/hybrid results (the "networking" query correctly ranked the
networking-related chunk first); the pre-generated example's real
recall (1.00), precision (0.75 — genuinely imperfect, not cherry-picked:
one irrelevant chunk was really retrieved), groundedness (1.00), and
citation quality (1.00) all rendered correctly across all 4 tabs. 8 new
structural tests on the committed `rag_examples.json` (does not re-run
the generator in the test suite — that makes real paid LLM calls and
loads a real embedding model). 763 tests passing (was 755).

## Example 12 — Live retrieval evaluation (recall/precision) on your own labels

The user asked: "can we not build RAG evaluation (precision, recall,
etc.) on live chunking and semantic search?" Answered directly: the
only real blocker was that recall/precision need a human-labeled ground
truth (which chunks are ACTUALLY relevant to a query) — something no
one can infer, not an LLM-call cost or a technical limitation. Confirmed
with the user: solve it with real checkboxes, letting the user label
their own live query's ground truth on the spot.

Added a new "2b. Live retrieval evaluation" section directly under the
live vector/BM25/hybrid search results: every live chunk (not just the
retrieved ones — recall needs to know about relevant chunks that were
MISSED too, not just ones that were retrieved) gets a checkbox asking
"relevant to this query?", labeled with whether it was actually
retrieved. Once at least one chunk is checked, `evaluate_retrieval()`
(the same real function the pre-generated example uses) computes real
recall/precision live against the user's own real labels — no LLM call,
no fabrication.

Verified live in a real browser (`agent-browser`): checking one relevant
chunk (out of 3, all retrieved) correctly showed recall=100%,
precision=33%; checking a second correctly updated to recall=100%,
precision=67% — confirmed the math updates correctly in real time as
labels change. 763 tests passing (pure dashboard addition, no existing
logic changed).
