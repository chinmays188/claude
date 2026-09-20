from pydantic import BaseModel

from app.domains.pm.models import Prd, PrdCriticFeedback
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator


class CritiquedPrd(BaseModel):
    prd: Prd
    critique: PrdCriticFeedback

PRD_PROMPT = """Draft a PRD for this product idea, grounded in the retrieved
context below (existing product docs, prior research) where relevant. Do not
fabricate customer data, metrics, or experiment results that aren't present in
the context (Section 38).

Product idea: {idea}

Retrieved context (existing product docs / research excerpts):
{context}

Respond with ONLY a JSON object:
{{
  "problem_statement": "<the problem being solved>",
  "customer_context": "<who has this problem, grounded in retrieved context if available>",
  "hypothesis": "<what we believe will happen if we solve it>",
  "solution": "<proposed solution>",
  "metrics": ["<metric to track success>"],
  "experiment": "<how we'd validate the hypothesis before full build>"
}}
"""

CRITIC_PROMPT = """You are a skeptical Critic Agent reviewing this PRD. Your
job is to challenge it, not rubber-stamp it (Section 17). Answer each question
directly and specifically — vague answers like "seems fine" are not useful.

PRD:
{prd}

Respond with ONLY a JSON object:
{{
  "is_actually_a_problem": "<answer: is this really a problem worth solving?>",
  "is_ai_required": "<answer: does this actually need AI, or would a simpler approach work?>",
  "is_solution_over_engineered": "<answer: is the proposed solution more complex than necessary?>",
  "supporting_evidence": "<what evidence actually supports this, and what's missing?>",
  "falsification_criteria": "<what would prove the hypothesis wrong?>",
  "simplest_alternative": "<what is the simplest solution that could work?>",
  "verdict": "proceed" | "revise" | "reject"
}}
"""


def draft_prd(llm: LLMProvider, idea: str, secure_retriever: SecureRetriever, requester_id: str, requester_tenant_id: str, top_k: int = 8) -> Prd:
    """Section 17's pipeline up to the PRD itself: idea -> problem validation
    -> customer context -> existing product retrieval -> hypothesis -> solution
    -> metrics -> experiment."""
    if not idea or not idea.strip():
        raise ValueError("Product idea must not be empty.")

    retrieved = secure_retriever.search(
        idea, requester_id=requester_id, requester_tenant_id=requester_tenant_id, top_k=top_k
    )
    context = "\n".join(f"[{r.chunk.id}] {r.chunk.text}" for r in retrieved)
    if not context:
        context = "(no existing product documents or research found)"

    generator = RepairableGenerator(llm, Prd)
    return generator.generate(PRD_PROMPT.format(idea=idea, context=context))


def critique_prd(llm: LLMProvider, prd: Prd) -> PrdCriticFeedback:
    """Section 17's Critic Agent — a mandatory adversarial second pass over
    every PRD, not an optional add-on. Every one of the 6 questions Section 17
    lists is answered explicitly."""
    generator = RepairableGenerator(llm, PrdCriticFeedback)
    return generator.generate(CRITIC_PROMPT.format(prd=prd.model_dump_json()))


def draft_and_critique_prd(
    llm: LLMProvider, idea: str, secure_retriever: SecureRetriever, requester_id: str, requester_tenant_id: str, top_k: int = 8
) -> CritiquedPrd:
    """Convenience wrapper: a PRD without its critique is an incomplete
    artifact per Section 17 — this is the entry point most callers should use."""
    prd = draft_prd(llm, idea, secure_retriever, requester_id, requester_tenant_id, top_k)
    critique = critique_prd(llm, prd)
    return CritiquedPrd(prd=prd, critique=critique)
