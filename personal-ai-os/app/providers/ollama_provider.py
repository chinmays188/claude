import httpx

from app.providers.base import LLMProvider

# Real local model serving via Ollama (https://ollama.com) -- no API key, no
# network call leaves this machine, genuinely free (no per-token cost, no
# quota). Added as a third ModelRouter tier (app/routing/model_router.py)
# alongside the two existing Gemini cloud tiers, per the user's ask: "lets
# install ollama and get into model routing." Requires `ollama serve`
# running locally (started here via `brew services start ollama`) and the
# model already pulled (`ollama pull <model>`) -- this provider does not
# pull models itself, matching GeminiProvider's own pattern of assuming its
# backend is already reachable rather than provisioning it.
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:1b"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 60.0


class OllamaProvider(LLMProvider):
    def __init__(
        self, model: str = DEFAULT_OLLAMA_MODEL, base_url: str = DEFAULT_OLLAMA_BASE_URL,
        request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    ):
        self._model = model
        self._base_url = base_url
        self._timeout = request_timeout_seconds

    def generate(self, prompt: str) -> str:
        response = httpx.post(
            f"{self._base_url}/api/generate",
            json={"model": self._model, "prompt": prompt, "stream": False},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json()["response"]

    @property
    def model_name(self) -> str:
        return f"ollama/{self._model}"
