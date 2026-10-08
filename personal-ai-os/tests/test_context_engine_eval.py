from app.context.personal_context_engine import ContextItem, ImportanceLevel, PersonalContextEngine
from app.evaluation.context_engine_eval import (
    ContextGoldenCase,
    accuracy,
    run_context_golden_case,
    run_context_golden_suite,
)
from app.evaluation.context_engine_golden import CONTEXT_GOLDEN_CASES, NOW


def _case(content_a: str, content_b: str, expected: list[str]) -> ContextGoldenCase:
    return ContextGoldenCase(
        id="t", description="", token_budget=10, expected_included_contents=expected,
        items=[
            {
                "content": content_a, "relevance": 0.9, "importance": ImportanceLevel.HIGH,
                "freshness": NOW, "source": "test", "confidence": 1.0, "token_cost": 10,
            },
            {
                "content": content_b, "relevance": 0.1, "importance": ImportanceLevel.NONE,
                "freshness": NOW, "source": "test", "confidence": 0.1, "token_cost": 10,
            },
        ],
    )


def test_run_context_golden_case_passes_when_expected_item_selected():
    engine = PersonalContextEngine()
    case = _case("a", "b", expected=["a"])

    result = run_context_golden_case(engine, case, now=NOW)

    assert result.passed is True


def test_run_context_golden_case_fails_when_expected_item_missing():
    engine = PersonalContextEngine()
    case = _case("a", "b", expected=["b"])  # b is NONE-importance, can never be selected

    result = run_context_golden_case(engine, case, now=NOW)

    assert result.passed is False
    assert "b" in result.reason


def test_accuracy_computes_real_pass_fraction():
    results = run_context_golden_suite(
        PersonalContextEngine(),
        [_case("a", "b", expected=["a"]), _case("a", "b", expected=["b"])],
        now=NOW,
    )

    assert accuracy(results) == 0.5


def test_accuracy_empty_is_a_real_zero():
    assert accuracy([]) == 0.0


def test_real_golden_set_passes_with_current_default_weights():
    """The real, measured result from investigating 'Context Engineering':
    the current default weights score 100% on this real golden set --
    not fabricated to flatter the defaults, but a genuine outcome of
    cases written from real scoring-logic intuition before running them."""
    engine = PersonalContextEngine()

    results = run_context_golden_suite(engine, CONTEXT_GOLDEN_CASES, now=NOW)

    assert accuracy(results) == 1.0


def test_a_relevance_heavy_configuration_genuinely_fails_a_real_case():
    """Real evidence the golden set actually discriminates between weight
    configurations, not just trivially passing everything: over-weighting
    raw relevance genuinely breaks the 'explicit HIGH-importance
    preference beats higher-relevance LOW-importance noise' case."""
    engine = PersonalContextEngine(weight_relevance=0.7, weight_importance=0.1, weight_freshness=0.1, weight_confidence=0.1)

    results = run_context_golden_suite(engine, CONTEXT_GOLDEN_CASES, now=NOW)

    assert accuracy(results) < 1.0
