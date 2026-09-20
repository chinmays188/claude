from pydantic import BaseModel

from app.domains.career.models import ResumeOptimizationResult
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator


class ResumeOptimizationOutcome(BaseModel):
    result: ResumeOptimizationResult
    valid_excerpt_ids: list[str]

OPTIMIZE_PROMPT = """You are optimizing a resume for a specific job description,
using ONLY the candidate's real, retrieved achievement excerpts below. You must
NEVER invent an achievement, metric, or experience that is not present in the
excerpts (Section 10 rule 6). Every suggested bullet change must be traceable
to one of the excerpt ids provided.

Job description:
{jd_text}

Candidate's retrieved achievement excerpts (id -> text):
{excerpts}

Respond with ONLY a JSON object:
{{
  "missing_keywords": ["<keyword from the JD not reflected in the resume>"],
  "suggested_bullet_changes": ["<a specific, grounded rewording suggestion>"],
  "grounding_achievement_ids": ["<excerpt id(s) each suggestion is based on>"]
}}
"""


def optimize_resume(
    llm: LLMProvider,
    jd_text: str,
    secure_retriever: SecureRetriever,
    requester_id: str,
    requester_tenant_id: str,
    top_k: int = 8,
) -> ResumeOptimizationOutcome:
    """Section 10: retrieve real achievements, match to JD, identify missing
    keywords, suggest changes -- never invent achievements. valid_excerpt_ids
    lets a caller verify (via check_resume_suggestions_grounded below) that
    every suggestion traces back to a real, retrieved excerpt."""
    if not jd_text or not jd_text.strip():
        raise ValueError("Job description text must not be empty.")

    retrieved = secure_retriever.search(
        jd_text, requester_id=requester_id, requester_tenant_id=requester_tenant_id, top_k=top_k
    )
    excerpts = "\n".join(f"[{r.chunk.id}] {r.chunk.text}" for r in retrieved)
    if not excerpts:
        excerpts = "(no resume or achievement documents found for this candidate)"

    generator = RepairableGenerator(llm, ResumeOptimizationResult)
    prompt = OPTIMIZE_PROMPT.format(jd_text=jd_text, excerpts=excerpts)
    result = generator.generate(prompt)

    return ResumeOptimizationOutcome(
        result=result, valid_excerpt_ids=[r.chunk.id for r in retrieved]
    )


def _normalize_excerpt_id(excerpt_id: str) -> str:
    """The model sometimes echoes an excerpt id back wrapped in the same
    brackets the prompt displays it in (e.g. "[doc::chunk0]" instead of
    "doc::chunk0") — a formatting quirk, not a fabricated id. Caught via a
    real live trace against a real resume: the achievement content was
    genuine, but the exact-match check below flagged it as ungrounded
    purely because of the stray brackets."""
    return excerpt_id.strip().strip("[]").strip()


def check_resume_suggestions_grounded(
    result: ResumeOptimizationResult, valid_excerpt_ids: set[str]
) -> bool:
    """Section 10's factuality requirement, made checkable: every grounding id
    the model cited must actually be one of the excerpts it was given — a
    fabricated id here would mean a suggestion isn't really grounded in the
    candidate's real achievements."""
    if not result.grounding_achievement_ids:
        return len(result.suggested_bullet_changes) == 0
    normalized_valid_ids = {_normalize_excerpt_id(vid) for vid in valid_excerpt_ids}
    return all(
        _normalize_excerpt_id(gid) in normalized_valid_ids
        for gid in result.grounding_achievement_ids
    )


def check_outcome_grounded(outcome: ResumeOptimizationOutcome) -> bool:
    return check_resume_suggestions_grounded(outcome.result, set(outcome.valid_excerpt_ids))
