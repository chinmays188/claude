import sqlite3

from app.dashboard_ui.user_learning_goals import LEARNING_CAPABILITIES, seed_learning_capability_goals
from app.domains.cross_domain.goal_store import GoalStore
from app.domains.router import Domain


def _store():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return GoalStore(conn)


def test_seeds_exactly_15_capabilities():
    assert len(LEARNING_CAPABILITIES) == 15


def test_seed_creates_all_goals_as_learning_domain():
    store = _store()

    goals = seed_learning_capability_goals(store)

    assert len(goals) == 15
    assert all(g.domain == Domain.LEARNING for g in goals)


def test_seed_is_idempotent():
    store = _store()

    seed_learning_capability_goals(store)
    seed_learning_capability_goals(store)  # re-seed

    all_goals = store.list_by_owner("demo_user")
    assert len(all_goals) == 15  # no duplicates


def test_every_goal_has_success_criteria():
    store = _store()

    goals = seed_learning_capability_goals(store)

    assert all(len(g.success_criteria) > 0 for g in goals)


def test_goals_use_priority_0_5_and_no_deadline_per_user_choice():
    """User's explicit choice for these two fields: priority=0.5, no
    deadline. Progress, unlike these two, is a real code-coverage-proxy
    assessment (see module docstring), not a fixed default -- verified
    separately below."""
    store = _store()

    goals = seed_learning_capability_goals(store)

    assert all(g.priority == 0.5 for g in goals)
    assert all(g.deadline is None for g in goals)


def test_progress_values_are_a_real_assessment_not_all_zero():
    """Progress was updated from the original all-zero default to a real,
    evidence-based code-coverage-proxy assessment per capability -- this
    guards against silently reverting to the meaningless all-zero state."""
    store = _store()

    goals = seed_learning_capability_goals(store)

    progresses = {g.progress for g in goals}
    assert len(progresses) > 1  # not all identical
    assert all(0.0 <= p <= 1.0 for p in progresses)
    assert max(progresses) > 0.5  # at least one capability is meaningfully progressed
    assert min(progresses) < 0.5  # at least one capability is honestly behind


def test_every_goal_has_a_progress_basis_recorded():
    """Every progress value must carry its evidence, not be a bare number --
    stored as the last success_criteria entry (see seed_learning_capability_goals)."""
    store = _store()

    goals = seed_learning_capability_goals(store)

    assert all(
        any(c.startswith("[Progress basis]") for c in g.success_criteria)
        for g in goals
    )
