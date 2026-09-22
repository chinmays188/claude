"""Real, live-generated example traces for the public dashboard's Traces
page, so it shows genuine content without exposing a live Gemini key on the
public Streamlit Cloud deployment (decided explicitly with the user).

Unlike app/dashboard_ui/demo_workflow_outputs.py's fabricated values, these
are NOT invented: each record in example_traces.json is the real, unedited
output of a real scripts/trace_request.py run -- both real routers
(DomainRouter AND the separate TaskClassifier+Orchestrator path), real
memory keyword-overlap lookup, real tool calls (calculator, retrieve),
real Gemini responses, real token counts and cost -- captured once locally
and committed as a fixed snapshot. Re-running the same inputs later against
the live API would very likely produce different exact wording (LLM
outputs aren't deterministic), but every number and structural shape here
is something that actually happened, not a guess.

Covers 5 real runs, chosen to show the range of real behavior, not just the
happy path:
  1. "Should I learn Kubernetes for my career?" -- DomainRouter says
     CAREER+LEARNING (cross-domain); the separate Orchestrator path
     independently routes to analyst_agent -- a concrete, real example of
     the two routers disagreeing/operating independently.
  2. "What is Kubernetes and how does it help with scaling?" (with
     --index-file) -- routes to research_agent, which makes a real
     'retrieve' tool call against a real small indexed document.
  3. A FINANCE question with real arithmetic -- routes through
     DomainRouter to FINANCE, and separately to analyst_agent via
     Orchestrator, which makes a real 'calculator' tool call.
  4. "Create a 30-day plan..." -- routes to planner_agent via Orchestrator.
  5. "What's the weather like today?" -- DomainRouter classifies this
     UNCLEAR (no domain fits); the separate Orchestrator path still routes
     it somewhere (to research_agent) -- again showing the two routers are
     independent, not layered.
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
