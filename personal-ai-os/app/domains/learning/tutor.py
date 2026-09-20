from app.domains.learning.models import ContentKind, Explanation
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

EXPLAIN_PROMPT = """Explain the concept "{concept}" clearly and factually, at a
level appropriate for someone learning it for the first time. This must be a
FACTUAL explanation — accurate, verifiable technical content, not a metaphor
or guess.

Respond with ONLY a JSON object:
{{"concept": "{concept}", "content": "<the explanation>", "kind": "factual"}}
"""

ANALOGY_PROMPT = """Generate an analogy that helps explain "{concept}" to
someone unfamiliar with it. This is explicitly an ANALOGY — a comparison to
something more familiar, not a literal technical claim about {concept} itself.

Respond with ONLY a JSON object:
{{"concept": "{concept}", "content": "<the analogy>", "kind": "analogy"}}
"""

EXAMPLE_PROMPT = """Generate a concrete, factual example demonstrating
"{concept}" in practice (e.g. a short code snippet, a real-world usage
scenario). This must be FACTUAL — a real, accurate example, not speculation.

Respond with ONLY a JSON object:
{{"concept": "{concept}", "content": "<the example>", "kind": "factual"}}
"""


def explain_concept(llm: LLMProvider, concept: str) -> Explanation:
    """Section 28's explain_concept skill. Section 38: explanations are always
    tagged FACTUAL — if the model's own tagging disagrees, that's a defect the
    caller can detect (see app/evaluation/learning_eval.py's tagging check)."""
    if not concept or not concept.strip():
        raise ValueError("Concept must not be empty.")
    generator = RepairableGenerator(llm, Explanation)
    return generator.generate(EXPLAIN_PROMPT.format(concept=concept))


def generate_analogy(llm: LLMProvider, concept: str) -> Explanation:
    """Section 28's generate_analogy skill, tagged ANALOGY per Section 38 —
    never presented as a literal factual claim about the concept."""
    if not concept or not concept.strip():
        raise ValueError("Concept must not be empty.")
    generator = RepairableGenerator(llm, Explanation)
    return generator.generate(ANALOGY_PROMPT.format(concept=concept))


def generate_example(llm: LLMProvider, concept: str) -> Explanation:
    """Section 28's generate_example skill."""
    if not concept or not concept.strip():
        raise ValueError("Concept must not be empty.")
    generator = RepairableGenerator(llm, Explanation)
    return generator.generate(EXAMPLE_PROMPT.format(concept=concept))
