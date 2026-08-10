from app.evaluation.grounding_eval import citation_quality, evaluate_grounding
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_fully_grounded_answer():
    llm = ScriptedProvider(
        [
            '{"grounded_claim_count": 2, "unsupported_claim_count": 0, '
            '"groundedness_score": 1.0, "citations": [{"claim": "RAG combines retrieval and generation", "chunk_id": "c1"}]}'
        ]
    )

    result = evaluate_grounding(llm, "RAG combines retrieval and generation.", {"c1": "RAG combines retrieval with generation."})

    assert result.groundedness_score == 1.0
    assert result.unsupported_claim_count == 0


def test_partially_ungrounded_answer():
    llm = ScriptedProvider(
        [
            '{"grounded_claim_count": 1, "unsupported_claim_count": 1, '
            '"groundedness_score": 0.5, "citations": [{"claim": "claim1", "chunk_id": "c1"}]}'
        ]
    )

    result = evaluate_grounding(llm, "some answer", {"c1": "evidence"})

    assert result.groundedness_score == 0.5
    assert result.unsupported_claim_count == 1


def test_citation_quality_all_valid():
    llm = ScriptedProvider(
        ['{"grounded_claim_count": 1, "unsupported_claim_count": 0, "groundedness_score": 1.0, '
         '"citations": [{"claim": "c", "chunk_id": "c1"}, {"claim": "c2", "chunk_id": "c2"}]}']
    )
    result = evaluate_grounding(llm, "answer", {"c1": "e1", "c2": "e2"})

    quality = citation_quality(result, valid_chunk_ids={"c1", "c2"})

    assert quality == 1.0


def test_citation_quality_with_hallucinated_chunk_id():
    llm = ScriptedProvider(
        ['{"grounded_claim_count": 1, "unsupported_claim_count": 0, "groundedness_score": 1.0, '
         '"citations": [{"claim": "c", "chunk_id": "c1"}, {"claim": "c2", "chunk_id": "does_not_exist"}]}']
    )
    result = evaluate_grounding(llm, "answer", {"c1": "e1"})

    quality = citation_quality(result, valid_chunk_ids={"c1"})

    assert quality == 0.5


def test_citation_quality_no_citations():
    llm = ScriptedProvider(
        ['{"grounded_claim_count": 0, "unsupported_claim_count": 0, "groundedness_score": 0.0, "citations": []}']
    )
    result = evaluate_grounding(llm, "answer", {})

    quality = citation_quality(result, valid_chunk_ids={"c1"})

    assert quality == 0.0
