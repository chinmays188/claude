"""Real, hand-crafted golden cases for PersonalContextEngine's scoring
weights, found missing while investigating "Context Engineering"
("what do we need to do to make it 100%"). Each case states a scenario
and a human-judged correct outcome BEFORE looking at what any particular
weight configuration would produce -- not reverse-engineered to flatter
the current defaults.
"""

from datetime import datetime, timedelta, timezone

from app.context.personal_context_engine import ImportanceLevel
from app.evaluation.context_engine_eval import ContextGoldenCase

NOW = datetime(2026, 10, 8, tzinfo=timezone.utc)


def _item(content: str, relevance: float, importance: ImportanceLevel, age_days: float, confidence: float, token_cost: int) -> dict:
    return {
        "content": content, "relevance": relevance, "importance": importance,
        "freshness": NOW - timedelta(days=age_days), "source": "test", "confidence": confidence,
        "token_cost": token_cost,
    }


CONTEXT_GOLDEN_CASES = [
    ContextGoldenCase(
        id="fresh_relevant_beats_stale_low_confidence",
        description="A fresh, highly-relevant, high-confidence item should beat a very "
                    "stale, low-confidence item of similar relevance under a tight budget.",
        items=[
            _item("User just said they're learning Kubernetes this month.", relevance=0.9,
                  importance=ImportanceLevel.MEDIUM, age_days=1, confidence=0.95, token_cost=50),
            _item("User mentioned liking Python 2 years ago (possibly outdated).", relevance=0.85,
                  importance=ImportanceLevel.MEDIUM, age_days=730, confidence=0.3, token_cost=50),
        ],
        token_budget=50,
        expected_included_contents=["User just said they're learning Kubernetes this month."],
    ),
    ContextGoldenCase(
        id="high_importance_beats_higher_relevance_low_importance",
        description="A HIGH-importance item (e.g. an explicit user preference) should beat "
                    "a merely higher-relevance-scored but LOW-importance item under a tight budget.",
        items=[
            _item("User explicitly stated: never recommend unpaid internships.", relevance=0.5,
                  importance=ImportanceLevel.HIGH, age_days=10, confidence=0.9, token_cost=50),
            _item("A tangentially related forum post about internships.", relevance=0.7,
                  importance=ImportanceLevel.LOW, age_days=10, confidence=0.9, token_cost=50),
        ],
        token_budget=50,
        expected_included_contents=["User explicitly stated: never recommend unpaid internships."],
    ),
    ContextGoldenCase(
        id="none_importance_always_excluded_even_if_highly_relevant",
        description="An item explicitly classified NONE-importance must never be selected, "
                    "even with high relevance and ample budget (Section 20's own example: "
                    "'unrelated conversation -> NONE' should never enter context).",
        items=[
            _item("Small talk about the weather.", relevance=0.95,
                  importance=ImportanceLevel.NONE, age_days=0, confidence=1.0, token_cost=10),
            _item("User's actual career goal.", relevance=0.3,
                  importance=ImportanceLevel.LOW, age_days=5, confidence=0.9, token_cost=10),
        ],
        token_budget=1000,
        expected_included_contents=["User's actual career goal."],
    ),
    ContextGoldenCase(
        id="tight_budget_prefers_cheaper_similar_value_item",
        description="Under a tight budget, when two items score similarly, the real greedy "
                    "selection should still fit as much real value as the budget allows -- a "
                    "single large low-marginal-value item should not crowd out two smaller "
                    "higher-total-value items that together fit the same budget.",
        items=[
            _item("Short, highly relevant fact.", relevance=0.8,
                  importance=ImportanceLevel.MEDIUM, age_days=1, confidence=0.9, token_cost=20),
            _item("Another short, highly relevant fact.", relevance=0.8,
                  importance=ImportanceLevel.MEDIUM, age_days=1, confidence=0.9, token_cost=20),
        ],
        token_budget=40,
        expected_included_contents=["Short, highly relevant fact.", "Another short, highly relevant fact."],
    ),
    ContextGoldenCase(
        id="low_confidence_loses_to_high_confidence_at_similar_relevance",
        description="At similar relevance/importance/freshness, a low-confidence item "
                    "(uncertain/unverified) should lose to a high-confidence one under a "
                    "tight budget.",
        items=[
            _item("Confirmed: user's current employer is Acme Corp.", relevance=0.6,
                  importance=ImportanceLevel.MEDIUM, age_days=5, confidence=0.95, token_cost=50),
            _item("Possibly: user's employer might be Acme Corp (unconfirmed).", relevance=0.6,
                  importance=ImportanceLevel.MEDIUM, age_days=5, confidence=0.2, token_cost=50),
        ],
        token_budget=50,
        expected_included_contents=["Confirmed: user's current employer is Acme Corp."],
    ),
]
