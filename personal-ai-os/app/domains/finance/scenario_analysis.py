from pydantic import BaseModel

from app.domains.finance.calculations import apply_scenario_shock, recovery_return_required
from app.domains.finance.models import ClaimKind, Portfolio, TaggedClaim


class ScenarioAnalysisResult(BaseModel):
    claims: list[TaggedClaim]


def analyze_scenario(portfolio: Portfolio, shock_pct: float, target_value: float | None = None) -> ScenarioAnalysisResult:
    """Section 24: 'What happens if my portfolio falls 20%?' Every number here
    comes from calculations.py's pure-Python arithmetic — no LLM call in this
    function at all. Section 24's rule is absolute for this workflow: an LLM
    should never compute or restate a scenario shock's numbers itself."""
    result = apply_scenario_shock(portfolio, shock_pct)

    claims = [
        TaggedClaim(text=f"Current portfolio value: {result.current_value:.2f}", kind=ClaimKind.FACT, value=result.current_value),
        TaggedClaim(
            text=f"Scenario shock applied: {result.shock_pct:.1%}", kind=ClaimKind.ASSUMPTION, value=result.shock_pct
        ),
        TaggedClaim(text=f"Projected value after shock: {result.new_value:.2f}", kind=ClaimKind.CALCULATION, value=result.new_value),
        TaggedClaim(text=f"Projected loss: {result.loss:.2f}", kind=ClaimKind.CALCULATION, value=result.loss),
    ]

    if target_value is not None:
        recovery = recovery_return_required(result.new_value, target_value)
        claims.append(
            TaggedClaim(
                text=f"Return required to reach {target_value:.2f}: {recovery:.1%}",
                kind=ClaimKind.CALCULATION, value=recovery,
            )
        )

    return ScenarioAnalysisResult(claims=claims)
