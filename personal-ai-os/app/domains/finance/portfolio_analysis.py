from pydantic import BaseModel

from app.domains.finance.calculations import (
    asset_class_allocation,
    concentration_ratio,
    portfolio_total_cost_basis,
    portfolio_total_value,
    portfolio_unrealized_gain,
)
from app.domains.finance.models import ClaimKind, Portfolio, TaggedClaim
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

OBSERVATIONS_PROMPT = """You are analyzing a portfolio. All numeric FACTS and
CALCULATIONS below were computed deterministically in code — do not
recalculate or contradict them. Your job is ONLY to add ASSUMPTION or OPINION
claims: risk observations, goal-alignment judgment, concentration commentary.
NEVER compute a number yourself; if you reference a number, it must be one of
the FACTS/CALCULATIONS given below, verbatim.

Portfolio facts (already computed, do not recalculate):
{facts}

Respond with ONLY a JSON object:
{{"claims": [{{"text": "<observation or opinion, referencing a fact number verbatim if applicable>", "kind": "ASSUMPTION" | "OPINION"}}]}}
"""


class _ObservationClaim(BaseModel):
    text: str
    kind: ClaimKind


class _ObservationList(BaseModel):
    claims: list[_ObservationClaim]


class PortfolioAnalysisResult(BaseModel):
    """Section 23's exact output list, each claim explicitly tagged FACT/
    CALCULATION/ASSUMPTION/OPINION — never an untagged blob of prose."""

    claims: list[TaggedClaim]


def analyze_portfolio(llm: LLMProvider, portfolio: Portfolio) -> PortfolioAnalysisResult:
    """Section 23's pipeline. All numbers (total value, allocation,
    concentration, unrealized gain) are computed deterministically in
    calculations.py FIRST and tagged FACT/CALCULATION — the LLM is only asked
    to add risk/goal-alignment commentary (ASSUMPTION/OPINION), and is
    explicitly told not to recompute or contradict the given numbers."""
    total_value = portfolio_total_value(portfolio)
    cost_basis = portfolio_total_cost_basis(portfolio)
    gain = portfolio_unrealized_gain(portfolio)
    allocation = asset_class_allocation(portfolio)
    concentration = concentration_ratio(portfolio)

    claims: list[TaggedClaim] = [
        TaggedClaim(text=f"Total portfolio value: {total_value:.2f}", kind=ClaimKind.FACT, value=total_value),
        TaggedClaim(text=f"Total cost basis: {cost_basis:.2f}", kind=ClaimKind.FACT, value=cost_basis),
        TaggedClaim(text=f"Unrealized gain/loss: {gain:.2f}", kind=ClaimKind.CALCULATION, value=gain),
        TaggedClaim(
            text=f"Largest single holding is {concentration:.1%} of the portfolio",
            kind=ClaimKind.CALCULATION, value=concentration,
        ),
    ]
    for asset_class, fraction in allocation.items():
        claims.append(
            TaggedClaim(text=f"{asset_class} allocation: {fraction:.1%}", kind=ClaimKind.CALCULATION, value=fraction)
        )

    facts_text = "\n".join(f"- {c.text}" for c in claims)
    generator = RepairableGenerator(llm, _ObservationList)
    observations = generator.generate(OBSERVATIONS_PROMPT.format(facts=facts_text))

    for obs in observations.claims:
        claims.append(TaggedClaim(text=obs.text, kind=obs.kind, value=None))

    return PortfolioAnalysisResult(claims=claims)
