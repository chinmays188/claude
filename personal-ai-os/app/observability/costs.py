from pydantic import BaseModel, Field


class CostRate(BaseModel):
    """Cost per 1K tokens, in a caller-defined currency unit (Section 50: exact
    currency/cost calculation is configurable, not hardcoded)."""

    input_per_1k: float
    output_per_1k: float


class CostEntry(BaseModel):
    component: str  # e.g. "orchestrator", "research_agent", "web_search", "evaluator"
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0


class JourneyCost(BaseModel):
    journey: str
    entries: list[CostEntry] = Field(default_factory=list)

    @property
    def total(self) -> float:
        return sum(e.cost for e in self.entries)

    def by_component(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for entry in self.entries:
            totals[entry.component] = totals.get(entry.component, 0.0) + entry.cost
        return totals

    def by_model(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for entry in self.entries:
            if not entry.model:
                continue
            totals[entry.model] = totals.get(entry.model, 0.0) + entry.cost
        return totals


def compute_cost(input_tokens: int, output_tokens: int, rate: CostRate) -> float:
    return (input_tokens / 1000) * rate.input_per_1k + (output_tokens / 1000) * rate.output_per_1k


class CostTracker:
    """Accumulates cost entries for a single user journey, so cost can be
    attributed by component (agent/tool/skill) and by model, not just a single
    total (Section 49-50)."""

    def __init__(self, journey: str, rates: dict[str, CostRate]):
        self._journey = JourneyCost(journey=journey)
        self._rates = rates

    def record(self, component: str, model: str, input_tokens: int, output_tokens: int) -> None:
        rate = self._rates.get(model)
        cost = compute_cost(input_tokens, output_tokens, rate) if rate else 0.0
        self._journey.entries.append(
            CostEntry(
                component=component, model=model,
                input_tokens=input_tokens, output_tokens=output_tokens, cost=cost,
            )
        )

    def record_zero_cost(self, component: str) -> None:
        """For free components (local tools, local retrieval, local embeddings)
        that still deserve a line item so the journey breakdown is complete."""
        self._journey.entries.append(CostEntry(component=component))

    @property
    def journey(self) -> JourneyCost:
        return self._journey
