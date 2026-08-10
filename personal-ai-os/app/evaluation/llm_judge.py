from pydantic import BaseModel

from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

JUDGE_PROMPT = """You are an evaluation judge for an AI agent's response. Score it
across multiple dimensions, each from 0.0 (completely fails) to 1.0 (fully succeeds).
Do not just judge "was the answer good" — score each dimension independently.

User input: {user_input}
Expected behavior: {expected_behavior}
Agent output: {agent_output}
Retrieved context (if any): {retrieved_context}
Tool trace (if any): {tool_trace}

Respond with ONLY a JSON object:
{{
  "correctness": <float>,
  "completeness": <float>,
  "groundedness": <float>,
  "citation_quality": <float>,
  "instruction_following": <float>,
  "overall": <float>
}}
"""


class JudgeScore(BaseModel):
    correctness: float
    completeness: float
    groundedness: float
    citation_quality: float
    instruction_following: float
    overall: float


def judge_response(
    llm: LLMProvider,
    user_input: str,
    expected_behavior: str,
    agent_output: str,
    retrieved_context: str = "(none)",
    tool_trace: str = "(none)",
) -> JudgeScore:
    generator = RepairableGenerator(llm, JudgeScore)
    prompt = JUDGE_PROMPT.format(
        user_input=user_input,
        expected_behavior=expected_behavior,
        agent_output=agent_output,
        retrieved_context=retrieved_context,
        tool_trace=tool_trace,
    )
    return generator.generate(prompt)
