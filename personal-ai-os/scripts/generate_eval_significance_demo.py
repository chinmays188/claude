"""Generates a REAL multi-run significance demo for the dashboard, after
the user shared a real eval-methodology excerpt: "Due to LLM
stochasticity, agent performance evals must measure uncertainty and
report confidence intervals with mean pass rates... the performance
delta CI must be statistically significant. An interval is inconclusive
if it contains 0."

This project's existing harness (scripts/generate_eval_harness_run.py)
ran the real golden dataset ONCE and reported a single pass rate --
exactly the gap the excerpt names. This script runs the SAME real
golden dataset (evals/golden/basic_routing.json, the same file every
other eval-harness script uses) N_RUNS times against the real, live
Orchestrator, to show real sampling variance and a real Wilson
confidence interval -- not simulated or hand-picked numbers.

It then demonstrates BOTH real outcomes a significance-gated comparison
can produce: (1) comparing the real multi-run result against ITSELF
(same code, re-sampled) -- should come back INCONCLUSIVE, proving two
honest runs of unchanged code don't falsely look like an improvement;
(2) comparing against a scripted, clearly-labeled SIMULATED regression
(a real decrease deliberately large enough to be statistically
significant) -- to show what a genuinely detected regression looks
like, since this project's real code has no actual regression to
demonstrate against live.

Usage:
    PYTHONPATH=. python scripts/generate_eval_significance_demo.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.genai.errors import ClientError

from app.agents.orchestrator import Orchestrator
from app.config import require_gemini_key
from app.evaluation.confidence import compare_pass_rates, wilson_interval
from app.evaluation.golden import GoldenCase, run_golden_case
from app.providers.gemini_provider import GeminiProvider

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "evals" / "golden" / "basic_routing.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "eval_significance_demo.json"

N_RUNS_PER_SAMPLE = 3  # kept small -- each run makes real LLM calls per case
# This project's free-tier Gemini quota is a real, hard 15 requests/minute
# (confirmed repeatedly this session) -- each real golden-case run costs
# ~2-3 real calls (routing + agent), so a short pause between CASES
# (not just between runs) is needed to avoid tripping it across this
# script's ~85-125 total real calls.
SLEEP_BETWEEN_CASES_SECONDS = 5.0


def _load_cases() -> list[GoldenCase]:
    raw = json.loads(GOLDEN_PATH.read_text())
    return [GoldenCase.model_validate(c) for c in raw]


def _run_set_multi_with_backoff(orchestrator: Orchestrator, cases: list[GoldenCase], n_runs: int) -> tuple[int, int]:
    """Same real counting as run_golden_set_multi(), with a real retry-
    with-backoff on the free tier's real 429 rate limit (found necessary
    live, not hypothetical -- this exact script hit it on first run) and
    a deliberate pause between cases to avoid tripping it again."""
    total_successes = 0
    total_n = 0
    for run_index in range(n_runs):
        for case in cases:
            for attempt in range(3):
                try:
                    result = run_golden_case(orchestrator, case)
                    break
                except ClientError as exc:
                    if "RESOURCE_EXHAUSTED" not in str(exc) or attempt == 2:
                        raise
                    print(f"  Real rate limit hit, waiting 30s before retry (attempt {attempt + 1})...")
                    time.sleep(30)
            total_successes += 1 if result.passed else 0
            total_n += 1
            time.sleep(SLEEP_BETWEEN_CASES_SECONDS)
        print(f"  Run {run_index + 1}/{n_runs} of this sample complete.")
    return total_successes, total_n


def main() -> None:
    require_gemini_key()
    cases = _load_cases()
    llm = GeminiProvider()
    orchestrator = Orchestrator(llm)

    print(f"Running the real {len(cases)}-case golden set {N_RUNS_PER_SAMPLE} times (sample A)...")
    successes_a, n_a = _run_set_multi_with_backoff(orchestrator, cases, n_runs=N_RUNS_PER_SAMPLE)
    ci_a = wilson_interval(successes_a, n_a)
    print(f"Sample A: {successes_a}/{n_a} passed. Wilson 95% CI: [{ci_a.lower:.3f}, {ci_a.upper:.3f}]")

    print(f"Running the real {len(cases)}-case golden set {N_RUNS_PER_SAMPLE} more times (sample B, SAME unchanged code)...")
    successes_b, n_b = _run_set_multi_with_backoff(orchestrator, cases, n_runs=N_RUNS_PER_SAMPLE)
    ci_b = wilson_interval(successes_b, n_b)
    print(f"Sample B: {successes_b}/{n_b} passed. Wilson 95% CI: [{ci_b.lower:.3f}, {ci_b.upper:.3f}]")

    self_comparison = compare_pass_rates(successes_a, n_a, successes_b, n_b)
    print(f"A vs. B (same code): verdict={self_comparison.verdict} (expected: INCONCLUSIVE)")

    # A real, clearly-labeled SIMULATED regression -- this project's real
    # code has no actual regression to run live against; a large,
    # deliberate drop demonstrates what a genuinely significant
    # regression verdict looks like, honestly disclosed as simulated.
    simulated_regressed_successes = max(0, successes_a - n_a // 2)
    regression_comparison = compare_pass_rates(successes_a, n_a, simulated_regressed_successes, n_a)
    print(
        f"A vs. simulated regression ({simulated_regressed_successes}/{n_a}): "
        f"verdict={regression_comparison.verdict} (expected: REGRESSION)"
    )

    output = {
        "n_cases": len(cases),
        "n_runs_per_sample": N_RUNS_PER_SAMPLE,
        "sample_a": {"successes": successes_a, "n": n_a, "ci_lower": ci_a.lower, "ci_upper": ci_a.upper, "point_estimate": ci_a.point_estimate},
        "sample_b": {"successes": successes_b, "n": n_b, "ci_lower": ci_b.lower, "ci_upper": ci_b.upper, "point_estimate": ci_b.point_estimate},
        "self_comparison": {
            "verdict": self_comparison.verdict,
            "delta_point_estimate": self_comparison.delta_point_estimate,
            "delta_lower": self_comparison.delta_lower,
            "delta_upper": self_comparison.delta_upper,
        },
        "simulated_regression": {
            "simulated_successes": simulated_regressed_successes,
            "simulated_n": n_a,
            "verdict": regression_comparison.verdict,
            "delta_point_estimate": regression_comparison.delta_point_estimate,
            "delta_lower": regression_comparison.delta_lower,
            "delta_upper": regression_comparison.delta_upper,
            "note": "The regressed sample is SIMULATED (artificially halved success count) -- "
                    "this project's real code has no actual regression to demonstrate against live.",
        },
    }
    OUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"\nWrote real eval significance demo to {OUT_PATH}")


if __name__ == "__main__":
    main()
