# Orchestrator / Multi-Agent Routing

## Example 1 — Research

Input:
"Explain RAG."

Expected:
- Classifier returns `task_type=research`
- `ResearchAgent` handles the request
- `AgentResponse.agent == "research_agent"`

## Example 2 — Analysis

Input:
"Compare RAG, fine-tuning and long-context prompting."

Expected:
- Classifier returns `task_type=analysis`
- `AnalystAgent` handles the request
- `AgentResponse.agent == "analyst_agent"`

## Example 3 — Planning

Input:
"Create a 30-day plan for learning Docker."

Expected:
- Classifier returns `task_type=planning`
- `PlannerAgent` handles the request
- `AgentResponse.agent == "planner_agent"`

## Example 4 — Ambiguous input

Input:
"Do something useful."

Expected:
- Classifier returns `task_type=unclear` (or confidence below threshold)
- Orchestrator does NOT guess an agent
- Returns a `ClarificationNeeded` response asking the user what they meant
- No agent is invoked, no LLM call beyond classification

## Edge case — Empty input

Input:
""

Expected:
- Orchestrator raises a validation error before calling the classifier

## Failure case — Malformed classifier output

Condition:
Classifier LLM call returns text that isn't valid JSON, or JSON missing required fields.

Expected:
- `ClassificationError` raised
- Orchestrator does not silently default to an agent
- (Repair loop for this is deferred to Milestone 4 — Structured Output)

## Failure case — Low-confidence classification

Condition:
Classifier returns a valid `task_type` but `confidence` below the configured threshold (default 0.5).

Expected:
- Treated as `unclear` regardless of the raw `task_type`
- Orchestrator returns `ClarificationNeeded`

## Example — Multi-agent orchestration for inputs that need more than one agent

The user's ask: "we need to think of multi agent orchestration between
research agent, analyst, planner agent as some inputs will require all 3,"
and explicitly: "pattern will not be sequential, will depend on the
input" -- ruling out a fixed pipeline.

New `app/agents/multi_agent_coordinator.py`:
- `MultiAgentPlanner`: one real LLM call that decides, per input, whether
  more than one agent is genuinely needed and whether they should run
  SEQUENTIAL (each agent's real output feeds the next, prepended as
  context ahead of the original request) or PARALLEL (independent runs,
  then synthesized into one answer by a final LLM call). SINGLE (the
  common case) skips coordination entirely.
- `MultiAgentCoordinator`: actually runs the plan against the SAME agent
  instances `Orchestrator` already built (so tool wiring/domain context
  stay identical to the single-agent path) -- never builds its own agents.
- `might_need_multiple_agents()`: a free, no-LLM-call heuristic gate run
  BEFORE the real planning call. Confirmed with the user: paying for an
  extra LLM call on every single request (including obviously-simple
  ones) was an unacceptable cost increase, so only requests with a
  sequencing keyword (" then ", " and also ", etc.) or at or above 18
  words even trigger the real planning call. A false positive here just
  costs one wasted call that itself says SINGLE; a false negative
  silently skips real coordination -- the heuristic is deliberately tuned
  to cast a slightly wide net rather than a narrow one.
- `Orchestrator.handle()` runs the heuristic gate first; only when it's
  true does it make the real `MultiAgentPlanner` call, and only when that
  plan says coordination is needed does it delegate to
  `MultiAgentCoordinator` instead of the normal single-agent dispatch. A
  `MultiAgentPlanningError` (malformed LLM output exhausting repair
  attempts) degrades to the normal single-agent path rather than
  crashing -- consistent with how a `UnifiedRoutingError` degrades to
  `ClarificationNeeded`.
- A multi-agent result is still a real `AgentResponse` (agent name like
  `"multi_agent:sequential:research_agent+analyst_agent+planner_agent"`),
  so every existing caller (`app/main.py`, `voice_api.py`,
  `trace_request.py`, the dashboard) needed zero code changes to handle
  it.

A real bug was found and fixed while verifying this live: `GeminiProvider`
never set an HTTP request timeout (the SDK's default is `None`), so a
single `generate()` call could hang indefinitely if the API was slow to
respond (e.g. under this project's known free-tier rate limit) -- and
`AgentBudget.timeout_seconds` can't help, since that check only runs
BETWEEN calls, never during one already in flight. Fixed by passing a real
`HttpOptions(timeout=45000)` (45s) to the client. Verified: a call made
after killing a hung process now correctly raises `httpx.ReadTimeout`
after ~45s instead of hanging indefinitely -- confirmed via a raw `curl`
directly against the Gemini endpoint (bypassing all of this project's own
code) that the timeout was hit because the API itself was genuinely slow
to respond at that moment (very likely this session's own heavy testing
against a free-tier key), not because of a bug in the request.

Verified via 18 `Orchestrator` tests (including 4 new ones specifically
for the multi-agent path: heuristic-not-triggered skips the planner call
entirely, a long multi-clause request triggers the sequential path and
produces the final agent's real output, a malformed planner response
degrades gracefully, and the `on_multi_agent_planned` observer receives
the real plan), 8 `MultiAgentCoordinator`/`MultiAgentPlanner` tests, and 5
heuristic-gate tests.

Live verification status (honestly disclosed, not glossed over): while
diagnosing the timeout hang above, `gemini-3.5-flash-lite` itself became
persistently unresponsive on this project's key -- confirmed via a raw
`curl` directly against the Gemini endpoint (bypassing all of this
project's code) that the *server* was accepting the connection but
sending zero bytes back, ruling out a local/network cause. Switching
temporarily to `gemini-3.8-flash` (same key) to unblock verification:
- **`MultiAgentPlanner` itself verified live and correct**: given the
  exact 3-clause Kubernetes-vs-ECS-vs-adoption-plan request above, it
  correctly identified all 3 agents were needed and correctly chose
  SEQUENTIAL mode, with real, accurate reasoning
  ("...first explain Kubernetes (research), then compare it against ECS
  to pick a winner (analysis), and finally create an adoption roadmap
  based on the winning recommendation (planning)").
- **Full end-to-end completion (through `MultiAgentCoordinator`'s
  sequential agent chain to a final combined output) was NOT completed
  live** -- every attempt (both the sequential 3-agent case and a
  separate parallel 2-agent case) hit a real `google.genai.errors.
  ServerError: 503 UNAVAILABLE, "This model is currently experiencing
  high demand"` partway through the chain, while simple single-turn
  calls on the same model continued to succeed reliably throughout. This
  is consistent with a genuine, sustained Gemini-side capacity
  constraint under longer/multi-turn agentic load, not a bug in this
  code -- but it means the coordinator's actual multi-agent execution
  (as opposed to the planning decision) has only been verified via
  scripted tests so far, not a real live run to completion. Flagged
  explicitly as a pending follow-up, to be completed opportunistically
  once Gemini's capacity issue clears, per an explicit decision with the
  user to ship on this evidence rather than block further.
