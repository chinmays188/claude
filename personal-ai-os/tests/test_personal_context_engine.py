from datetime import datetime, timedelta, timezone

from app.context.personal_context_engine import (
    ContextItem,
    ImportanceLevel,
    PersonalContextEngine,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _item(content, relevance=0.5, importance=ImportanceLevel.MEDIUM, freshness=NOW, confidence=0.8, token_cost=10):
    return ContextItem(
        content=content, relevance=relevance, importance=importance,
        freshness=freshness, source="test", confidence=confidence, token_cost=token_cost,
    )


def test_none_importance_items_are_always_excluded():
    engine = PersonalContextEngine()
    items = [
        _item("unrelated chit-chat", relevance=0.9, importance=ImportanceLevel.NONE),
        _item("relevant fact", relevance=0.5, importance=ImportanceLevel.MEDIUM),
    ]

    selected = engine.select(items, token_budget=1000, now=NOW)

    assert len(selected) == 1
    assert selected[0].content == "relevant fact"


def test_higher_scoring_items_selected_first_under_tight_budget():
    engine = PersonalContextEngine(weight_relevance=1.0, weight_importance=0, weight_freshness=0, weight_confidence=0)
    items = [
        _item("low relevance", relevance=0.1, token_cost=10),
        _item("high relevance", relevance=0.9, token_cost=10),
    ]

    selected = engine.select(items, token_budget=10, now=NOW)

    assert len(selected) == 1
    assert selected[0].content == "high relevance"


def test_more_recent_item_scores_higher_when_other_factors_equal():
    engine = PersonalContextEngine(weight_relevance=0, weight_importance=0, weight_freshness=1.0, weight_confidence=0)
    old_item = _item("old", freshness=NOW - timedelta(days=200))
    new_item = _item("new", freshness=NOW)

    assert engine.score(new_item, now=NOW) > engine.score(old_item, now=NOW)


def test_higher_importance_scores_higher_when_other_factors_equal():
    engine = PersonalContextEngine(weight_relevance=0, weight_importance=1.0, weight_freshness=0, weight_confidence=0)
    low = _item("low", importance=ImportanceLevel.LOW)
    high = _item("high", importance=ImportanceLevel.HIGH)

    assert engine.score(high, now=NOW) > engine.score(low, now=NOW)


def test_higher_confidence_scores_higher_when_other_factors_equal():
    engine = PersonalContextEngine(weight_relevance=0, weight_importance=0, weight_freshness=0, weight_confidence=1.0)
    low_conf = _item("low", confidence=0.1)
    high_conf = _item("high", confidence=0.9)

    assert engine.score(high_conf, now=NOW) > engine.score(low_conf, now=NOW)


def test_select_respects_token_budget():
    engine = PersonalContextEngine()
    items = [_item(f"item{i}", relevance=0.5, token_cost=100) for i in range(10)]

    selected = engine.select(items, token_budget=250, now=NOW)

    total_tokens = sum(i.token_cost for i in selected)
    assert total_tokens <= 250


def test_select_empty_items_returns_empty():
    engine = PersonalContextEngine()

    assert engine.select([], token_budget=1000, now=NOW) == []
