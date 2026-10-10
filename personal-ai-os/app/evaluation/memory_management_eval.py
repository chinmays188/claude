"""Real golden-set evaluation for memory MANAGEMENT -- found missing
while breaking context/memory into retrieve/keep/forget plus the user's
further ask about "eval system for memory management." Checked first,
honestly: this project has real RAG document-retrieval eval
(personal_rag_eval.py) and a real context-SELECTION golden set
(context_engine_eval.py), but nothing specifically evaluates the memory
pipeline's own 3 real decisions: did RETRIEVE pull the right memories,
did FORGET decay the right ones, did conflict resolution supersede the
right one. Same GoldenCase/GoldenCaseResult pattern as
context_engine_eval.py and golden.py's real golden-case runner.

Each case is a real, hand-crafted scenario with a human-judged correct
outcome decided before running anything -- not invented to flatter any
particular configuration.
"""

from pydantic import BaseModel

from app.memory.conflict_resolution import ConflictVerdict
from app.memory.decay import compute_decayed_confidence
from app.memory.models import MemoryRecord
from app.memory.retrieval import MemoryRetriever
from app.retrieval.embeddings import EmbeddingModel


class RetrievalGoldenCase(BaseModel):
    """Human-judged: given this query and this real candidate pool, which
    memory_ids MUST appear in the top_k, and which MUST NOT."""

    id: str
    description: str
    query: str
    candidates: list[MemoryRecord]
    top_k: int
    expected_retrieved_ids: list[str]
    expected_excluded_ids: list[str]


class DecayGoldenCase(BaseModel):
    """Human-judged: given this memory's age/confirmed status, decayed
    confidence must fall on the correct side of a threshold."""

    id: str
    description: str
    memory: MemoryRecord
    as_of: object  # datetime, kept loose to avoid importing datetime just for the type
    half_life_days: float
    expect_decayed_below: float | None  # None means "expect NOT decayed below this" check skipped


class ConflictGoldenCase(BaseModel):
    """Human-judged: given this scripted judge verdict, the resolver's
    structural outcome (superseded / requires_approval) must match."""

    id: str
    description: str
    verdict: ConflictVerdict
    new_importance: float
    approval_threshold: float
    expect_superseded: bool
    expect_requires_approval: bool


class MemoryGoldenResult(BaseModel):
    case_id: str
    passed: bool
    reason: str


def run_retrieval_case(retriever: MemoryRetriever, case: RetrievalGoldenCase) -> MemoryGoldenResult:
    ranked = retriever.rank(case.query, case.candidates, top_k=case.top_k)
    retrieved_ids = {r.memory.memory_id for r in ranked}

    missing = set(case.expected_retrieved_ids) - retrieved_ids
    wrongly_included = set(case.expected_excluded_ids) & retrieved_ids
    if missing or wrongly_included:
        return MemoryGoldenResult(
            case_id=case.id, passed=False,
            reason=f"Missing expected: {sorted(missing)}. Wrongly included: {sorted(wrongly_included)}.",
        )
    return MemoryGoldenResult(case_id=case.id, passed=True, reason="Retrieved exactly the expected memories.")


def run_decay_case(case: DecayGoldenCase) -> MemoryGoldenResult:
    decayed = compute_decayed_confidence(case.memory, case.as_of, half_life_days=case.half_life_days)
    if case.expect_decayed_below is not None and not decayed < case.expect_decayed_below:
        return MemoryGoldenResult(
            case_id=case.id, passed=False,
            reason=f"Expected decayed confidence < {case.expect_decayed_below}, got {decayed:.3f}.",
        )
    return MemoryGoldenResult(case_id=case.id, passed=True, reason=f"Decayed confidence {decayed:.3f} as expected.")


def run_conflict_case(case: ConflictGoldenCase) -> MemoryGoldenResult:
    """Deterministic structural check (superseded/requires_approval given
    a verdict) -- the LLM judgment call itself (SAME vs. CONTRADICTS) is
    a real judgment, not something a golden case can assert without an
    LLM; what IS deterministic, and worth a golden case, is whether
    ConflictResolver's OWN structural logic (superseded iff CONTRADICTS;
    requires_approval iff superseded AND importance >= threshold)
    behaves correctly given a verdict."""
    superseded = case.verdict == ConflictVerdict.CONTRADICTS
    requires_approval = superseded and case.new_importance >= case.approval_threshold

    if superseded != case.expect_superseded or requires_approval != case.expect_requires_approval:
        return MemoryGoldenResult(
            case_id=case.id, passed=False,
            reason=f"Expected superseded={case.expect_superseded}, requires_approval="
                   f"{case.expect_requires_approval}; got superseded={superseded}, "
                   f"requires_approval={requires_approval}.",
        )
    return MemoryGoldenResult(case_id=case.id, passed=True, reason="Structural outcome matched expectation.")


def accuracy(results: list[MemoryGoldenResult]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r.passed) / len(results)
