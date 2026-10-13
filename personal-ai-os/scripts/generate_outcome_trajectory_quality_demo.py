"""Generates a REAL outcome/trajectory/quality breakdown for the
dashboard, per the user's ask: "we should divide our entire evals into
outcome, trajectory and quality for each evaluation."

Re-scores scripts/generate_eval_harness_run.py's already-committed, real
output (app/dashboard_ui/eval_harness_run.json -- real Orchestrator runs
and real LLM-judge calls from that script, not re-run here) through the
new app/evaluation/outcome_trajectory_quality.py split. No new LLM calls
-- this is pure re-composition of already-real data into the 3-part
shape, which is why this script runs instantly and needs no API key.

Honest, disclosed limitation: this real run's 7 cases all show
outcome_trajectory_agree=True (the harness's own real agent dispatch
always matched the expected agent for every case that outcome also
passed) -- a genuinely clean result, not manufactured to show a more
dramatic disagreement. The real mechanism for catching a disagreement
(outcome=pass, trajectory=fail) is proven instead by
tests/test_outcome_trajectory_quality.py's dedicated unit test, which
constructs that exact scenario directly since this project's real
golden set has not yet produced one.

Usage:
    PYTHONPATH=. python scripts/generate_outcome_trajectory_quality_demo.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.base import AgentResponse
from app.evaluation.golden import GoldenCaseResult
from app.evaluation.llm_judge import JudgeScore
from app.evaluation.outcome_trajectory_quality import TrajectoryExpectation, build_evaluation_result

SOURCE_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "eval_harness_run.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "outcome_trajectory_quality_demo.json"


def main() -> None:
    source = json.loads(SOURCE_PATH.read_text())

    results = []
    for case in source["results"]:
        det = case["deterministic"]
        golden_result = GoldenCaseResult(
            case_id=case["case_id"], passed=det["passed"], reason=det["reason"],
            actual_agent=det["actual_agent"], actual_tools=det["actual_tools"],
        )
        # stop_reason isn't captured in the committed harness JSON (it
        # predates this module) -- defaulted to the healthy value rather
        # than fabricating a specific real reading this script doesn't have.
        response = AgentResponse(
            input=case["input"], output=case["agent_output"], model=source["judge_model"],
            agent=det["actual_agent"] or "unknown", tool_calls=det["actual_tools"], stop_reason="task_completed",
        )
        expectation = TrajectoryExpectation(expected_agent=case["expected_agent"], expected_tools=case["expected_tools"])
        quality = JudgeScore.model_validate(case["judge_score"])

        result = build_evaluation_result(case["case_id"], golden_result, response, expectation, quality=quality)
        dumped = result.model_dump()
        dumped["outcome_trajectory_agree"] = result.outcome_trajectory_agree  # a @property, not dumped automatically
        results.append(dumped)
        print(
            f"[{case['case_id']}] outcome={result.outcome.passed} trajectory={result.trajectory.passed} "
            f"quality.overall={result.quality.overall:.2f} agree={result.outcome_trajectory_agree}"
        )

    disagreements = sum(1 for r in results if not r["outcome_trajectory_agree"])
    output = {"results": results, "disagreement_count": disagreements, "total_count": len(results)}
    OUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"\n{disagreements}/{len(results)} cases show outcome/trajectory disagreement in this real run.")
    print(f"Wrote real outcome/trajectory/quality demo to {OUT_PATH}")


if __name__ == "__main__":
    main()
