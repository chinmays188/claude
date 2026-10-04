import pytest

from app.agents.orchestrator import Orchestrator
from app.multimodal.base import MediaType, MultimodalProvider
from app.multimodal.multimodal_orchestrator import InputKind, MultimodalInput, MultimodalOrchestrator
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


class FakeMultimodalProvider(MultimodalProvider):
    """Deterministic stand-in -- no real Gemini call, records every real
    call it received so tests can assert the right prompt/media_type/
    mime_type reached it."""

    def __init__(self, canned_response: str):
        self._canned_response = canned_response
        self._model = "fake-multimodal-model"
        self.calls: list[tuple[str, bytes, MediaType, str]] = []

    def understand(self, prompt: str, media_bytes: bytes, media_type: MediaType, mime_type: str) -> str:
        self.calls.append((prompt, media_bytes, media_type, mime_type))
        return self._canned_response


def _simple_orchestrator_responses(answer: str) -> list[str]:
    return [
        '{"domains": [], "confidence": 0.9}',
        '{"task_type": "research", "confidence": 0.9}',
        f'{{"action": "final_answer", "answer": "{answer}"}}',
    ]


def test_text_input_bypasses_multimodal_provider_entirely():
    llm = ScriptedProvider(_simple_orchestrator_responses("RAG combines retrieval with generation."))
    multimodal = FakeMultimodalProvider("should never be used")
    orchestrator = MultimodalOrchestrator(Orchestrator(llm), multimodal)

    result = orchestrator.handle(MultimodalInput(kind=InputKind.TEXT, text="Explain RAG."))

    assert result.output == "RAG combines retrieval with generation."
    assert multimodal.calls == []
    assert orchestrator.last_conversion is None


def test_empty_text_raises():
    llm = ScriptedProvider([])
    orchestrator = MultimodalOrchestrator(Orchestrator(llm), FakeMultimodalProvider(""))

    with pytest.raises(ValueError):
        orchestrator.handle(MultimodalInput(kind=InputKind.TEXT, text="   "))


def test_image_input_converts_to_text_then_reaches_orchestrator():
    llm = ScriptedProvider(_simple_orchestrator_responses("The image shows a chart of quarterly revenue."))
    multimodal = FakeMultimodalProvider("A bar chart showing Q1-Q4 revenue growth.")
    orchestrator = MultimodalOrchestrator(Orchestrator(llm), multimodal)

    result = orchestrator.handle(
        MultimodalInput(kind=InputKind.IMAGE, media_bytes=b"fake-png-bytes", mime_type="image/png")
    )

    assert len(multimodal.calls) == 1
    prompt, media_bytes, media_type, mime_type = multimodal.calls[0]
    assert media_bytes == b"fake-png-bytes"
    assert media_type == MediaType.IMAGE
    assert mime_type == "image/png"
    assert result.output == "The image shows a chart of quarterly revenue."
    assert orchestrator.last_conversion.kind == InputKind.IMAGE
    assert orchestrator.last_conversion.extracted_text == "A bar chart showing Q1-Q4 revenue growth."


def test_pdf_input_uses_real_default_mime_type_when_not_given():
    llm = ScriptedProvider(_simple_orchestrator_responses("Summary provided."))
    multimodal = FakeMultimodalProvider("This document discusses Kubernetes.")
    orchestrator = MultimodalOrchestrator(Orchestrator(llm), multimodal)

    orchestrator.handle(MultimodalInput(kind=InputKind.PDF, media_bytes=b"fake-pdf-bytes"))

    _, _, media_type, mime_type = multimodal.calls[0]
    assert media_type == MediaType.PDF
    assert mime_type == "application/pdf"


def test_audio_input_is_transcribed_then_routed_like_any_text_request():
    llm = ScriptedProvider(_simple_orchestrator_responses("RAG combines retrieval with generation."))
    multimodal = FakeMultimodalProvider("What is RAG?")
    orchestrator = MultimodalOrchestrator(Orchestrator(llm), multimodal)

    result = orchestrator.handle(
        MultimodalInput(kind=InputKind.AUDIO, media_bytes=b"fake-wav-bytes", mime_type="audio/wav")
    )

    _, _, media_type, mime_type = multimodal.calls[0]
    assert media_type == MediaType.AUDIO
    assert mime_type == "audio/wav"
    assert orchestrator.last_conversion.extracted_text == "What is RAG?"
    assert result.output == "RAG combines retrieval with generation."


def test_media_without_bytes_raises():
    orchestrator = MultimodalOrchestrator(Orchestrator(ScriptedProvider([])), FakeMultimodalProvider(""))

    with pytest.raises(ValueError):
        orchestrator.handle(MultimodalInput(kind=InputKind.IMAGE))


def test_user_prompt_alongside_media_is_combined_with_the_real_extracted_text():
    # The combined (user_prompt + extracted text) wording happens to trip
    # might_need_multiple_agents()'s free word-count heuristic -- a real,
    # already-documented interaction (see app/conversation/session.py's
    # own tests) for injected-context prompts, not specific to this module.
    responses = (
        ['{"agents": [], "mode": "SINGLE", "reasoning": "ok"}']
        + _simple_orchestrator_responses("Here's a comparison.")
    )
    llm = ScriptedProvider(responses)
    multimodal = FakeMultimodalProvider("Revenue grew 20% in Q3.")
    orchestrator = MultimodalOrchestrator(Orchestrator(llm), multimodal)

    seen_prompts = []
    original_decide = llm.generate

    def recording_generate(prompt):
        seen_prompts.append(prompt)
        return original_decide(prompt)

    llm.generate = recording_generate

    orchestrator.handle(
        MultimodalInput(
            kind=InputKind.IMAGE, media_bytes=b"fake-png-bytes",
            user_prompt="How does this compare to last quarter?",
        )
    )

    # The combined text (user prompt + extracted content) must have
    # reached the real agent decision call, not just the raw extraction.
    agent_prompt = seen_prompts[-1]
    assert "How does this compare to last quarter?" in agent_prompt
    assert "Revenue grew 20% in Q3." in agent_prompt
