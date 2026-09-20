from app.observability.costs import CostEntry, JourneyCost
from app.observability.domain_cost import attribute_journey_cost_to_domains


def test_attributes_entries_to_mapped_domains():
    journey = JourneyCost(
        journey="career_jd_analysis",
        entries=[
            CostEntry(component="career_jd_analysis", model="gemini-flash", cost=0.01),
            CostEntry(component="domain_router", model="gemini-flash-lite", cost=0.001),
        ],
    )

    report = attribute_journey_cost_to_domains(journey, component_domain_map={"career_jd_analysis": "CAREER"})

    totals = report.by_domain()
    assert totals["CAREER"] == 0.01
    assert totals["(none)"] == 0.001


def test_total_matches_journey_total():
    journey = JourneyCost(journey="j", entries=[CostEntry(component="a", cost=0.01), CostEntry(component="b", cost=0.02)])

    report = attribute_journey_cost_to_domains(journey, component_domain_map={})

    assert report.total == 0.03


def test_empty_journey_produces_empty_report():
    journey = JourneyCost(journey="j", entries=[])

    report = attribute_journey_cost_to_domains(journey, component_domain_map={})

    assert report.total == 0.0
    assert report.by_domain() == {}
