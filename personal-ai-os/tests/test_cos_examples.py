import sqlite3

from app.dashboard_ui.cos_examples import (
    load_example_goal_runs,
    load_example_harness_suggestion,
    seed_cos_examples,
)
from app.proactive.goal_run import GoalRunStore
from app.proactive.harness_feedback import HarnessSuggestionStore


def test_load_example_goal_runs_returns_real_committed_runs():
    runs = load_example_goal_runs()
    assert len(runs) == 2


def test_load_example_harness_suggestion_returns_real_committed_suggestion():
    suggestion = load_example_harness_suggestion()
    assert suggestion is not None
    assert suggestion.has_suggestion is True
    assert suggestion.suggestion


def test_seed_cos_examples_populates_both_stores_without_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    goal_run_store = GoalRunStore(conn)
    suggestion_store = HarnessSuggestionStore(conn)

    n_runs, n_suggestions = seed_cos_examples(goal_run_store, suggestion_store)

    assert n_runs == 2
    assert n_suggestions == 1
    assert len(goal_run_store.list_by_owner("demo_user")) == 2
    assert len(suggestion_store.list_by_owner("demo_user")) == 1


def test_seed_cos_examples_is_idempotent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    goal_run_store = GoalRunStore(conn)
    suggestion_store = HarnessSuggestionStore(conn)

    seed_cos_examples(goal_run_store, suggestion_store)
    seed_cos_examples(goal_run_store, suggestion_store)

    assert len(goal_run_store.list_by_owner("demo_user")) == 2
    assert len(suggestion_store.list_by_owner("demo_user")) == 1


def test_example_goal_runs_include_one_achieved_and_one_not():
    """Real, unscripted example content -- must show both outcomes, not
    just a cherry-picked success, per this module's own docstring."""
    runs = load_example_goal_runs()
    achieved_flags = {r.achieved for r in runs}
    assert achieved_flags == {True, False}
