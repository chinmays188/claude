import httpx
import pytest

from app.providers.ollama_provider import OllamaProvider


def _ollama_reachable() -> bool:
    try:
        httpx.get("http://localhost:11434/api/version", timeout=2.0)
        return True
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(
    not _ollama_reachable(),
    reason="Ollama is not running locally (`brew services start ollama`) -- skipping real local-model tests.",
)


def test_generates_real_local_response():
    provider = OllamaProvider()

    result = provider.generate("Reply with only the word: pong")

    assert isinstance(result, str)
    assert len(result) > 0


def test_model_name_identifies_the_local_model():
    provider = OllamaProvider(model="llama3.2:1b")

    assert provider.model_name == "ollama/llama3.2:1b"
