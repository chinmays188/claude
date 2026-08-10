import json

from pydantic import BaseModel

from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

GROUNDING_PROMPT = """You are evaluating whether an AI-generated answer is grounded in
the retrieved evidence provided to it. Do not judge whether the answer is well-written —
only whether its factual claims are supported by the evidence.

Retrieved evidence (chunk id -> text):
{evidence}

Answer to evaluate:
{answer}

Respond with ONLY a JSON object:
{{
  "grounded_claim_count": <int, number of factual claims supported by the evidence>,
  "unsupported_claim_count": <int, number of factual claims NOT supported by the evidence>,
  "groundedness_score": <float 0.0-1.0, fraction of claims that are grounded>,
  "citations": [{{"claim": "<short claim text>", "chunk_id": "<supporting chunk id>"}}]
}}
"""


class Citation(BaseModel):
    claim: str
    chunk_id: str


class GroundingResult(BaseModel):
    grounded_claim_count: int
    unsupported_claim_count: int
    groundedness_score: float
    citations: list[Citation]


def evaluate_grounding(
    llm: LLMProvider, answer: str, evidence: dict[str, str]
) -> GroundingResult:
    generator = RepairableGenerator(llm, GroundingResult)
    prompt = GROUNDING_PROMPT.format(
        evidence=json.dumps(evidence),
        answer=answer,
    )
    return generator.generate(prompt)


def citation_quality(result: GroundingResult, valid_chunk_ids: set[str]) -> float:
    """Fraction of citations that point to a chunk id that actually exists."""
    if not result.citations:
        return 0.0
    valid = sum(1 for c in result.citations if c.chunk_id in valid_chunk_ids)
    return valid / len(result.citations)
