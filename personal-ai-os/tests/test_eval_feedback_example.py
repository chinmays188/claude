import json
from pathlib import Path

EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "eval_feedback_example.json"


def _load():
    return json.loads(EXAMPLE_PATH.read_text())


def test_example_cites_a_real_low_scoring_case():
    data = _load()
    assert len(data["low_scoring_case_ids"]) >= 1
    assert "research_003_adversarial" in data["low_scoring_case_ids"]


def test_example_has_real_suggestion_shape():
    data = _load()
    suggestion = data["suggestion"]
    assert isinstance(suggestion["has_suggestion"], bool)
    if suggestion["has_suggestion"]:
        assert suggestion["suggestion"]
        assert suggestion["evidence_cited"]


def test_example_evidence_references_the_real_low_scoring_case():
    data = _load()
    suggestion = data["suggestion"]
    assert "research_003_adversarial" in suggestion["evidence_cited"]
