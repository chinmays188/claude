"""Runs the real learning golden set (evals/learning/*.json) through the
real grading harness (learning_golden_runner.py), found missing while
investigating "AI Evaluation".

Usage:
    PYTHONPATH=. python scripts/generate_learning_eval_harness_run.py
"""

import json
from pathlib import Path

from app.config import require_gemini_key
from app.evaluation.domain_golden import load_domain_cases
from app.evaluation.learning_golden_runner import run_learning_golden_suite
from app.providers.gemini_provider import GeminiProvider

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "learning_eval_harness_run.json"


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()

    cases = load_domain_cases("learning")
    results = run_learning_golden_suite(llm, cases)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.case_id} ({r.category}) -- {r.reason}")

    pass_rate = sum(1 for r in results if r.passed) / len(results) if results else 0.0
    print(f"\nPass rate: {pass_rate:.0%} ({sum(1 for r in results if r.passed)}/{len(results)})")

    out = {"domain": "learning", "results": [r.model_dump() for r in results], "pass_rate": pass_rate}
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote real learning eval harness run to {OUT_PATH}")


if __name__ == "__main__":
    main()
