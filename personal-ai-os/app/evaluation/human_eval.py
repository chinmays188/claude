from pydantic import BaseModel, Field


class HumanRating(BaseModel):
    case_id: str
    correctness: int = Field(ge=1, le=5)
    relevance: int = Field(ge=1, le=5)
    completeness: int = Field(ge=1, le=5)
    trustworthiness: int = Field(ge=1, le=5)
    usefulness: int = Field(ge=1, le=5)
    citation_quality: int = Field(ge=1, le=5)

    @property
    def average(self) -> float:
        return (
            self.correctness + self.relevance + self.completeness
            + self.trustworthiness + self.usefulness + self.citation_quality
        ) / 6


def judge_human_correlation(judge_scores: list[float], human_scores: list[float]) -> float:
    """Pearson correlation between LLM-judge scores and human scores (both normalized
    to the same scale by the caller). Answers Section 17's question: how well does
    the automated judge track human judgment?"""
    if len(judge_scores) != len(human_scores):
        raise ValueError("judge_scores and human_scores must be the same length.")
    n = len(judge_scores)
    if n < 2:
        raise ValueError("Need at least 2 paired scores to compute correlation.")

    mean_j = sum(judge_scores) / n
    mean_h = sum(human_scores) / n

    cov = sum((j - mean_j) * (h - mean_h) for j, h in zip(judge_scores, human_scores))
    var_j = sum((j - mean_j) ** 2 for j in judge_scores)
    var_h = sum((h - mean_h) ** 2 for h in human_scores)

    denominator = (var_j * var_h) ** 0.5
    if denominator == 0:
        return 0.0
    return cov / denominator
