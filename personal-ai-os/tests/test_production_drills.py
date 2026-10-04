import json
from pathlib import Path

DRILLS_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "production_drills.json"


def _load():
    return json.loads(DRILLS_PATH.read_text())


def test_drills_file_has_all_4_drills():
    data = _load()
    assert set(data.keys()) == {
        "disaster_recovery", "release_versioning", "eval_gated_release", "queue_workflow_runtime",
    }


def test_disaster_recovery_drill_survived_real_corruption():
    dr = _load()["disaster_recovery"]
    assert dr["backup_integrity_ok"] is True
    assert dr["restored_integrity_ok"] is True
    assert dr["data_survived"] is True
    assert dr["goals_before_corruption"] == dr["goals_after_restore"]


def test_release_versioning_rollback_matches_real_v1():
    rv = _load()["release_versioning"]
    assert rv["v2_published"] is True
    assert rv["rollback_matches_real_v1"] is True
    assert rv["rollback_version"] == 1


def test_eval_gated_release_passed_and_blocked_correctly():
    gate = _load()["eval_gated_release"]
    assert gate["same_candidate_passed"] is True
    assert gate["regressed_candidate_blocked"] is True
    assert "regression" in gate["block_message"].lower()


def test_queue_workflow_runtime_job_genuinely_completed():
    qwr = _load()["queue_workflow_runtime"]
    assert qwr["job_status"] == "succeeded"
    assert qwr["final_state_is_completed"] is True
    assert qwr["result"]
