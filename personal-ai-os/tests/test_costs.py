import pytest

from app.observability.costs import CostRate, CostTracker, compute_cost


def test_compute_cost_basic():
    rate = CostRate(input_per_1k=0.01, output_per_1k=0.03)

    cost = compute_cost(input_tokens=1000, output_tokens=500, rate=rate)

    assert cost == pytest.approx(0.01 + 0.015)


def test_compute_cost_zero_tokens():
    rate = CostRate(input_per_1k=0.01, output_per_1k=0.03)

    assert compute_cost(0, 0, rate) == 0.0


def test_tracker_accumulates_journey_total():
    tracker = CostTracker("career_research", rates={"gemini-flash": CostRate(input_per_1k=0.01, output_per_1k=0.02)})

    tracker.record("orchestrator", "gemini-flash", input_tokens=500, output_tokens=100)
    tracker.record("research_agent", "gemini-flash", input_tokens=1000, output_tokens=800)

    assert tracker.journey.total == pytest.approx(0.005 + 0.002 + 0.01 + 0.016)


def test_tracker_breaks_down_by_component():
    tracker = CostTracker("j", rates={"m": CostRate(input_per_1k=0.01, output_per_1k=0.01)})
    tracker.record("orchestrator", "m", 1000, 0)
    tracker.record("evaluator", "m", 1000, 0)

    breakdown = tracker.journey.by_component()

    assert breakdown["orchestrator"] == pytest.approx(0.01)
    assert breakdown["evaluator"] == pytest.approx(0.01)


def test_tracker_breaks_down_by_model():
    tracker = CostTracker(
        "j", rates={"cheap": CostRate(input_per_1k=0.001, output_per_1k=0.001), "strong": CostRate(input_per_1k=0.01, output_per_1k=0.01)}
    )
    tracker.record("classifier", "cheap", 1000, 0)
    tracker.record("research_agent", "strong", 1000, 0)

    breakdown = tracker.journey.by_model()

    assert breakdown["cheap"] == pytest.approx(0.001)
    assert breakdown["strong"] == pytest.approx(0.01)


def test_unknown_model_costs_zero_rather_than_raising():
    tracker = CostTracker("j", rates={})

    tracker.record("component", "unknown-model", 1000, 1000)

    assert tracker.journey.total == 0.0


def test_zero_cost_component_included_in_breakdown_at_zero():
    tracker = CostTracker("j", rates={})

    tracker.record_zero_cost("local_calculator")

    assert tracker.journey.by_component()["local_calculator"] == 0.0
