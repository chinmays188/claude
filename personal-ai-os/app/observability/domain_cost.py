from pydantic import BaseModel

from app.observability.costs import CostEntry, JourneyCost


class DomainCostEntry(BaseModel):
    """Section 42: 'Cost per domain.' Extends a plain CostEntry (Phase 1,
    Milestone 13) with which domain it belongs to, without modifying that
    schema — existing CostTracker/JourneyCost usage stays untouched."""

    entry: CostEntry
    domain: str  # "CAREER" | "PM" | "FINANCE" | "LEARNING" | "" for domain-agnostic


class DomainCostReport(BaseModel):
    domain_entries: list[DomainCostEntry]

    def by_domain(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for de in self.domain_entries:
            key = de.domain or "(none)"
            totals[key] = totals.get(key, 0.0) + de.entry.cost
        return totals

    @property
    def total(self) -> float:
        return sum(de.entry.cost for de in self.domain_entries)


def attribute_journey_cost_to_domains(journey: JourneyCost, component_domain_map: dict[str, str]) -> DomainCostReport:
    """Section 42: attributes each cost entry in an existing JourneyCost
    (Phase 1) to a domain, using a caller-supplied component->domain mapping
    (e.g. {'career_jd_analysis': 'CAREER', 'pm_prd': 'PM'}). Entries for a
    component not in the map are attributed to '' (domain-agnostic, e.g.
    shared infrastructure like the DomainRouter itself — Section 40's point
    that shared infra costs don't belong to any one domain)."""
    domain_entries = [
        DomainCostEntry(entry=entry, domain=component_domain_map.get(entry.component, ""))
        for entry in journey.entries
    ]
    return DomainCostReport(domain_entries=domain_entries)
