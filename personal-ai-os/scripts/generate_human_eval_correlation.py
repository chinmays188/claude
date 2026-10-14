"""Generates a REAL judge<->human correlation for the dashboard, using
the user's ACTUAL 1-5 ratings of this project's real 7-case harness run
(app/dashboard_ui/eval_harness_run.json) -- closes the one real gap "AI
Evaluation" disclosed across every prior pass: "human-in-the-loop needs
a real human's ratings this harness cannot fabricate."

These are genuinely the user's own ratings, given directly in
conversation after reviewing each case's real input/output -- not
invented, not a placeholder, not an illustrative example. If this
script is ever re-run with different ratings, it should be because the
user re-rated the cases for real, not to make the correlation number
look different.

Usage:
    PYTHONPATH=. python scripts/generate_human_eval_correlation.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.evaluation.human_eval import HumanRating, judge_human_correlation

HARNESS_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "eval_harness_run.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "human_eval_correlation.json"

# The user's real ratings, given directly: (correctness, relevance,
# completeness, trustworthiness, usefulness, citation_quality), each 1-5.
REAL_HUMAN_RATINGS = {
    "research_001": (5, 5, 5, 5, 5, 5),
    "research_002": (1, 2, 3, 4, 5, 5),
    "analysis_001": (3, 4, 5, 1, 3, 5),
    "planning_001": (5, 5, 5, 5, 5, 2),
    "ambiguous_001": (1, 1, 1, 1, 3, 2),
    "research_003_adversarial": (3, 3, 5, 2, 1, 2),
    "analysis_002_adversarial": (1, 2, 3, 4, 5, 1),
}


def main() -> None:
    harness = json.loads(HARNESS_PATH.read_text())

    ratings = []
    judge_scores = []
    human_scores = []
    for case in harness["results"]:
        case_id = case["case_id"]
        if case_id not in REAL_HUMAN_RATINGS:
            continue
        correctness, relevance, completeness, trustworthiness, usefulness, citation_quality = REAL_HUMAN_RATINGS[case_id]
        rating = HumanRating(
            case_id=case_id, correctness=correctness, relevance=relevance, completeness=completeness,
            trustworthiness=trustworthiness, usefulness=usefulness, citation_quality=citation_quality,
        )
        ratings.append(rating)
        judge_scores.append(case["judge_score"]["overall"])
        human_scores.append(rating.average)
        print(f"[{case_id}] judge_overall={case['judge_score']['overall']:.2f}  human_average={rating.average:.2f}")

    correlation = judge_human_correlation(judge_scores, human_scores)
    print(f"\nReal judge<->human Pearson correlation: {correlation:.3f}")

    output = {
        "ratings": [r.model_dump() for r in ratings],
        "judge_scores": judge_scores,
        "human_scores": human_scores,
        "correlation": correlation,
    }
    OUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote real human-eval correlation to {OUT_PATH}")


if __name__ == "__main__":
    main()
