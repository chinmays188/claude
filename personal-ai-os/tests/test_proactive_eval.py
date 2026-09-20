from app.evaluation.proactive_eval import (
    DecisionQualityCase,
    LabeledCase,
    compute_false_rates,
    decision_accuracy,
)
from app.proactive.decision_engine import ResponseType


def test_false_positive_rate_computed_correctly():
    cases = [
        LabeledCase(case_id="c1", signal_fired=True, should_have_fired=False),  # FP
        LabeledCase(case_id="c2", signal_fired=False, should_have_fired=False),  # TN
    ]

    report = compute_false_rates(cases)

    assert report.false_positive_rate == 0.5
    assert report.false_positive_count == 1


def test_false_negative_rate_computed_correctly():
    cases = [
        LabeledCase(case_id="c1", signal_fired=False, should_have_fired=True),  # FN
        LabeledCase(case_id="c2", signal_fired=True, should_have_fired=True),  # TP
    ]

    report = compute_false_rates(cases)

    assert report.false_negative_rate == 0.5
    assert report.false_negative_count == 1


def test_rates_are_reported_separately_not_blended():
    cases = [
        LabeledCase(case_id="c1", signal_fired=True, should_have_fired=False),  # FP
        LabeledCase(case_id="c2", signal_fired=False, should_have_fired=True),  # FN
        LabeledCase(case_id="c3", signal_fired=True, should_have_fired=True),  # TP
        LabeledCase(case_id="c4", signal_fired=False, should_have_fired=False),  # TN
    ]

    report = compute_false_rates(cases)

    assert report.false_positive_rate == 0.5  # 1 FP out of (1 FP + 1 TN)
    assert report.false_negative_rate == 0.5  # 1 FN out of (1 FN + 1 TP)


def test_empty_cases_returns_zero_rates():
    report = compute_false_rates([])

    assert report.false_positive_rate == 0.0
    assert report.false_negative_rate == 0.0


def test_decision_accuracy_computed_correctly():
    cases = [
        DecisionQualityCase(case_id="c1", actual_response_type=ResponseType.ESCALATE, expected_response_type=ResponseType.ESCALATE),
        DecisionQualityCase(case_id="c2", actual_response_type=ResponseType.NOTIFY_ONLY, expected_response_type=ResponseType.ESCALATE),
    ]

    assert decision_accuracy(cases) == 0.5


def test_decision_accuracy_empty_cases():
    assert decision_accuracy([]) == 0.0
