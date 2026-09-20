from app.domains.learning.adaptive_loop import AdaptiveLoop
from app.domains.learning.models import Exercise
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _exercise() -> Exercise:
    return Exercise(concept="Docker", question="What does a Dockerfile do?", expected_answer_summary="Defines how to build an image.")


def test_run_round_updates_progress():
    llm = ScriptedProvider(
        [
            '{"conceptual_understanding": 8, "technical_depth": 8, "application": 8, "system_thinking": 8, "pm_translation": 8, "feedback": "great"}',
            '{"gaps": []}',
        ]
    )
    loop = AdaptiveLoop(llm)

    loop.run_round("Docker", "A good answer.", exercise=_exercise())

    progress = loop.progress_for("Docker")
    assert progress.attempts == 1
    assert progress.average_score == 8.0


def test_average_score_accumulates_across_rounds():
    llm = ScriptedProvider(
        [
            '{"conceptual_understanding": 4, "technical_depth": 4, "application": 4, "system_thinking": 4, "pm_translation": 4, "feedback": "weak"}',
            '{"gaps": [{"concept": "Docker layers", "description": "missed it", "severity": 0.7}]}',
            '{"conceptual_understanding": 8, "technical_depth": 8, "application": 8, "system_thinking": 8, "pm_translation": 8, "feedback": "better"}',
            '{"gaps": []}',
        ]
    )
    loop = AdaptiveLoop(llm)

    loop.run_round("Docker", "weak answer", exercise=_exercise())
    loop.run_round("Docker", "better answer", exercise=_exercise())

    progress = loop.progress_for("Docker")
    assert progress.attempts == 2
    assert progress.average_score == 6.0  # (4 + 8) / 2


def test_mastery_requires_min_attempts_and_high_score():
    llm = ScriptedProvider(
        [
            '{"conceptual_understanding": 9, "technical_depth": 9, "application": 9, "system_thinking": 9, "pm_translation": 9, "feedback": "great"}',
            '{"gaps": []}',
        ]
    )
    loop = AdaptiveLoop(llm)

    loop.run_round("Docker", "great answer", exercise=_exercise())

    # Single high-scoring attempt should NOT yet count as mastered.
    assert loop.progress_for("Docker").mastered is False


def test_mastery_achieved_after_enough_high_scoring_attempts():
    llm = ScriptedProvider(
        [
            '{"conceptual_understanding": 9, "technical_depth": 9, "application": 9, "system_thinking": 9, "pm_translation": 9, "feedback": "great"}',
            '{"gaps": []}',
            '{"conceptual_understanding": 9, "technical_depth": 9, "application": 9, "system_thinking": 9, "pm_translation": 9, "feedback": "great"}',
            '{"gaps": []}',
        ]
    )
    loop = AdaptiveLoop(llm)

    loop.run_round("Docker", "great answer", exercise=_exercise())
    loop.run_round("Docker", "great answer again", exercise=_exercise())

    assert loop.progress_for("Docker").mastered is True


def test_next_exercise_targets_worst_knowledge_gap():
    llm = ScriptedProvider(
        [
            '{"conceptual_understanding": 5, "technical_depth": 5, "application": 5, "system_thinking": 5, "pm_translation": 5, "feedback": "ok"}',
            '{"gaps": [{"concept": "Docker networking", "description": "confused ports", "severity": 0.9}, '
            '{"concept": "Docker volumes", "description": "minor confusion", "severity": 0.3}]}',
            '{"concept": "Docker networking", "question": "Explain port mapping.", "expected_answer_summary": "..."}',
        ]
    )
    loop = AdaptiveLoop(llm)
    loop.run_round("Docker", "some answer", exercise=_exercise())

    next_ex = loop.next_exercise("Docker")

    assert next_ex.concept == "Docker networking"


def test_next_exercise_targets_original_concept_when_no_gaps():
    llm = ScriptedProvider(
        [
            '{"conceptual_understanding": 9, "technical_depth": 9, "application": 9, "system_thinking": 9, "pm_translation": 9, "feedback": "great"}',
            '{"gaps": []}',
            '{"concept": "Docker", "question": "Another question.", "expected_answer_summary": "..."}',
        ]
    )
    loop = AdaptiveLoop(llm)
    loop.run_round("Docker", "great answer", exercise=_exercise())

    next_ex = loop.next_exercise("Docker")

    assert next_ex.concept == "Docker"


def test_run_round_generates_exercise_when_none_supplied():
    llm = ScriptedProvider(
        [
            '{"concept": "Docker", "question": "Generated Q?", "expected_answer_summary": "..."}',
            '{"conceptual_understanding": 7, "technical_depth": 7, "application": 7, "system_thinking": 7, "pm_translation": 7, "feedback": "fine"}',
            '{"gaps": []}',
        ]
    )
    loop = AdaptiveLoop(llm)

    loop.run_round("Docker", "an answer")

    assert loop.progress_for("Docker").attempts == 1
