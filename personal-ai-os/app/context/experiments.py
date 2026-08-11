from pydantic import BaseModel


class ContextExperimentVariant(BaseModel):
    """One configuration under test — e.g. a specific section ordering, a
    specific token budget, a specific compression strategy. Section 21 lists
    several experiment dimensions (ordering, compression, retrieval order,
    memory order, tool-result placement, lost-in-the-middle, token budget);
    this model is deliberately generic so the same comparison machinery works
    for any of them."""

    name: str
    accuracy: float  # fraction of golden cases answered correctly under this variant
    groundedness: float
    latency_ms: float
    token_usage: int
    cost: float = 0.0


class ExperimentComparison(BaseModel):
    variants: list[ContextExperimentVariant]

    @property
    def best_accuracy(self) -> ContextExperimentVariant:
        return max(self.variants, key=lambda v: v.accuracy)

    @property
    def cheapest(self) -> ContextExperimentVariant:
        return min(self.variants, key=lambda v: v.cost)

    @property
    def fastest(self) -> ContextExperimentVariant:
        return min(self.variants, key=lambda v: v.latency_ms)

    def ranked_by(self, metric: str, descending: bool = True) -> list[ContextExperimentVariant]:
        return sorted(self.variants, key=lambda v: getattr(v, metric), reverse=descending)


def compare_variants(variants: list[ContextExperimentVariant]) -> ExperimentComparison:
    if not variants:
        raise ValueError("Need at least one variant to compare.")
    return ExperimentComparison(variants=variants)
