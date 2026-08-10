from enum import Enum

from pydantic import BaseModel


class AdaptationApproach(str, Enum):
    IN_CONTEXT_LEARNING = "in_context_learning"
    RAG = "rag"
    FINE_TUNING = "fine_tuning"
    DISTILLATION = "distillation"


class AdaptationProblem(BaseModel):
    needs_fresh_external_knowledge: bool = False
    needs_specific_output_style_or_format: bool = False
    is_simple_and_example_solvable: bool = False
    needs_smaller_model_to_match_larger_model: bool = False


def recommend_approach(problem: AdaptationProblem) -> AdaptationApproach:
    """Codifies Section 57's decision framework as explicit, testable rules —
    not a model to train, but the actual if/then logic the spec describes.
    Rules are checked in a fixed priority order since a problem can technically
    match more than one signal."""
    if problem.needs_smaller_model_to_match_larger_model:
        return AdaptationApproach.DISTILLATION
    if problem.needs_fresh_external_knowledge:
        return AdaptationApproach.RAG
    if problem.needs_specific_output_style_or_format:
        return AdaptationApproach.FINE_TUNING
    if problem.is_simple_and_example_solvable:
        return AdaptationApproach.IN_CONTEXT_LEARNING
    raise ValueError(
        "No adaptation signal matched — this problem needs a more specific "
        "diagnosis before choosing an approach (see Section 57's framework)."
    )
