from app.proactive.attention import AttentionEngine
from app.proactive.triggers import Signal


def _signal(trigger_name="task_stuck", title="Stuck task") -> Signal:
    return Signal(owner_id="alice", trigger_name=trigger_name, title=title, description="d", source_event_id="e1")


def test_score_uses_trigger_base_weight():
    engine = AttentionEngine()

    scored = engine.score(_signal(trigger_name="goal_deadline_approaching"))

    assert scored.attention_score == 0.9


def test_score_unknown_trigger_uses_default_weight():
    engine = AttentionEngine()

    scored = engine.score(_signal(trigger_name="some_new_trigger"))

    assert scored.attention_score == 0.4


def test_is_duplicate_detects_same_trigger_and_title():
    engine = AttentionEngine()
    signal1 = _signal()
    signal2 = _signal()  # same trigger_name + title

    assert engine.is_duplicate(signal1) is False
    assert engine.is_duplicate(signal2) is True


def test_is_duplicate_treats_different_titles_as_distinct():
    engine = AttentionEngine()

    assert engine.is_duplicate(_signal(title="Task A stuck")) is False
    assert engine.is_duplicate(_signal(title="Task B stuck")) is False


def test_rank_sorts_highest_attention_first():
    engine = AttentionEngine()
    signals = [
        _signal(trigger_name="task_stuck", title="Task A"),
        _signal(trigger_name="goal_deadline_approaching", title="Goal B"),
        _signal(trigger_name="urgent_email", title="Email C"),
    ]

    ranked = engine.rank(signals)

    assert ranked[0].signal.trigger_name == "goal_deadline_approaching"
    assert ranked[-1].signal.trigger_name == "task_stuck"


def test_rank_filters_below_min_score():
    engine = AttentionEngine()
    signals = [_signal(trigger_name="task_stuck", title="Task A"), _signal(trigger_name="goal_deadline_approaching", title="Goal B")]

    ranked = engine.rank(signals, min_score=0.7)

    assert len(ranked) == 1
    assert ranked[0].signal.trigger_name == "goal_deadline_approaching"


def test_rank_deduplicates_across_calls():
    engine = AttentionEngine()
    signal = _signal(title="Repeated issue")

    first_rank = engine.rank([signal])
    second_rank = engine.rank([signal])  # same signal content again

    assert len(first_rank) == 1
    assert len(second_rank) == 0
