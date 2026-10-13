"""Generates a REAL dataset-type classification + historical-failure
promotion demo for the dashboard, per the user's ask: "these are
datasets to be used in eval - golden dataset, synthetic dataset,
production data, historical failures, edge cases."

Part 1 (classification) needs no LLM call -- pure Python over real,
already-committed files, runnable live on the dashboard. Part 2
(promoting a real failure trace into a GoldenCase and RE-RUNNING it
against the real, live Orchestrator) needs a real Gemini call, so it's
pre-generated here and committed, consistent with this dashboard's
standing no-live-LLM-call rule.

Usage:
    PYTHONPATH=. python scripts/generate_dataset_registry_demo.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.orchestrator import Orchestrator
from app.config import require_gemini_key
from app.dashboard_ui.failure_traces import load_failure_trace_records
from app.evaluation.dataset_registry import trace_to_golden_case
from app.evaluation.golden import run_golden_case
from app.observability.traces import Trace
from app.providers.gemini_provider import GeminiProvider

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "dataset_registry_demo.json"


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()
    orchestrator = Orchestrator(llm)

    records = load_failure_trace_records()
    promotions = []
    for i, record in enumerate(records):
        trace = Trace.model_validate(record["trace_json"])
        case = trace_to_golden_case(trace, record["input_text"], case_id=f"promoted_historical_failure_{i}")
        result = run_golden_case(orchestrator, case)
        promotions.append({
            "case_id": case.id,
            "input": case.input,
            "promoted_expected_agent": case.expected_agent,
            "re_run_passed": result.passed,
            "re_run_reason": result.reason,
            "re_run_actual_agent": result.actual_agent,
        })
        print(f"[{case.id}] expected_agent={case.expected_agent!r} -> re-run passed={result.passed} ({result.reason})")

    OUT_PATH.write_text(json.dumps({"promotions": promotions}, indent=2))
    print(f"\nWrote real dataset registry demo to {OUT_PATH}")


if __name__ == "__main__":
    main()
