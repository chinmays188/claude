"""Generates a REAL HarnessSuggestion grounded in the real eval harness
run's results, per the user's follow-up ask: "there should be low scoring
runs as well on the eval dashboard and how the feedback got translated."

Depends on app/dashboard_ui/eval_harness_run.json already existing (run
scripts/generate_eval_harness_run.py first). This script does NOT
re-run the harness -- it reads that real, already-committed result and
makes exactly one real, additional LLM call
(app/proactive/harness_feedback.py's generate_harness_suggestion(),
now with the eval_harness_run evidence wired in) to show the real,
concrete translation from "a real low eval score" to "a real proposed
workflow change" -- never invented, never auto-applied.

Usage:
    PYTHONPATH=. python scripts/generate_eval_feedback_example.py
"""

import json
from pathlib import Path

from app.config import require_gemini_key
from app.proactive.harness_feedback import generate_harness_suggestion
from app.providers.gemini_provider import GeminiProvider

EVAL_RUN_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "eval_harness_run.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "eval_feedback_example.json"


def main() -> None:
    require_gemini_key()
    if not EVAL_RUN_PATH.exists():
        raise SystemExit(f"{EVAL_RUN_PATH} does not exist -- run scripts/generate_eval_harness_run.py first.")

    eval_run = json.loads(EVAL_RUN_PATH.read_text())
    low_scoring = [
        r for r in eval_run["results"]
        if not r["deterministic"]["passed"] or r["judge_score"]["overall"] < 0.7
    ]
    print(f"Real low-scoring case(s) found: {[r['case_id'] for r in low_scoring]}")

    llm = GeminiProvider()
    suggestion = generate_harness_suggestion(
        llm, owner_id="demo_user", traces=[], eval_history=[], goal_runs=[],
        eval_harness_run=eval_run,
    )

    print(f"has_suggestion={suggestion.has_suggestion}")
    print(f"suggestion: {suggestion.suggestion}")
    print(f"evidence_cited: {suggestion.evidence_cited}")

    out = {
        "low_scoring_case_ids": [r["case_id"] for r in low_scoring],
        "suggestion": json.loads(suggestion.model_dump_json()),
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote real eval-feedback example to {OUT_PATH}")


if __name__ == "__main__":
    main()
