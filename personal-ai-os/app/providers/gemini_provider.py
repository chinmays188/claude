from pydantic import BaseModel

from google import genai

from app.config import Config, require_gemini_key
from app.providers.base import LLMProvider


class GenerationUsage(BaseModel):
    """Real token counts from the Gemini API response, for cost attribution
    (app/observability/costs.py's CostTracker). Not part of the LLMProvider
    interface itself -- generate() must keep returning plain str since every
    caller (DomainRouter, agents, RepairableGenerator) and every test's
    ScriptedProvider assumes that. This is an additive method callers can
    opt into when they specifically want cost/usage visibility."""

    input_tokens: int
    output_tokens: int


class GeminiProvider(LLMProvider):
    def __init__(self, model: str | None = None, track_usage: bool = False):
        require_gemini_key()
        self._model = model or Config.GEMINI_MODEL
        self._client = genai.Client(api_key=Config.GEMINI_API_KEY)
        # When enabled, every real generate() call made through this
        # instance appends its actual usage here -- no extra/duplicate LLM
        # calls, just capturing what the SDK already returns for calls that
        # happen anyway (e.g. DomainRouter's and ToolAgent's internal
        # RepairableGenerator calls, which only ever call generate()).
        # Off by default: existing callers (tests, other code) see zero
        # behavior change.
        self._track_usage = track_usage
        self.usage_log: list[GenerationUsage] = []

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        if self._track_usage:
            self.usage_log.append(
                GenerationUsage(
                    input_tokens=response.usage_metadata.prompt_token_count or 0,
                    output_tokens=response.usage_metadata.candidates_token_count or 0,
                )
            )
        return response.text

    @property
    def model_name(self) -> str:
        return self._model
