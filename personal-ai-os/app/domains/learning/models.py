from enum import Enum

from pydantic import BaseModel, Field


class ContentKind(str, Enum):
    """Section 38: Learning OS must clearly distinguish factual explanation
    from analogy from speculation — every generated piece of teaching content
    is tagged with which of these it is."""

    FACTUAL = "factual"
    ANALOGY = "analogy"
    SPECULATION = "speculation"


class Explanation(BaseModel):
    concept: str
    content: str
    kind: ContentKind


class Exercise(BaseModel):
    concept: str
    question: str
    expected_answer_summary: str  # what a correct answer should cover, for grading


class AnswerEvaluation(BaseModel):
    """Section 30's exact evaluation dimensions, each 0-10 per the example."""

    conceptual_understanding: int = Field(ge=0, le=10)
    technical_depth: int = Field(ge=0, le=10)
    application: int = Field(ge=0, le=10)
    system_thinking: int = Field(ge=0, le=10)
    pm_translation: int = Field(ge=0, le=10)
    feedback: str


class KnowledgeGap(BaseModel):
    concept: str
    description: str
    severity: float  # 0.0-1.0


class LearningProgress(BaseModel):
    """Tracks one learner's state across the adaptive loop (Section 29) for a
    given concept — enough state to decide what to teach/exercise next."""

    concept: str
    attempts: int = 0
    average_score: float = 0.0
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list)
    mastered: bool = False
