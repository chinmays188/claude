from enum import Enum

from app.providers.base import LLMProvider


class TaskComplexity(str, Enum):
    SIMPLE = "simple"  # classification, short lookups
    COMPLEX = "complex"  # research/analysis/planning generation
    EVALUATION = "evaluation"  # judging/scoring another response


class ModelRouter:
    """Routes a task to a model tier based on its complexity, per Section 37.
    Both tiers are Gemini models here (Section 8: the system must run on Gemini
    alone) — this demonstrates real routing logic without requiring a second
    provider/API key."""

    def __init__(self, providers: dict[TaskComplexity, LLMProvider]):
        missing = set(TaskComplexity) - set(providers)
        if missing:
            raise ValueError(f"Missing provider(s) for: {sorted(m.value for m in missing)}")
        self._providers = providers

    def route(self, complexity: TaskComplexity) -> LLMProvider:
        return self._providers[complexity]
