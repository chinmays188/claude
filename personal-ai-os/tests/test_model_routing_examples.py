import json
from pathlib import Path

EXAMPLES_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "model_routing_examples.json"


def _load():
    return json.loads(EXAMPLES_PATH.read_text())


def test_examples_file_exists_and_has_all_three_scenarios():
    data = _load()
    assert len(data["examples"]) == 3
    complexities = {e["predicted_complexity"] for e in data["examples"]}
    assert complexities == {"simple", "complex"}


def test_examples_have_real_shape_not_fabricated():
    data = _load()
    for e in data["examples"]:
        assert isinstance(e["answer"], str) and e["answer"]
        assert isinstance(e["routed_model"], str) and e["routed_model"]
        assert isinstance(e["degraded"], bool)
        assert isinstance(e["simulated"], bool)


def test_at_least_one_example_is_not_simulated():
    """The simple-request example and the first complex-request example
    are always real, live calls -- only the third example intentionally
    simulates a failure (see scripts/generate_model_routing_examples.py's
    docstring for why)."""
    data = _load()
    real_examples = [e for e in data["examples"] if not e["simulated"]]
    assert len(real_examples) == 2


def test_simple_example_is_never_degraded():
    data = _load()
    simple = next(e for e in data["examples"] if e["predicted_complexity"] == "simple")
    assert simple["degraded"] is False
