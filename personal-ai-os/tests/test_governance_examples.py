import json
from pathlib import Path

EXAMPLES_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "governance_examples.json"


def _load():
    return json.loads(EXAMPLES_PATH.read_text())


def test_examples_file_has_all_3_scenarios():
    data = _load()
    assert set(data.keys()) == {"read_path", "act_path", "sandbox_timeout"}


def test_read_path_completed_without_approval():
    data = _load()
    read_path = data["read_path"]
    assert read_path["stop_reason"] == "task_completed"
    assert read_path["tool_calls"] == ["calculator"]
    assert "564" in read_path["output"]


def test_act_path_genuinely_blocked_then_executed_after_approval():
    data = _load()
    act_path = data["act_path"]
    assert act_path["stop_reason"] == "approval_pending"
    assert act_path["pending_action_id"]
    assert act_path["execution_result_after_approval"] == "564"


def test_sandbox_timeout_genuinely_violated():
    data = _load()
    timeout = data["sandbox_timeout"]
    assert timeout["violated"] is True
    assert "timeout" in timeout["error"].lower()
