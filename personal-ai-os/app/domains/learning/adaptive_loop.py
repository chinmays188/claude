from app.domains.learning.evaluator import evaluate_answer, identify_knowledge_gap
from app.domains.learning.models import AnswerEvaluation, Exercise, LearningProgress
from app.domains.learning.practice import generate_exercise
from app.providers.base import LLMProvider

MASTERY_THRESHOLD = 8.0  # average score (out of 10) considered mastered
MASTERY_MIN_ATTEMPTS = 2  # don't declare mastery off a single lucky answer


def _average_score(evaluation: AnswerEvaluation) -> float:
    return (
        evaluation.conceptual_understanding + evaluation.technical_depth
        + evaluation.application + evaluation.system_thinking + evaluation.pm_translation
    ) / 5


class AdaptiveLoop:
    """Section 29's loop: concept -> explanation -> example -> exercise ->
    answer -> evaluation -> knowledge gap -> next exercise. This class owns
    the exercise/evaluate/gap-track/decide-next step; explanation/example
    generation (tutor.py) happens once per concept, not repeated each round."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm
        self._progress: dict[str, LearningProgress] = {}

    def progress_for(self, concept: str) -> LearningProgress:
        return self._progress.setdefault(concept, LearningProgress(concept=concept))

    def run_round(self, concept: str, answer: str, exercise: Exercise | None = None) -> AnswerEvaluation:
        """Runs one exercise/evaluate/gap-track round and updates progress
        in place. If no exercise is supplied, generates one first."""
        if exercise is None:
            exercise = generate_exercise(self._llm, concept)

        evaluation = evaluate_answer(self._llm, exercise, answer)
        gaps = identify_knowledge_gap(self._llm, exercise, answer, evaluation)

        progress = self.progress_for(concept)
        score = _average_score(evaluation)
        progress.attempts += 1
        progress.average_score = (
            (progress.average_score * (progress.attempts - 1) + score) / progress.attempts
        )
        progress.knowledge_gaps = gaps
        progress.mastered = (
            progress.attempts >= MASTERY_MIN_ATTEMPTS and progress.average_score >= MASTERY_THRESHOLD
        )

        return evaluation

    def next_exercise(self, concept: str) -> Exercise:
        """Section 29: 'the system should adapt based on performance.' If
        there are known gaps, the next exercise targets the most severe gap
        rather than the concept in general."""
        progress = self.progress_for(concept)
        if progress.knowledge_gaps:
            worst_gap = max(progress.knowledge_gaps, key=lambda g: g.severity)
            return generate_exercise(self._llm, worst_gap.concept)
        return generate_exercise(self._llm, concept)
