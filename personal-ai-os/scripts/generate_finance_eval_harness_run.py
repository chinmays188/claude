"""Runs the real finance golden set (evals/finance/*.json) through the
real grading harness (finance_golden_runner.py), found missing while
investigating "AI Evaluation". A real, honest finding: finance_002
(scenario_analysis) needs no LLM call at all (Section 24's absolute
rule) -- only finance_001 (portfolio_analysis) makes a real, live
Gemini call.

Usage:
    PYTHONPATH=. python scripts/generate_finance_eval_harness_run.py
"""

import json
from datetime import date
from pathlib import Path

from app.config import require_gemini_key
from app.domains.finance.models import Holding, Portfolio
from app.evaluation.domain_golden import load_domain_cases
from app.evaluation.finance_golden_runner import run_finance_golden_suite
from app.providers.gemini_provider import GeminiProvider

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "finance_eval_harness_run.json"

FIXTURE_PORTFOLIO = Portfolio(
    owner_id="demo_user", as_of=date.today(),
    holdings=[Holding(asset="Index Fund A", asset_class="equity", quantity=100, cost_basis=8000, current_value=9500)],
)


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()

    cases = load_domain_cases("finance")
    results = run_finance_golden_suite(llm, cases, FIXTURE_PORTFOLIO)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.case_id} ({r.category}) -- {r.reason}")

    pass_rate = sum(1 for r in results if r.passed) / len(results) if results else 0.0
    print(f"\nPass rate: {pass_rate:.0%} ({sum(1 for r in results if r.passed)}/{len(results)})")

    out = {"domain": "finance", "results": [r.model_dump() for r in results], "pass_rate": pass_rate}
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote real finance eval harness run to {OUT_PATH}")


if __name__ == "__main__":
    main()
