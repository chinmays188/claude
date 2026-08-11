from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class ImportanceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


@dataclass
class ContextItem:
    """Section 20: every candidate piece of context is scored on all of these
    dimensions before the engine decides what actually enters the prompt —
    never just 'is this text relevant', which collapses multiple real decisions
    into one number."""

    content: str
    relevance: float  # 0.0-1.0, semantic/task relevance to the current request
    importance: ImportanceLevel
    freshness: datetime
    source: str  # "memory" | "document" | "tool_result" | "history" | ...
    confidence: float  # 0.0-1.0, how sure we are this information is correct
    token_cost: int


IMPORTANCE_WEIGHT = {
    ImportanceLevel.HIGH: 1.0,
    ImportanceLevel.MEDIUM: 0.6,
    ImportanceLevel.LOW: 0.3,
    ImportanceLevel.NONE: 0.0,
}


class PersonalContextEngine:
    """Section 19: decides what information enters the context window, given
    the current request, history, memory, retrieved documents, tool results,
    preferences, and current date/time. Produces a prioritized, budget-aware
    subset of ContextItems — never 'append everything it was given.'"""

    def __init__(
        self,
        weight_relevance: float = 0.4,
        weight_importance: float = 0.3,
        weight_freshness: float = 0.2,
        weight_confidence: float = 0.1,
        freshness_half_life_days: float = 30.0,
    ):
        self._w_relevance = weight_relevance
        self._w_importance = weight_importance
        self._w_freshness = weight_freshness
        self._w_confidence = weight_confidence
        self._half_life_days = freshness_half_life_days

    def score(self, item: ContextItem, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        freshness_score = self._freshness_score(item.freshness, now)
        return (
            self._w_relevance * item.relevance
            + self._w_importance * IMPORTANCE_WEIGHT[item.importance]
            + self._w_freshness * freshness_score
            + self._w_confidence * item.confidence
        )

    def select(
        self, items: list[ContextItem], token_budget: int, now: datetime | None = None
    ) -> list[ContextItem]:
        """Greedily selects highest-scoring items first until the token budget
        would be exceeded. NONE-importance items are always excluded outright,
        regardless of score (Section 20's example: 'Unrelated conversation ->
        NONE' should never enter context)."""
        eligible = [item for item in items if item.importance != ImportanceLevel.NONE]
        scored = [(self.score(item, now), item) for item in eligible]
        scored.sort(key=lambda pair: pair[0], reverse=True)

        selected = []
        used_tokens = 0
        for _, item in scored:
            if used_tokens + item.token_cost > token_budget:
                continue
            selected.append(item)
            used_tokens += item.token_cost

        return selected

    def _freshness_score(self, freshness: datetime, now: datetime) -> float:
        if freshness.tzinfo is None:
            freshness = freshness.replace(tzinfo=timezone.utc)
        age_days = max((now - freshness).total_seconds() / 86400, 0)
        return 0.5 ** (age_days / self._half_life_days)
