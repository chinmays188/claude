from pydantic import BaseModel

from app.proactive.decision_engine import ResponseType


class LabeledCase(BaseModel):
    """A labeled case for proactive-system evaluation: did a signal ACTUALLY
    warrant surfacing to the user, per ground truth (human-labeled, in a real
    eval set)."""

    case_id: str
    signal_fired: bool  # did the trigger/attention pipeline surface this?
    should_have_fired: bool  # ground truth: was it actually worth surfacing?


class FalseRateReport(BaseModel):
    false_positive_rate: float  # fired but shouldn't have (annoying the user)
    false_negative_rate: float  # should have fired but didn't (missed something important)
    true_positive_count: int
    true_negative_count: int
    false_positive_count: int
    false_negative_count: int


def compute_false_rates(cases: list[LabeledCase]) -> FalseRateReport:
    """Milestone 42: 'False positive/negative evaluation.' A proactive system
    has two distinct, differently-costly failure modes — false positives
    (annoying/distracting the user with noise) and false negatives (silently
    missing something that mattered) — reported as two separate numbers,
    never averaged into one blended 'accuracy' score that would hide which
    failure mode is actually happening."""
    if not cases:
        return FalseRateReport(
            false_positive_rate=0.0, false_negative_rate=0.0,
            true_positive_count=0, true_negative_count=0, false_positive_count=0, false_negative_count=0,
        )

    tp = sum(1 for c in cases if c.signal_fired and c.should_have_fired)
    tn = sum(1 for c in cases if not c.signal_fired and not c.should_have_fired)
    fp = sum(1 for c in cases if c.signal_fired and not c.should_have_fired)
    fn = sum(1 for c in cases if not c.signal_fired and c.should_have_fired)

    negatives = fp + tn
    positives = fn + tp

    return FalseRateReport(
        false_positive_rate=fp / negatives if negatives else 0.0,
        false_negative_rate=fn / positives if positives else 0.0,
        true_positive_count=tp, true_negative_count=tn,
        false_positive_count=fp, false_negative_count=fn,
    )


class DecisionQualityCase(BaseModel):
    """Was the DecisionEngine's chosen response_type appropriate, per a
    labeled expectation? Distinct from the trigger-level false-rate above —
    this evaluates the decision layer (Milestone 38), not the trigger layer."""

    case_id: str
    actual_response_type: ResponseType
    expected_response_type: ResponseType


def decision_accuracy(cases: list[DecisionQualityCase]) -> float:
    if not cases:
        return 0.0
    correct = sum(1 for c in cases if c.actual_response_type == c.expected_response_type)
    return correct / len(cases)
