from google import genai

from app.config import Config, require_gemini_key
from app.providers.base import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, model: str | None = None):
        require_gemini_key()
        self._model = model or Config.GEMINI_MODEL
        self._client = genai.Client(api_key=Config.GEMINI_API_KEY)

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        return response.text

    @property
    def model_name(self) -> str:
        return self._model
