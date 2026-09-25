"""Combines the two previously-separate, disconnected routers
(app/domains/router.py's DomainRouter and app/routing/classifier.py's
TaskClassifier) into a single entry point.

Found while building the dashboard's Architecture page: DomainRouter
(CAREER/PM/FINANCE/LEARNING) was used only by scripts/trace_request.py and
tests, while TaskClassifier+Orchestrator (RESEARCH/ANALYSIS/PLANNING) was
what app/main.py and app/api/voice_api.py actually used in production --
neither called the other, and nothing combined their outputs. The user
asked for one router.

Design decision (confirmed with the user): domain and task-type are
different axes, not redundant labels -- "what life area is this about" vs.
"what kind of cognitive task is this." UnifiedRouter classifies both,
two stages, reusing DomainRouter and TaskClassifier's own already-tested
prompts/logic rather than re-deriving a single fused classifier from
scratch. This is 2 LLM calls per request (same as running both routers
separately did before), not fewer -- no attempt was made to fuse them into
one call, since that would mean rewriting and re-validating both prompts
at once.

Domain is genuinely optional here: many real requests (e.g. "what's 47
times 12") don't belong to any of the four Phase 3 domains at all, and
forcing one would misclassify them. GENERAL is a first-class outcome, not
a fallback error.
"""

from pydantic import BaseModel

from app.domains.router import Domain, DomainRouter, DomainRoutingError
from app.providers.base import LLMProvider
from app.routing.classifier import ClassificationError, TaskClassifier, TaskType


class UnifiedClassification(BaseModel):
    domain: Domain | None  # None means GENERAL -- doesn't fit a Phase 3 domain
    domain_confidence: float
    is_cross_domain: bool  # True if DomainRouter found multiple domains; we surface only the first as `domain`
    all_domains: list[Domain]  # every domain DomainRouter found, for cross-domain visibility
    task_type: TaskType
    task_confidence: float


class UnifiedRoutingError(Exception):
    pass


class UnifiedRouter:
    """Single entry point replacing separate DomainRouter/TaskClassifier
    calls. Classifies domain first, then task-type -- both real LLM calls,
    reusing the existing, already-tested classifiers internally."""

    def __init__(self, llm: LLMProvider):
        self._domain_router = DomainRouter(llm)
        self._task_classifier = TaskClassifier(llm)

    def route(self, text: str) -> UnifiedClassification:
        if not text or not text.strip():
            raise ValueError("Input text must not be empty.")

        try:
            domain_result = self._domain_router.route(text)
        except DomainRoutingError as exc:
            raise UnifiedRoutingError(f"Domain classification failed: {exc}") from exc

        try:
            task_result = self._task_classifier.classify(text)
        except ClassificationError as exc:
            raise UnifiedRoutingError(f"Task-type classification failed: {exc}") from exc

        primary_domain = domain_result.domains[0] if domain_result.domains else None

        return UnifiedClassification(
            domain=primary_domain,
            domain_confidence=domain_result.confidence,
            is_cross_domain=domain_result.is_cross_domain,
            all_domains=domain_result.domains,
            task_type=task_result.task_type,
            task_confidence=task_result.confidence,
        )
