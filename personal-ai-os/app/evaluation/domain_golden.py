import json
from pathlib import Path

from pydantic import BaseModel

EVALS_ROOT = Path(__file__).resolve().parent.parent.parent / "evals"


class DomainGoldenCase(BaseModel):
    """Generic shape for the per-domain golden case JSON files (Section 39):
    evals/{career,pm,finance,learning}/*.json. Fields beyond id/category are
    deliberately loose (dict) since each domain's cases carry different input
    shapes — a labeled test runner for a specific workflow (e.g.
    test_career_jd_analysis.py) is where the strict, typed assertions live;
    this model is just for loading/counting/iterating cases."""

    id: str
    category: str = ""
    input: dict | str | list = None
    expected_capabilities: list[str] = []
    expected_domains: list[str] = []


def load_domain_cases(domain: str) -> list[DomainGoldenCase]:
    """Section 39: 'evals/career/, evals/pm/, evals/finance/, evals/learning/,
    evals/cross_domain/.' Loads every *.json file in a domain's eval
    directory and returns the combined case list."""
    domain_dir = EVALS_ROOT / domain
    if not domain_dir.is_dir():
        raise FileNotFoundError(f"No eval directory for domain '{domain}' at {domain_dir}")

    cases: list[DomainGoldenCase] = []
    for path in sorted(domain_dir.glob("*.json")):
        raw = json.loads(path.read_text())
        cases.extend(DomainGoldenCase.model_validate(item) for item in raw)
    return cases


def count_cases_by_domain() -> dict[str, int]:
    """Section 39's target tracking: '50 cases / domain, eventually 100+.'
    This makes current progress toward that target visible and queryable."""
    domains = ["career", "pm", "finance", "learning", "cross_domain"]
    return {domain: len(load_domain_cases(domain)) for domain in domains}
