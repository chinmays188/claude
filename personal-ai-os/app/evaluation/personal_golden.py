from enum import Enum

from pydantic import BaseModel

from app.personal_rag.pipeline import PersonalRagPipeline


class PersonalEvalCategory(str, Enum):
    """Section 34's evaluation categories, extended from Phase 1's generic
    golden-set framework to personal workloads specifically."""

    CAREER = "career"
    LEARNING = "learning"
    PM = "pm"
    PERSONAL_KNOWLEDGE = "personal_knowledge"


class PersonalGoldenCase(BaseModel):
    id: str
    category: PersonalEvalCategory
    question: str
    requester_id: str
    requester_tenant_id: str
    expected_answer_contains: list[str] = []
    expected_citation_document_ids: list[str] = []


class PersonalGoldenResult(BaseModel):
    case_id: str
    category: PersonalEvalCategory
    passed: bool
    reason: str


def run_personal_golden_case(
    pipeline: PersonalRagPipeline, case: PersonalGoldenCase, memory_candidates: list = None
) -> PersonalGoldenResult:
    result = pipeline.answer(
        case.question, requester_id=case.requester_id, requester_tenant_id=case.requester_tenant_id,
        memory_candidates=memory_candidates or [],
    )

    missing_content = [m for m in case.expected_answer_contains if m.lower() not in result.answer.lower()]
    if missing_content:
        return PersonalGoldenResult(
            case_id=case.id, category=case.category, passed=False,
            reason=f"Answer missing expected content: {missing_content}",
        )

    cited_doc_ids = {c.chunk_id.split("::")[0] for c in result.citations}
    missing_citations = set(case.expected_citation_document_ids) - cited_doc_ids
    if missing_citations:
        return PersonalGoldenResult(
            case_id=case.id, category=case.category, passed=False,
            reason=f"Expected citation(s) from document(s) {sorted(missing_citations)} not found.",
        )

    return PersonalGoldenResult(case_id=case.id, category=case.category, passed=True, reason="All expectations met.")


def run_personal_golden_set(
    pipeline: PersonalRagPipeline, cases: list[PersonalGoldenCase]
) -> list[PersonalGoldenResult]:
    return [run_personal_golden_case(pipeline, case) for case in cases]


def pass_rate_by_category(results: list[PersonalGoldenResult]) -> dict[str, float]:
    """Section 34's categories deserve independent visibility — a single blended
    pass rate could hide 'career eval is failing but learning is fine.'"""
    by_category: dict[str, list[PersonalGoldenResult]] = {}
    for r in results:
        by_category.setdefault(r.category.value, []).append(r)

    return {
        category: sum(1 for r in cat_results if r.passed) / len(cat_results)
        for category, cat_results in by_category.items()
    }
