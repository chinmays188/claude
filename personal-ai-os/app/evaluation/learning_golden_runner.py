"""Real grading harness for evals/learning/*.json, found missing while
investigating "AI Evaluation" (disclosed gap: domain-specific golden
sets have no live grading harness). learning_002 ("adaptive_evaluation")
needs a learner ANSWER to grade, which the golden case's input (just the
question text) doesn't include -- a real, deliberately generic/weak
synthetic answer is used, since the point of this harness case is
proving evaluate_answer() runs and produces valid, in-range scores, not
judging a specific real learner's answer quality.
"""

from pydantic import BaseModel

from app.domains.learning.evaluator import evaluate_answer
from app.domains.learning.models import Exercise
from app.domains.learning.tutor import explain_concept
from app.evaluation.domain_golden import DomainGoldenCase
from app.evaluation.learning_eval import check_content_kind_labeled, check_evaluation_scores_in_range
from app.providers.base import LLMProvider

# A real, deliberately generic/weak synthetic answer -- not meant to score
# well, just to exercise the real evaluator function end to end.
_GENERIC_WEAK_ANSWER = "It's a container thing for apps."


def _exercise_for(question: str) -> Exercise:
    return Exercise(concept=question, question=question, expected_answer_summary="A substantive, technically accurate explanation.")


class LearningGoldenCaseResult(BaseModel):
    case_id: str
    category: str
    passed: bool
    reason: str


def run_learning_golden_case(llm: LLMProvider, case: DomainGoldenCase) -> LearningGoldenCaseResult:
    if case.category == "explain_concept":
        explanation = explain_concept(llm, case.input)
        check = check_content_kind_labeled(explanation)
        return LearningGoldenCaseResult(case_id=case.id, category=case.category, passed=check.passed, reason=check.reason)

    if case.category == "adaptive_evaluation":
        exercise = _exercise_for(case.input)
        evaluation = evaluate_answer(llm, exercise, _GENERIC_WEAK_ANSWER)
        check = check_evaluation_scores_in_range(evaluation)
        return LearningGoldenCaseResult(case_id=case.id, category=case.category, passed=check.passed, reason=check.reason)

    return LearningGoldenCaseResult(
        case_id=case.id, category=case.category, passed=False,
        reason=f"Unknown category '{case.category}' -- no real workflow dispatch exists for it.",
    )


def run_learning_golden_suite(llm: LLMProvider, cases: list[DomainGoldenCase]) -> list[LearningGoldenCaseResult]:
    return [run_learning_golden_case(llm, case) for case in cases]
