from app.domains.cross_domain.weekly_review import WeeklyReviewSources, generate_weekly_review
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_generate_weekly_review_returns_all_sections():
    llm = ScriptedProvider(
        ['{"what_happened": "Shipped the refund flow.", "accomplishments": ["Shipped refund flow"], '
         '"changes": ["New teammate joined"], "behind": ["Docs not updated"], '
         '"requires_attention": ["Support backlog growing"], "decisions_made": ["Chose RAG over fine-tuning"], '
         '"next_week": ["Finish docs"]}']
    )

    review = generate_weekly_review(llm, WeeklyReviewSources(github="Merged PR #12: refund flow."))

    assert review.what_happened == "Shipped the refund flow."
    assert "Shipped refund flow" in review.accomplishments
    assert "Finish docs" in review.next_week


def test_generate_weekly_review_defaults_when_no_sources_given():
    llm = ScriptedProvider(
        ['{"what_happened": "No significant activity this week.", "accomplishments": [], "changes": [], '
         '"behind": [], "requires_attention": [], "decisions_made": [], "next_week": []}']
    )

    review = generate_weekly_review(llm, WeeklyReviewSources())

    assert review.what_happened == "No significant activity this week."
