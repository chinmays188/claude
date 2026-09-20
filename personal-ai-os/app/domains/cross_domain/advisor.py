from pydantic import BaseModel

from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

ADVISOR_PROMPT = """A user is asking a question that spans multiple domains of
their life. Combine the domain-specific perspectives below into ONE
recommendation. Do not invent domain context not present below (Section 38).

User question: {question}

Domain perspectives (each pre-computed by that domain's own agent):
{perspectives}

Respond with ONLY a JSON object:
{{
  "career_relevance": "HIGH" | "MEDIUM" | "LOW",
  "current_work_relevance": "HIGH" | "MEDIUM" | "LOW",
  "learning_difficulty": "HIGH" | "MEDIUM" | "LOW",
  "recommended_priority": "HIGH" | "MEDIUM" | "LOW",
  "reasoning": "<why, referencing the domain perspectives given>"
}}
"""


class CrossDomainRecommendation(BaseModel):
    """Section 31's exact combined-output example (career relevance, current
    work relevance, learning difficulty, recommended priority) generalized
    beyond the one worked Kubernetes example."""

    career_relevance: str
    current_work_relevance: str
    learning_difficulty: str
    recommended_priority: str
    reasoning: str


class DomainPerspective(BaseModel):
    domain: str
    perspective: str


def combine_domain_perspectives(
    llm: LLMProvider, question: str, perspectives: list[DomainPerspective]
) -> CrossDomainRecommendation:
    """Section 31/32: takes perspectives already produced by each relevant
    domain (e.g. Learning OS's explain_concept, Career OS's JD-relevance
    analysis, PM OS's current-work relevance) and combines them into one
    recommendation — never regenerating domain-specific content itself, so
    each domain's own factuality/grounding guarantees carry through."""
    if not question or not question.strip():
        raise ValueError("Question must not be empty.")
    if not perspectives:
        raise ValueError("At least one domain perspective is required to combine.")

    perspectives_text = "\n".join(f"[{p.domain}] {p.perspective}" for p in perspectives)
    generator = RepairableGenerator(llm, CrossDomainRecommendation)
    return generator.generate(ADVISOR_PROMPT.format(question=question, perspectives=perspectives_text))
