from google import genai
from google.genai import types

from app.config import Config, require_gemini_key
from app.multimodal.base import MediaType, MultimodalProvider


class GeminiMultimodalProvider(MultimodalProvider):
    def __init__(self, model: str | None = None):
        require_gemini_key()
        self._model = model or Config.GEMINI_MODEL
        self._client = genai.Client(api_key=Config.GEMINI_API_KEY)

    def understand(self, prompt: str, media_bytes: bytes, media_type: MediaType, mime_type: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=[
                types.Part.from_bytes(data=media_bytes, mime_type=mime_type),
                prompt,
            ],
        )
        return response.text
