import pytest

from app.context.experiments import ContextExperimentVariant, compare_variants


def _variant(name, accuracy, latency, tokens, cost=0.0, groundedness=0.9):
    return ContextExperimentVariant(
        name=name, accuracy=accuracy, groundedness=groundedness,
        latency_ms=latency, token_usage=tokens, cost=cost,
    )


def test_best_accuracy_variant():
    comparison = compare_variants(
        [_variant("A", accuracy=0.8, latency=100, tokens=500), _variant("B", accuracy=0.95, latency=200, tokens=800)]
    )

    assert comparison.best_accuracy.name == "B"


def test_fastest_variant():
    comparison = compare_variants(
        [_variant("A", accuracy=0.8, latency=500, tokens=500), _variant("B", accuracy=0.8, latency=100, tokens=500)]
    )

    assert comparison.fastest.name == "B"


def test_cheapest_variant():
    comparison = compare_variants(
        [_variant("A", accuracy=0.8, latency=100, tokens=500, cost=0.05), _variant("B", accuracy=0.8, latency=100, tokens=500, cost=0.01)]
    )

    assert comparison.cheapest.name == "B"


def test_ranked_by_arbitrary_metric():
    comparison = compare_variants(
        [_variant("A", accuracy=0.7, latency=100, tokens=500), _variant("B", accuracy=0.9, latency=100, tokens=500)]
    )

    ranked = comparison.ranked_by("accuracy")

    assert [v.name for v in ranked] == ["B", "A"]


def test_empty_variants_raises():
    with pytest.raises(ValueError):
        compare_variants([])
