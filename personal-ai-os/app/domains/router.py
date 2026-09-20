from enum import Enum

from pydantic import BaseModel

from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator, StructuredOutputError

DOMAIN_ROUTER_PROMPT = """Classify which domain(s) of a Personal AI OS this request
belongs to. A request can belong to more than one domain when it genuinely spans
both (Section 5's example: "Should I learn this technology for my career?" is
both CAREER and LEARNING) — do not force a single answer when the request is
truly cross-domain, but do not split a request across domains just because it
touches multiple topics in passing either.

Domains:
- CAREER: resume, job descriptions, interviews, career goals, networking
- PM: product management work — feedback, stakeholder requests, PRDs, sprints, project status
- FINANCE: portfolio, investments, loans, financial goals and projections
- LEARNING: explaining or teaching a technical concept, skill-building
- UNCLEAR: the request doesn't clearly belong to any domain, or is too ambiguous

User request: {text}

Respond with ONLY a JSON object:
{{"domains": ["CAREER" | "PM" | "FINANCE" | "LEARNING"], "confidence": 0.0-1.0}}

If the request is unclear, respond with {{"domains": [], "confidence": <low value>}}.
"""


class Domain(str, Enum):
    CAREER = "CAREER"
    PM = "PM"
    FINANCE = "FINANCE"
    LEARNING = "LEARNING"


class DomainClassification(BaseModel):
    domains: list[Domain]
    confidence: float

    @property
    def is_unclear(self) -> bool:
        return len(self.domains) == 0

    @property
    def is_cross_domain(self) -> bool:
        return len(self.domains) > 1


class DomainRoutingError(Exception):
    pass


class DomainRouter:
    """Section 5: classifies a request into one or more of the four Phase 3
    domains, or UNCLEAR (represented as an empty domain list) when confidence
    is too low. Multi-domain output is a first-class case, not an edge case —
    the router does not force a single label onto a genuinely cross-domain
    request (Section 31's "Should I learn Kubernetes?" example)."""

    def __init__(self, llm: LLMProvider, confidence_threshold: float = 0.5):
        self._generator = RepairableGenerator(llm, DomainClassification)
        self._confidence_threshold = confidence_threshold

    def route(self, text: str) -> DomainClassification:
        if not text or not text.strip():
            raise ValueError("Input text must not be empty.")

        try:
            result = self._generator.generate(DOMAIN_ROUTER_PROMPT.format(text=text))
        except StructuredOutputError as exc:
            raise DomainRoutingError(str(exc)) from exc

        if result.confidence < self._confidence_threshold:
            return DomainClassification(domains=[], confidence=result.confidence)

        return result
