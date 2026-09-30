import json
from pathlib import Path

RESULTS_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "eval_harness_run.json"


def _load():
    return json.loads(RESULTS_PATH.read_text())


def test_harness_run_covers_all_golden_cases():
    data = _load()
    golden_path = Path(__file__).resolve().parent.parent / "evals" / "golden" / "basic_routing.json"
    golden_cases = json.loads(golden_path.read_text())
    assert data["golden_case_count"] == len(golden_cases)
    assert len(data["results"]) == len(golden_cases)


def test_harness_run_has_real_shape_not_fabricated():
    data = _load()
    assert 0.0 <= data["deterministic_pass_rate"] <= 1.0
    assert 0.0 <= data["average_judge_overall"] <= 1.0
    for r in data["results"]:
        assert isinstance(r["input"], str) and r["input"]
        assert isinstance(r["agent_output"], str) and r["agent_output"]
        assert isinstance(r["deterministic"]["passed"], bool)
        judge = r["judge_score"]
        for dim in ("correctness", "completeness", "groundedness", "citation_quality", "instruction_following", "overall"):
            assert 0.0 <= judge[dim] <= 1.0


def test_harness_run_includes_domain_case_counts():
    data = _load()
    assert set(data["golden_case_counts_by_domain"].keys()) >= {"career", "pm", "finance", "learning"}
