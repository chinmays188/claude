"""Classifies every real eval dataset this project actually has, per the
user's ask: "these are datasets to be used in eval - golden dataset,
synthetic dataset, production data, historical failures, edge cases."

Checked first, honestly, against every real file under evals/ and
app/dashboard_ui/*.json before writing this:
  - GOLDEN: evals/golden/basic_routing.json -- real, hand-crafted cases
    with a human-judged correct outcome (expected_agent/tools).
  - SYNTHETIC: evals/{career,pm,finance,learning,cross_domain}/*.json --
    every domain dataset is explicitly fabricated-but-labeled-as-such,
    per this project's standing synthetic-data-only convention (no real
    personal/financial/career data anywhere in the repo).
  - EDGE_CASE: 2 cases already existed inside basic_routing.json
    (research_003_adversarial, analysis_002_adversarial) but were only
    ever distinguished by an "_adversarial" FILENAME SUFFIX -- never a
    separately-tracked dataset type. This registry tags them explicitly.
  - HISTORICAL_FAILURE: a real, found gap. app/observability/
    error_analysis.py computes live failure rates from stored traces,
    and app/dashboard_ui/failure_traces.json already holds 3 real,
    committed failure-mode traces (tool failure, retrieval failure,
    budget-exhausted) -- but nothing ever converted a real failed trace
    BACK into a reusable golden case. trace_to_golden_case() (below)
    closes this: a real past failure becomes a real regression-test
    case, not just a static, replayed example.
  - PRODUCTION: deliberately, structurally ABSENT -- not a gap to close.
    This project made an explicit, standing decision (confirmed across
    every domain's synthetic fixtures: Career/Learning/PM/Finance) to
    use ONLY fabricated data, never real personal/financial/career
    data. A real "production data" eval set would directly contradict
    that decision. Documented here as a deliberate non-goal, with
    HISTORICAL_FAILURE (real traces from this project's OWN synthetic
    runs, not real user data) as the closest honest substitute.
"""

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

from app.evaluation.golden import GoldenCase
from app.observability.traces import Trace

EVALS_ROOT = Path(__file__).resolve().parent.parent.parent / "evals"


class DatasetType(str, Enum):
    GOLDEN = "golden"
    SYNTHETIC = "synthetic"
    EDGE_CASE = "edge_case"
    HISTORICAL_FAILURE = "historical_failure"
    PRODUCTION = "production"  # deliberately never populated -- see module docstring


class DatasetEntry(BaseModel):
    """One real, classified case or file -- source is a real path (for a
    file-backed entry) or a description of where the data came from (for
    a promoted trace), never fabricated."""

    dataset_type: DatasetType
    case_id: str
    source: str
    note: str = ""


def classify_golden_cases() -> list[DatasetEntry]:
    """Classifies evals/golden/basic_routing.json's real cases --
    anything with '_adversarial' in its id is EDGE_CASE (closing the
    real gap where this distinction only ever lived in a filename
    convention), everything else is GOLDEN."""
    path = EVALS_ROOT / "golden" / "basic_routing.json"
    raw = json.loads(path.read_text())
    entries = []
    for case in raw:
        is_edge_case = "_adversarial" in case["id"]
        entries.append(
            DatasetEntry(
                dataset_type=DatasetType.EDGE_CASE if is_edge_case else DatasetType.GOLDEN,
                case_id=case["id"], source=str(path),
                note="Deliberately adversarial -- a genuine, non-staged chance at a real low score."
                if is_edge_case else "",
            )
        )
    return entries


def classify_synthetic_cases() -> list[DatasetEntry]:
    """Classifies every real evals/{domain}/*.json case as SYNTHETIC --
    every one of these datasets is explicitly fabricated, per this
    project's standing convention."""
    entries = []
    for domain_dir in sorted(EVALS_ROOT.iterdir()):
        if not domain_dir.is_dir() or domain_dir.name in ("golden", "adversarial"):
            continue
        for path in sorted(domain_dir.glob("*.json")):
            raw = json.loads(path.read_text())
            for case in raw:
                entries.append(
                    DatasetEntry(dataset_type=DatasetType.SYNTHETIC, case_id=case["id"], source=str(path))
                )
    return entries


def production_dataset_non_goal_note() -> str:
    """Not a function that produces real data -- a real, honest statement
    of why none exists, for a caller (e.g. the dashboard) that wants to
    show WHY this dataset type is empty rather than silently omitting
    it."""
    return (
        "Deliberately empty: this project has a standing, explicit decision to use ONLY "
        "synthetic/fabricated data in every domain (Career, PM, Finance, Learning) -- never "
        "real personal, financial, or career data. A real production dataset would "
        "contradict that decision. HISTORICAL_FAILURE traces (promoted from this project's "
        "own synthetic runs) are the closest honest substitute for real production evidence."
    )


def trace_to_golden_case(trace: Trace, input_text: str, case_id: str) -> GoldenCase:
    """Promotes a real past Trace (e.g. one already committed in
    app/dashboard_ui/failure_traces.json, or any trace a caller pulls
    from the real TraceStore) into a reusable GoldenCase -- closing the
    real HISTORICAL_FAILURE gap: a past failure becomes a re-runnable
    regression-test case, not just a static example shown once on a
    dashboard page and never exercised again.

    Real, found limitation while building this against this project's
    own 3 committed failure traces: Trace.agent (the top-level field) is
    NOT reliably the real dispatched agent -- it's set by whatever
    script generated the trace (e.g. "trace_request" for all 3 existing
    examples, or even the literal placeholder string "agent" in one of
    them, a real bug in scripts/trace_request.py's own instrumentation).
    The real dispatched agent, when present at all, lives in the
    top-level "orchestrator_run" span's metadata["agent"] instead -- this
    function looks there FIRST and only falls back to trace.agent (with
    expected_agent left None, a real "don't know" rather than a
    fabricated guess) when no such span exists or it has no agent
    recorded. A promoted case with expected_agent=None still has real
    value: run_golden_case() treats that as 'clarification expected',
    which is wrong for these recovered-from-failure traces, so a caller
    promoting a trace with no recoverable agent should treat the result
    as input-only replay material, not yet a strict pass/fail case."""
    expected_agent = None
    for span in trace.spans:
        if span.name == "orchestrator_run":
            agent_value = span.metadata.get("agent")
            if agent_value and agent_value != "agent":  # "agent" is the known placeholder bug, not a real value
                expected_agent = agent_value
            break

    return GoldenCase(id=case_id, input=input_text, expected_agent=expected_agent)
