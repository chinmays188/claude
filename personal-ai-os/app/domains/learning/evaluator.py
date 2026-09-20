from pydantic import BaseModel

from app.domains.learning.models import AnswerEvaluation, Exercise, KnowledgeGap
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

EVALUATE_PROMPT = """Evaluate this learner's answer to a practice exercise.
Score each dimension independently from 0 to 10 (Section 30's exact rubric) —
do not just give one blended score.

Exercise: {question}
What a correct answer should cover: {expected_answer_summary}
Learner's answer: {answer}

Respond with ONLY a JSON object:
{{
  "conceptual_understanding": <0-10>,
  "technical_depth": <0-10>,
  "application": <0-10>,
  "system_thinking": <0-10>,
  "pm_translation": <0-10>,
  "feedback": "<short, specific feedback>"
}}
"""

GAP_PROMPT = """Based on this learner's answer and its evaluation, identify any
specific knowledge gap revealed. If the answer was strong across all
dimensions, respond with an empty list.

Exercise: {question}
Learner's answer: {answer}
Evaluation: {evaluation}

Respond with ONLY a JSON object:
{{"gaps": [{{"concept": "<specific sub-concept>", "description": "<what's missing/wrong>", "severity": <0.0-1.0>}}]}}
"""


class _GapList(BaseModel):
    gaps: list[KnowledgeGap]


def evaluate_answer(llm: LLMProvider, exercise: Exercise, answer: str) -> AnswerEvaluation:
    """Section 28/30's evaluate_answer skill — scores the 5 dimensions Section
    30 lists explicitly, never a single blended score."""
    if not answer or not answer.strip():
        raise ValueError("Answer must not be empty.")
    generator = RepairableGenerator(llm, AnswerEvaluation)
    prompt = EVALUATE_PROMPT.format(
        question=exercise.question, expected_answer_summary=exercise.expected_answer_summary, answer=answer
    )
    return generator.generate(prompt)


def identify_knowledge_gap(
    llm: LLMProvider, exercise: Exercise, answer: str, evaluation: AnswerEvaluation
) -> list[KnowledgeGap]:
    """Section 28's identify_knowledge_gap skill — feeds the adaptive loop
    (Section 29): a caller uses this to decide what to teach/exercise next."""
    generator = RepairableGenerator(llm, _GapList)
    prompt = GAP_PROMPT.format(
        question=exercise.question, answer=answer, evaluation=evaluation.model_dump_json()
    )
    result = generator.generate(prompt)
    return result.gaps
