import pytest
from pydantic import BaseModel

from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator, StructuredOutputError


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.call_count = 0

    def generate(self, prompt: str) -> str:
        self.call_count += 1
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


class Classification(BaseModel):
    task_type: str
    confidence: float


def test_valid_on_first_try_makes_one_call():
    llm = ScriptedProvider(['{"task_type": "research", "confidence": 0.9}'])
    generator = RepairableGenerator(llm, Classification)

    result = generator.generate("classify this")

    assert result.task_type == "research"
    assert llm.call_count == 1


def test_repairs_after_one_invalid_response():
    llm = ScriptedProvider(
        [
            '{"confidence": "very high"}',
            '{"task_type": "research", "confidence": 0.9}',
        ]
    )
    generator = RepairableGenerator(llm, Classification)

    result = generator.generate("classify this")

    assert result.task_type == "research"
    assert llm.call_count == 2


def test_exhausts_repairs_and_raises():
    llm = ScriptedProvider(["not json"] * 10)
    generator = RepairableGenerator(llm, Classification, max_repair_attempts=2)

    with pytest.raises(StructuredOutputError):
        generator.generate("classify this")

    assert llm.call_count == 3  # initial + 2 repair attempts


def test_malformed_json_triggers_repair():
    llm = ScriptedProvider(
        [
            "not json at all",
            '{"task_type": "research", "confidence": 0.9}',
        ]
    )
    generator = RepairableGenerator(llm, Classification)

    result = generator.generate("classify this")

    assert result.task_type == "research"
