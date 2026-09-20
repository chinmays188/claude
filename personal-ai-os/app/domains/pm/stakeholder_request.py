from app.domains.pm.models import StakeholderRequestAnalysis
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

ANALYZE_PROMPT = """A stakeholder made this request. Analyze it using ONLY the
evidence retrieved below (existing roadmap, past decisions, prior feedback) —
do not fabricate roadmap items or stakeholder statements that aren't present.

Stakeholder request: {request}

Retrieved evidence (roadmap/decisions/feedback excerpts):
{evidence}

Respond with ONLY a JSON object:
{{
  "request": "{request}",
  "problem_extracted": "<the underlying problem, not just the literal ask>",
  "user_impact": "<who is affected and how>",
  "recommendation": "BUILD" | "INVESTIGATE" | "REJECT" | "DEFER" | "NEED_MORE_EVIDENCE",
  "reasoning": "<why this recommendation, grounded in the evidence above>"
}}
"""


def analyze_stakeholder_request(
    llm: LLMProvider,
    request: str,
    secure_retriever: SecureRetriever,
    requester_id: str,
    requester_tenant_id: str,
    top_k: int = 8,
) -> StakeholderRequestAnalysis:
    """Section 16's pipeline: request -> problem extraction -> user impact ->
    evidence retrieval -> existing roadmap -> priority analysis ->
    recommendation, with reasoning always included (Section 16: 'The system
    should explain why')."""
    if not request or not request.strip():
        raise ValueError("Stakeholder request must not be empty.")

    retrieved = secure_retriever.search(
        request, requester_id=requester_id, requester_tenant_id=requester_tenant_id, top_k=top_k
    )
    evidence = "\n".join(f"[{r.chunk.id}] {r.chunk.text}" for r in retrieved)
    if not evidence:
        evidence = "(no roadmap, decision, or feedback documents found)"

    generator = RepairableGenerator(llm, StakeholderRequestAnalysis)
    return generator.generate(ANALYZE_PROMPT.format(request=request, evidence=evidence))
