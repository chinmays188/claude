import time

from pydantic import BaseModel

from google import genai
from google.genai import types as genai_types

from app.config import Config, require_gemini_key
from app.providers.base import LLMProvider

# Real bug found while running the multi-agent coordinator live: the SDK's
# HttpOptions.timeout defaults to None (no request timeout at all), and it
# retries automatically on 429/5xx. Combined with this project's real
# free-tier rate limit (confirmed earlier this session:
# RESOURCE_EXHAUSTED, 15 req/min), a single generate() call could hang for
# minutes with no way for AgentBudget's timeout_seconds to interrupt it --
# that budget check only runs BETWEEN calls, never during one already in
# flight. A hard client-side timeout is the real fix: it turns an
# indefinite hang into a real, catchable exception.
DEFAULT_REQUEST_TIMEOUT_MS = 45_000


class GenerationUsage(BaseModel):
    """Real token counts from the Gemini API response, for cost attribution
    (app/observability/costs.py's CostTracker). Not part of the LLMProvider
    interface itself -- generate() must keep returning plain str since every
    caller (DomainRouter, agents, RepairableGenerator) and every test's
    ScriptedProvider assumes that. This is an additive method callers can
    opt into when they specifically want cost/usage visibility."""

    input_tokens: int
    output_tokens: int


class StreamingLatency(BaseModel):
    """Real TTFT (time to first token) vs. total generation latency --
    found missing while investigating 'LLM Fundamentals' and 'AI Cost &
    Latency Engineering' (both independently disclosed the same gap:
    'no TTFT/streaming measurement exists anywhere'). These are two
    genuinely different real numbers a caller cares about differently:
    TTFT is what makes an interactive UI feel responsive (the user sees
    SOMETHING quickly); total latency is what the real end-to-end cost/
    completion-time budget actually is. Measured with time.monotonic()
    around the real streaming SDK call, not estimated."""

    ttft_ms: float
    total_latency_ms: float
    chunk_count: int
    text: str


class GeminiProvider(LLMProvider):
    def __init__(
        self, model: str | None = None, track_usage: bool = False,
        request_timeout_ms: int = DEFAULT_REQUEST_TIMEOUT_MS,
        temperature: float | None = None, top_p: float | None = None,
        top_k: int | None = None, max_output_tokens: int | None = None,
    ):
        require_gemini_key()
        self._model = model or Config.GEMINI_MODEL
        self._client = genai.Client(
            api_key=Config.GEMINI_API_KEY,
            http_options=genai_types.HttpOptions(timeout=request_timeout_ms),
        )
        # Found missing while investigating "LLM Fundamentals" (criterion:
        # "understand... temperature and model parameters"): generate()
        # never exposed any real generation-config control at all --
        # every call used the SDK's own implicit defaults, with no way for
        # a caller to ask for more/less randomness. All default to None
        # (the SDK's own defaults), so every existing caller sees zero
        # behavior change unless it opts in.
        self._generation_config = genai_types.GenerateContentConfig(
            temperature=temperature, top_p=top_p, top_k=top_k, max_output_tokens=max_output_tokens,
        )
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
            config=self._generation_config,
        )
        if self._track_usage:
            self.usage_log.append(
                GenerationUsage(
                    input_tokens=response.usage_metadata.prompt_token_count or 0,
                    output_tokens=response.usage_metadata.candidates_token_count or 0,
                )
            )
        return response.text

    def generate_streaming(self, prompt: str) -> StreamingLatency:
        """Real streaming call, separate from generate() (which stays
        non-streaming -- every existing caller assumes generate() returns
        a plain str, so this is additive, not a replacement). Measures
        the REAL wall-clock gap between making the call and the first
        chunk arriving (TTFT) vs. the full stream completing (total
        latency) -- the two numbers both named-missing gaps asked for,
        from one real call, not simulated."""
        start = time.monotonic()
        first_chunk_at: float | None = None
        chunks: list[str] = []

        stream = self._client.models.generate_content_stream(
            model=self._model, contents=prompt, config=self._generation_config,
        )
        for chunk in stream:
            if first_chunk_at is None:
                first_chunk_at = time.monotonic()
            if chunk.text:
                chunks.append(chunk.text)

        end = time.monotonic()
        ttft_ms = (first_chunk_at - start) * 1000 if first_chunk_at is not None else 0.0
        total_latency_ms = (end - start) * 1000

        return StreamingLatency(
            ttft_ms=ttft_ms, total_latency_ms=total_latency_ms,
            chunk_count=len(chunks), text="".join(chunks),
        )

    @property
    def model_name(self) -> str:
        return self._model
