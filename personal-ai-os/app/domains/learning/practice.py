from app.domains.learning.models import Exercise
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

EXERCISE_PROMPT = """Generate a single practice exercise/question for the
concept "{concept}", at difficulty level "{difficulty}". The exercise should
require the learner to actually apply the concept, not just recall a
definition.

Respond with ONLY a JSON object:
{{"concept": "{concept}", "question": "<the exercise question>", "expected_answer_summary": "<what a correct answer should cover, for grading>"}}
"""


def generate_exercise(llm: LLMProvider, concept: str, difficulty: str = "medium") -> Exercise:
    """Section 28's generate_exercise skill."""
    if not concept or not concept.strip():
        raise ValueError("Concept must not be empty.")
    generator = RepairableGenerator(llm, Exercise)
    return generator.generate(EXERCISE_PROMPT.format(concept=concept, difficulty=difficulty))


def generate_quiz(llm: LLMProvider, concept: str, num_questions: int = 3) -> list[Exercise]:
    """Section 28's generate_quiz skill — a quiz is just several exercises for
    the same concept, built by calling generate_exercise repeatedly rather than
    a separate generation path, so quiz questions get the same quality bar."""
    if num_questions <= 0:
        raise ValueError("num_questions must be positive.")
    return [generate_exercise(llm, concept) for _ in range(num_questions)]
