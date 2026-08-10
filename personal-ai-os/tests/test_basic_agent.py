import pytest

from app.agents.basic_agent import AgentResponse, BasicAgent
from app.providers.fake_provider import FakeProvider


def test_normal_input_returns_valid_response():
    agent = BasicAgent(llm=FakeProvider(canned_response="RAG combines retrieval with generation."))

    result = agent.run("Explain RAG.")

    assert isinstance(result, AgentResponse)
    assert result.input == "Explain RAG."
    assert result.output != ""
    assert result.model == "fake-model"


def test_empty_input_raises_before_calling_llm():
    agent = BasicAgent(llm=FakeProvider())

    with pytest.raises(ValueError):
        agent.run("")


def test_whitespace_only_input_raises():
    agent = BasicAgent(llm=FakeProvider())

    with pytest.raises(ValueError):
        agent.run("   ")


def test_long_input_does_not_crash():
    agent = BasicAgent(llm=FakeProvider(canned_response="summary"))
    long_text = "word " * 5000

    result = agent.run(long_text)

    assert isinstance(result, AgentResponse)
    assert result.output == "summary"


def test_provider_failure_propagates():
    class FailingProvider(FakeProvider):
        def generate(self, prompt: str) -> str:
            raise RuntimeError("provider unavailable")

    agent = BasicAgent(llm=FailingProvider())

    with pytest.raises(RuntimeError):
        agent.run("Explain RAG.")
