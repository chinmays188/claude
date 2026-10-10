from datetime import datetime, timezone

from app.memory.conflict_resolution import ConflictResolver, ConflictVerdict
from app.memory.models import MemoryRecord, MemoryType
from app.providers.base import LLMProvider

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _memory(content: str, importance: float = 0.5) -> MemoryRecord:
    return MemoryRecord(
        memory_id="m1", tenant_id="t1", user_id="alice", type=MemoryType.PREFERENCE,
        content=content, source="conversation", created_at=NOW, updated_at=NOW, importance=importance,
    )


def test_genuine_contradiction_is_marked_superseded():
    llm = ScriptedProvider(['{"verdict": "CONTRADICTS", "reasoning": "Preference flipped from dark to light mode."}'])
    resolver = ConflictResolver(llm)
    existing = _memory("Prefers dark mode.")

    resolution = resolver.resolve(existing, "Prefers light mode now.", new_importance=0.5)

    assert resolution.judgment.verdict == ConflictVerdict.CONTRADICTS
    assert resolution.superseded is True
    assert resolution.existing_memory.memory_id == "m1"


def test_restatement_is_not_marked_superseded():
    llm = ScriptedProvider(['{"verdict": "SAME", "reasoning": "Just rephrased the same preference."}'])
    resolver = ConflictResolver(llm)
    existing = _memory("Prefers dark mode.")

    resolution = resolver.resolve(existing, "Likes using dark mode.", new_importance=0.5)

    assert resolution.judgment.verdict == ConflictVerdict.SAME
    assert resolution.superseded is False


def test_high_importance_conflict_requires_approval():
    llm = ScriptedProvider(['{"verdict": "CONTRADICTS", "reasoning": "Changed stated career goal."}'])
    resolver = ConflictResolver(llm, approval_threshold=0.7)
    existing = _memory("Wants to become an engineering manager.")

    resolution = resolver.resolve(existing, "No longer wants to become an engineering manager.", new_importance=0.9)

    assert resolution.superseded is True
    assert resolution.requires_approval is True


def test_low_importance_conflict_does_not_require_approval():
    llm = ScriptedProvider(['{"verdict": "CONTRADICTS", "reasoning": "Minor preference change."}'])
    resolver = ConflictResolver(llm, approval_threshold=0.7)
    existing = _memory("Prefers tea over coffee.", importance=0.3)

    resolution = resolver.resolve(existing, "Prefers coffee over tea now.", new_importance=0.3)

    assert resolution.superseded is True
    assert resolution.requires_approval is False
