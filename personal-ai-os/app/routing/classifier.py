from enum import Enum

from pydantic import BaseModel

from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator, StructuredOutputError

CLASSIFIER_PROMPT = """Classify the user's request into exactly one task type.

Task types:
- research: asking to explain, look up, or gather information on a topic
- analysis: asking to compare, evaluate, or judge between options
- planning: asking to create a plan, schedule, or sequenced set of steps
- unclear: the request is too ambiguous to classify confidently

Respond with ONLY a JSON object of the form:
{{"task_type": "research" | "analysis" | "planning" | "unclear", "confidence": 0.0-1.0}}

User request: {text}
"""


class TaskType(str, Enum):
    RESEARCH = "research"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    UNCLEAR = "unclear"


class Classification(BaseModel):
    task_type: TaskType
    confidence: float


class ClassificationError(Exception):
    pass


class TaskClassifier:
    def __init__(self, llm: LLMProvider, confidence_threshold: float = 0.5):
        self._generator = RepairableGenerator(llm, Classification)
        self._confidence_threshold = confidence_threshold

    def classify(self, text: str) -> Classification:
        try:
            result = self._generator.generate(CLASSIFIER_PROMPT.format(text=text))
        except StructuredOutputError as exc:
            raise ClassificationError(str(exc)) from exc

        if result.confidence < self._confidence_threshold:
            return Classification(task_type=TaskType.UNCLEAR, confidence=result.confidence)

        return result
