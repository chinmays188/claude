from app.domains.pm.models import FeedbackIntelligenceResult
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

FEEDBACK_PROMPT = """Analyze this raw customer/stakeholder feedback. Cluster it
into themes, estimate frequency and severity, and identify trends. Base
frequency/severity ONLY on what's actually present in the feedback below — do
not invent customer statements or data not present here (Section 38: never
fabricate customer data).

Raw feedback (one item per line):
{feedback_items}

Respond with ONLY a JSON object:
{{
  "top_themes": [{{"theme": "<name>", "frequency": <int>, "severity": <0.0-1.0>, "customer_impact": "<description>", "trend": "emerging" | "declining" | "stable"}}],
  "emerging_themes": ["<theme name>"],
  "declining_themes": ["<theme name>"],
  "critical_issues": ["<specific critical issue>"],
  "recommended_actions": ["<specific action>"]
}}
"""


def analyze_feedback(llm: LLMProvider, feedback_items: list[str]) -> FeedbackIntelligenceResult:
    """Section 15's pipeline: raw feedback -> intent extraction -> theme
    clustering -> frequency/severity/impact -> trend detection -> insight.
    Collapsed into one structured-output call rather than separate stages,
    since each stage's output (intent, cluster assignment) is an intermediate
    the schema doesn't need to expose separately."""
    if not feedback_items:
        raise ValueError("feedback_items must not be empty.")

    joined = "\n".join(f"- {item}" for item in feedback_items)
    generator = RepairableGenerator(llm, FeedbackIntelligenceResult)
    return generator.generate(FEEDBACK_PROMPT.format(feedback_items=joined))
