"""Real, live-generated example traces for the public dashboard's Traces
page, so it shows genuine content without exposing a live Gemini key on the
public Streamlit Cloud deployment (decided explicitly with the user).

Unlike app/dashboard_ui/demo_workflow_outputs.py's fabricated values, these
are NOT invented: each record in example_traces.json is the real, unedited
output of a real scripts/trace_request.py run -- the single UnifiedRouter
(domain + task-type, one router, not two), real memory keyword-overlap
lookup, real tool calls (calculator, retrieve), real Gemini responses, real
token counts and cost -- captured once locally and committed as a fixed
snapshot. Re-running the same inputs later against the live API would very
likely produce different exact wording (LLM outputs aren't deterministic),
but every number and structural shape here is something that actually
happened, not a guess.

HISTORY: these 5 examples were originally captured when this codebase had
TWO separate, disconnected routers (DomainRouter and TaskClassifier, never
combined). The user asked for one combined router instead; that's now
app/routing/unified_router.py's UnifiedRouter, used internally by
Orchestrator, which also now injects the classified domain into the
dispatched agent's prompt as context. These examples were regenerated
against that fix.

Covers 5 real runs, chosen to show the range of real behavior, not just the
happy path:
  1. "Should I learn Kubernetes for my career?" -- UnifiedRouter classifies
     CAREER + analysis, dispatching to analyst_agent with CAREER injected
     as context (visible in the agent's own framing of its answer).
  2. "What is Kubernetes and how does it help with scaling?" (with
     --index-file) -- classifies LEARNING + research, routes to
     research_agent, which makes a real 'retrieve' tool call against a
     real small indexed document.
  3. A FINANCE question with real arithmetic -- classifies FINANCE +
     research, routes to research_agent, which makes real 'calculator'
     tool calls (this run shows the agent looping on the same calculation
     6 times before hitting max_tool_calls_reached -- kept as an honest
     example of a real, imperfect run rather than cherry-picked).
  4. "Create a 30-day plan..." -- classifies CAREER + planning, routes to
     planner_agent.
  5. "What's the weather like today?" -- classifies GENERAL (no domain
     fits) + research, still routes to research_agent (which correctly
     says it has no live weather tool) -- GENERAL is a first-class,
     real outcome, not an error.
"""

import json
from pathlib import Path

from app.observability.trace_store import TraceStore
from app.observability.traces import Trace

_EXAMPLES_PATH = Path(__file__).resolve().parent / "example_traces.json"


def seed_example_traces(trace_store: TraceStore) -> int:
    """Loads example_traces.json and saves each as a real Trace via the
    given TraceStore. Idempotent: TraceStore.save() is INSERT OR REPLACE
    keyed by execution_id, so re-seeding never duplicates. Returns the
    number of example traces seeded."""
    raw = json.loads(_EXAMPLES_PATH.read_text())
    for example in raw:
        trace = Trace.model_validate(example["trace_json"])
        trace_store.save(trace, input_text=example["input_text"])
    return len(raw)
