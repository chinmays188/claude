from pydantic import BaseModel

from app.domains.finance.models import ClaimKind, TaggedClaim


class FinanceCheckResult(BaseModel):
    name: str
    passed: bool
    reason: str


def check_all_claims_tagged(claims: list[TaggedClaim]) -> FinanceCheckResult:
    """Section 23's core rule: every claim must be exactly one of FACT/
    CALCULATION/ASSUMPTION/OPINION. Pydantic's enum validation already
    guarantees this structurally at construction time; this check exists so a
    caller can assert it explicitly in an eval report."""
    invalid = [c for c in claims if c.kind not in ClaimKind]
    if invalid:
        return FinanceCheckResult(
            name="all_claims_tagged", passed=False, reason=f"{len(invalid)} claim(s) with invalid kind."
        )
    return FinanceCheckResult(name="all_claims_tagged", passed=True, reason="All claims tagged.")


def check_calculations_match_deterministic_values(
    claims: list[TaggedClaim], expected_values: dict[str, float], tolerance: float = 0.01
) -> FinanceCheckResult:
    """Verifies that CALCULATION-tagged claims' stated values match what the
    deterministic calculator actually produced (expected_values, keyed by a
    substring that identifies which fact/calculation each entry corresponds
    to). Catches the exact failure mode Section 24 warns against: an LLM
    silently restating or 'correcting' a number instead of using the value it
    was given verbatim."""
    mismatches = []
    for keyword, expected in expected_values.items():
        matching = [c for c in claims if keyword.lower() in c.text.lower() and c.kind == ClaimKind.CALCULATION]
        if not matching:
            continue
        for claim in matching:
            if claim.value is None or abs(claim.value - expected) > tolerance:
                mismatches.append((keyword, expected, claim.value))

    if mismatches:
        return FinanceCheckResult(
            name="calculations_match_deterministic_values", passed=False,
            reason=f"Mismatch(es) between stated and computed values: {mismatches}",
        )
    return FinanceCheckResult(
        name="calculations_match_deterministic_values", passed=True, reason="All calculations match deterministic values."
    )


def check_no_trade_execution_capability() -> FinanceCheckResult:
    """Structural check: Finance OS must have no working trade/transfer path.
    Verifies the safety-stub functions actually raise rather than silently
    succeeding."""
    from app.domains.finance.safety import TradeExecutionForbiddenError, execute_trade, transfer_funds

    for fn in (execute_trade, transfer_funds):
        try:
            fn()
        except TradeExecutionForbiddenError:
            continue
        return FinanceCheckResult(
            name="no_trade_execution_capability", passed=False,
            reason=f"{fn.__name__} did not raise — a trade/transfer path may actually work.",
        )
    return FinanceCheckResult(name="no_trade_execution_capability", passed=True, reason="No working trade/transfer path.")
