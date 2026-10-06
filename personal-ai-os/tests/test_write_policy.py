from app.memory.write_policy import MemoryWritePolicy, is_duplicate, is_semantic_duplicate
from app.providers.base import LLMProvider
from tests.fakes.fake_summary_embedding import FakeSummaryEmbedding


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_worth_remembering_returns_candidate():
    llm = ScriptedProvider(
        [
            '{"should_remember": true, "type": "decision", "importance": 0.5, '
            '"summary": "Chose RAG over fine-tuning for the spec doc Q&A feature."}'
        ]
    )
    policy = MemoryWritePolicy(llm)

    candidate, requires_approval = policy.evaluate("We decided to use RAG.", existing_summaries=[])

    assert candidate is not None
    assert candidate.type.value == "decision"
    assert requires_approval is False


def test_not_worth_remembering_returns_none():
    llm = ScriptedProvider(
        ['{"should_remember": false, "type": null, "importance": 0.0, "summary": null}']
    )
    policy = MemoryWritePolicy(llm)

    candidate, requires_approval = policy.evaluate("What's the weather?", existing_summaries=[])

    assert candidate is None
    assert requires_approval is False


def test_below_importance_threshold_returns_none():
    llm = ScriptedProvider(
        ['{"should_remember": true, "type": "learning", "importance": 0.1, "summary": "minor detail"}']
    )
    policy = MemoryWritePolicy(llm, importance_threshold=0.3)

    candidate, requires_approval = policy.evaluate("some text", existing_summaries=[])

    assert candidate is None


def test_duplicate_summary_returns_none():
    llm = ScriptedProvider(
        ['{"should_remember": true, "type": "goal", "importance": 0.6, "summary": "Learn Docker in 30 days."}']
    )
    policy = MemoryWritePolicy(llm)

    candidate, requires_approval = policy.evaluate(
        "some text", existing_summaries=["Learn Docker in 30 days."]
    )

    assert candidate is None


def test_high_importance_requires_approval():
    llm = ScriptedProvider(
        ['{"should_remember": true, "type": "decision", "importance": 0.9, "summary": "Major career decision."}']
    )
    policy = MemoryWritePolicy(llm, approval_threshold=0.7)

    candidate, requires_approval = policy.evaluate("some text", existing_summaries=[])

    assert candidate is not None
    assert requires_approval is True


def test_is_duplicate_case_and_whitespace_insensitive():
    assert is_duplicate("  Learn Docker  ", ["learn docker"])
    assert not is_duplicate("Learn Kubernetes", ["learn docker"])


def test_is_duplicate_empty_existing_list():
    assert not is_duplicate("anything", [])


def test_is_semantic_duplicate_catches_a_real_paraphrase():
    embedding_model = FakeSummaryEmbedding()

    assert is_semantic_duplicate(
        embedding_model, "User wants to learn Docker within a month.",
        ["Learn Docker in 30 days."],
    )


def test_is_semantic_duplicate_does_not_flag_distinct_memories():
    embedding_model = FakeSummaryEmbedding()

    assert not is_semantic_duplicate(
        embedding_model, "Prefers dark mode in the dashboard UI.",
        ["Learn Docker in 30 days.", "Chose RAG over fine-tuning for the spec doc Q&A feature."],
    )


def test_is_semantic_duplicate_empty_existing_list():
    assert not is_semantic_duplicate(FakeSummaryEmbedding(), "anything", [])


def test_policy_without_embedding_model_only_catches_exact_duplicates():
    llm = ScriptedProvider(
        ['{"should_remember": true, "type": "goal", "importance": 0.6, '
         '"summary": "User wants to learn Docker within a month."}']
    )
    policy = MemoryWritePolicy(llm)  # no embedding_model given -- backward-compatible default

    candidate, _ = policy.evaluate("some text", existing_summaries=["Learn Docker in 30 days."])

    assert candidate is not None  # not caught -- exact-match only, as before this change


def test_policy_with_embedding_model_catches_semantic_duplicates():
    llm = ScriptedProvider(
        ['{"should_remember": true, "type": "goal", "importance": 0.6, '
         '"summary": "User wants to learn Docker within a month."}']
    )
    policy = MemoryWritePolicy(llm, embedding_model=FakeSummaryEmbedding())

    candidate, _ = policy.evaluate("some text", existing_summaries=["Learn Docker in 30 days."])

    assert candidate is None  # now caught as a real semantic duplicate


def test_policy_with_embedding_model_still_allows_distinct_memories():
    llm = ScriptedProvider(
        ['{"should_remember": true, "type": "preference", "importance": 0.6, '
         '"summary": "Prefers dark mode in the dashboard UI."}']
    )
    policy = MemoryWritePolicy(llm, embedding_model=FakeSummaryEmbedding())

    candidate, _ = policy.evaluate("some text", existing_summaries=["Learn Docker in 30 days."])

    assert candidate is not None
