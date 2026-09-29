import json
from pathlib import Path

RESULTS_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "lost_in_middle_results.json"


def _load():
    return json.loads(RESULTS_PATH.read_text())


def test_results_file_exists_and_has_all_three_positions():
    data = _load()
    positions = {r["position"] for r in data["results"]}
    assert positions == {"start", "middle", "end"}


def test_results_are_real_not_fabricated_shape():
    data = _load()
    assert data["filler_chunk_count"] > 0
    for r in data["results"]:
        assert isinstance(r["answer"], str) and r["answer"]
        assert isinstance(r["correct"], bool)
        assert r["context_char_length"] > 0
