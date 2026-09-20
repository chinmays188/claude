from pydantic import BaseModel

from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

ACTIONABILITY_TRUST_PROMPT = """Evaluate this AI response on two dimensions:

Actionability: does the response give the user something concrete they can act
on (a next step, a decision, a specific recommendation) rather than vague
generalities?

Trustworthiness: is the response appropriately confident — grounded in
evidence when evidence exists, and honest about uncertainty when it doesn't
(rather than confidently asserting something unsupported)?

User request: {question}
Response: {answer}

Respond with ONLY a JSON object:
{{"actionability": <float 0.0-1.0>, "trustworthiness": <float 0.0-1.0>, "reasoning": "<short explanation>"}}
"""


class ActionabilityTrustScore(BaseModel):
    actionability: float
    trustworthiness: float
    reasoning: str


def score_actionability_and_trust(llm: LLMProvider, question: str, answer: str) -> ActionabilityTrustScore:
    """Section 35's two metrics not already covered by Milestone 21's personal
    RAG eval (personalization, memory precision/recall, temporal correctness).
    Both are inherently judgment calls, so — consistent with Milestone 11's
    LLM-as-judge pattern — scored via a second LLM call rather than a rule."""
    generator = RepairableGenerator(llm, ActionabilityTrustScore)
    prompt = ACTIONABILITY_TRUST_PROMPT.format(question=question, answer=answer)
    return generator.generate(prompt)
