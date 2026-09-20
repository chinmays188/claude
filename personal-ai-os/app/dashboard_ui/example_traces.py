"""Real, live-generated example traces for the public dashboard's Traces
page, so it shows genuine content without exposing a live Gemini key on the
public Streamlit Cloud deployment (decided explicitly with the user).

Unlike app/dashboard_ui/demo_workflow_outputs.py's fabricated values, these
are NOT invented: each record in example_traces.json is the real, unedited
output of a real scripts/trace_request.py run (real DomainRouter call, real
ToolAgent decision loop, real Gemini responses, real token counts and cost)
captured once locally and committed as a fixed snapshot. Re-running the same
inputs later against the live API would very likely produce different exact
wording (LLM outputs aren't deterministic), but every number and structural
shape here is something that actually happened, not a guess.

Covers: CAREER+LEARNING (cross-domain), PM, FINANCE with a real calculator
tool call, CAREER+LEARNING again with a different question, and one UNCLEAR
routing (arithmetic/off-topic question below the confidence threshold) --
chosen specifically to show the range of real behaviors, not just the happy
path.
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
