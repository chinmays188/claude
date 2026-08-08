import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "agent_config.json"
STATE_PATH = ROOT / "data" / "runtime_state.json"
DB_PATH = ROOT / "data" / "job_agent.db"


class KillSwitchActive(Exception):
    pass


class DailyCeilingReached(Exception):
    pass


class BackoffActive(Exception):
    pass


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_runtime_state():
    if not STATE_PATH.exists():
        return {"backoff_until": None, "backoff_minutes": 0}
    with open(STATE_PATH) as f:
        return json.load(f)


def save_runtime_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def check_kill_switch():
    config = load_config()
    if config.get("kill_switch"):
        raise KillSwitchActive("kill_switch is set to true in agent_config.json — halting run")


def check_backoff():
    state = load_runtime_state()
    if state.get("backoff_until"):
        until = datetime.fromisoformat(state["backoff_until"])
        if datetime.now() < until:
            raise BackoffActive(f"in backoff until {until.isoformat()}")


def trigger_backoff():
    config = load_config()
    state = load_runtime_state()
    start = config["backoff"]["start_minutes"]
    cap = config["backoff"]["cap_minutes"]
    current = state.get("backoff_minutes", 0)
    next_minutes = min(current * 2, cap) if current else start
    state["backoff_minutes"] = next_minutes
    state["backoff_until"] = (datetime.now() + timedelta(minutes=next_minutes)).isoformat()
    save_runtime_state(state)
    return next_minutes


def clear_backoff():
    state = load_runtime_state()
    state["backoff_minutes"] = 0
    state["backoff_until"] = None
    save_runtime_state(state)


def calls_made_today():
    conn = sqlite3.connect(DB_PATH)
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT COALESCE(SUM(calls_made), 0) FROM run_log WHERE timestamp LIKE ?",
        (f"{today}%",),
    ).fetchone()
    conn.close()
    return row[0]


def check_daily_ceiling(additional_calls=0):
    config = load_config()
    ceiling = config["daily_mcp_call_ceiling"]
    made = calls_made_today()
    if made + additional_calls > ceiling:
        raise DailyCeilingReached(f"{made} calls made today, ceiling is {ceiling}")
    return ceiling - made


def log_run(calls_made, errors=None, backoff_state=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO run_log (timestamp, calls_made, errors, backoff_state) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), calls_made, errors, backoff_state),
    )
    conn.commit()
    conn.close()


def preflight():
    """Call at the top of every scheduled run. Raises if the run should not proceed."""
    check_kill_switch()
    check_backoff()
    remaining = check_daily_ceiling()
    if remaining <= 0:
        raise DailyCeilingReached("0 calls remaining today")
    return remaining


STAGES = ["discovery", "scoring", "tailoring", "contacts", "outreach_digest"]


def new_run_id():
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def start_stage(run_id, stage):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO stage_runs (run_id, stage, status, started_at) VALUES (?, ?, 'running', ?)",
        (run_id, stage, datetime.now().isoformat()),
    )
    conn.commit()
    stage_run_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return stage_run_id


def finish_stage(stage_run_id, status, result_summary=None, error=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE stage_runs SET status = ?, finished_at = ?, result_summary = ?, error = ? WHERE id = ?",
        (status, datetime.now().isoformat(), result_summary, error, stage_run_id),
    )
    conn.commit()
    conn.close()


def last_run_stage_status(run_id):
    """{stage: status} for a given run_id, to support resuming from the last incomplete stage."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT stage, status FROM stage_runs WHERE run_id = ? ORDER BY id", (run_id,)
    ).fetchall()
    conn.close()
    return dict(rows)


def most_recent_run_id():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT run_id FROM stage_runs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row[0] if row else None
