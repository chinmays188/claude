from pydantic import BaseModel

from app.domains.cross_domain.advisor import CrossDomainRecommendation, DomainPerspective
from app.domains.router import Domain


class CrossDomainCheckResult(BaseModel):
    name: str
    passed: bool
    reason: str


def check_correct_domain_selection(actual_domains: list[Domain], expected_domains: set[Domain]) -> CrossDomainCheckResult:
    """Section 37: 'Correct domain selection.' Verifies the router identified
    exactly the domains a labeled cross-domain case expects — neither missing
    a relevant domain nor including an irrelevant one."""
    actual_set = set(actual_domains)
    if actual_set != expected_domains:
        return CrossDomainCheckResult(
            name="correct_domain_selection", passed=False,
            reason=f"Expected domains {sorted(d.value for d in expected_domains)}, got {sorted(d.value for d in actual_set)}.",
        )
    return CrossDomainCheckResult(name="correct_domain_selection", passed=True, reason="Domains match expected set.")


def check_all_expected_perspectives_present(
    perspectives: list[DomainPerspective], expected_domains: set[str]
) -> CrossDomainCheckResult:
    """Section 37: 'Correct context retrieval.' A cross-domain recommendation
    must actually have gathered a perspective from every domain the question
    touches, not silently skip one."""
    present = {p.domain for p in perspectives}
    missing = expected_domains - present
    if missing:
        return CrossDomainCheckResult(
            name="all_expected_perspectives_present", passed=False,
            reason=f"Missing perspective(s) from domain(s): {sorted(missing)}",
        )
    return CrossDomainCheckResult(name="all_expected_perspectives_present", passed=True, reason="All expected perspectives present.")


def check_reasoning_references_perspectives(
    recommendation: CrossDomainRecommendation, perspectives: list[DomainPerspective]
) -> CrossDomainCheckResult:
    """Section 37: 'Reasoning consistency.' A cheap, auditable proxy — the
    combined recommendation's reasoning should reference content from more
    than zero of the domain perspectives it was given, not read as if it
    ignored them entirely."""
    reasoning_lower = recommendation.reasoning.lower()
    referenced = sum(
        1 for p in perspectives
        if any(word in reasoning_lower for word in p.perspective.lower().split() if len(word) > 5)
    )
    if referenced == 0 and perspectives:
        return CrossDomainCheckResult(
            name="reasoning_references_perspectives", passed=False,
            reason="Reasoning does not appear to reference any of the given domain perspectives.",
        )
    return CrossDomainCheckResult(name="reasoning_references_perspectives", passed=True, reason="Reasoning references given perspectives.")
