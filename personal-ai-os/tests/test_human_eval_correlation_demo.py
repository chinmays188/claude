import json
from pathlib import Path

from app.evaluation.human_eval import HumanRating, judge_human_correlation

DEMO_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "human_eval_correlation.json"


def test_committed_human_eval_correlation_file_exists_and_has_real_ratings():
    """Closes the one real gap this capability disclosed: human-in-the-
    loop eval needs a real human's ratings, which no harness can
    fabricate. This file holds the user's own real 1-5 ratings of this
    project's real harness cases, given directly in conversation."""
    assert DEMO_PATH.exists(), "Run scripts/generate_human_eval_correlation.py first."
    data = json.loads(DEMO_PATH.read_text())

    assert len(data["ratings"]) == 7  # all 7 real harness cases rated
    for rating in data["ratings"]:
        parsed = HumanRating.model_validate(rating)
        assert 1 <= parsed.correctness <= 5
        assert 1 <= parsed.citation_quality <= 5


def test_committed_correlation_value_is_reproducible_from_the_committed_scores():
    """The committed correlation must match what judge_human_correlation()
    actually computes from the committed judge/human score pairs -- not
    a stale or hand-edited number."""
    data = json.loads(DEMO_PATH.read_text())

    recomputed = judge_human_correlation(data["judge_scores"], data["human_scores"])

    assert abs(recomputed - data["correlation"]) < 1e-9
