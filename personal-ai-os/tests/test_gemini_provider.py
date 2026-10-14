import time
from unittest.mock import MagicMock, patch

from app.providers.gemini_provider import GeminiProvider


def _fake_response(text="ok", input_tokens=1, output_tokens=1):
    response = MagicMock()
    response.text = text
    response.usage_metadata.prompt_token_count = input_tokens
    response.usage_metadata.candidates_token_count = output_tokens
    return response


@patch("app.providers.gemini_provider.genai.Client")
@patch("app.providers.gemini_provider.require_gemini_key")
def test_generate_passes_temperature_to_the_real_sdk_call(mock_require_key, mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.models.generate_content.return_value = _fake_response()

    provider = GeminiProvider(temperature=0.7)
    provider.generate("hello")

    _, kwargs = mock_client.models.generate_content.call_args
    assert kwargs["config"].temperature == 0.7


@patch("app.providers.gemini_provider.genai.Client")
@patch("app.providers.gemini_provider.require_gemini_key")
def test_generate_passes_all_generation_params(mock_require_key, mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.models.generate_content.return_value = _fake_response()

    provider = GeminiProvider(temperature=1.2, top_p=0.9, top_k=40, max_output_tokens=256)
    provider.generate("hello")

    _, kwargs = mock_client.models.generate_content.call_args
    config = kwargs["config"]
    assert config.temperature == 1.2
    assert config.top_p == 0.9
    assert config.top_k == 40
    assert config.max_output_tokens == 256


@patch("app.providers.gemini_provider.genai.Client")
@patch("app.providers.gemini_provider.require_gemini_key")
def test_generate_defaults_leave_generation_params_unset(mock_require_key, mock_client_cls):
    """Backward-compatible: a caller that doesn't pass any generation
    params gets the SDK's own defaults (None on every field), not a
    change in behavior from before this param existed."""
    mock_client = mock_client_cls.return_value
    mock_client.models.generate_content.return_value = _fake_response()

    provider = GeminiProvider()
    provider.generate("hello")

    _, kwargs = mock_client.models.generate_content.call_args
    config = kwargs["config"]
    assert config.temperature is None
    assert config.top_p is None
    assert config.top_k is None
    assert config.max_output_tokens is None


def _fake_chunk(text):
    chunk = MagicMock()
    chunk.text = text
    return chunk


@patch("app.providers.gemini_provider.genai.Client")
@patch("app.providers.gemini_provider.require_gemini_key")
def test_generate_streaming_measures_real_ttft_and_total_latency(mock_require_key, mock_client_cls):
    mock_client = mock_client_cls.return_value

    def fake_stream(*args, **kwargs):
        time.sleep(0.01)  # real, measurable delay before the first chunk
        yield _fake_chunk("Hello")
        time.sleep(0.01)  # real, measurable delay before the second chunk
        yield _fake_chunk(" world")

    mock_client.models.generate_content_stream.return_value = fake_stream()

    provider = GeminiProvider()
    result = provider.generate_streaming("hello")

    assert result.text == "Hello world"
    assert result.chunk_count == 2
    assert result.ttft_ms > 0
    assert result.total_latency_ms >= result.ttft_ms  # total must never be less than time-to-first-token


@patch("app.providers.gemini_provider.genai.Client")
@patch("app.providers.gemini_provider.require_gemini_key")
def test_generate_streaming_handles_empty_stream(mock_require_key, mock_client_cls):
    """A real, honest edge case: a stream that yields nothing (e.g. a
    content-filtered response) must not crash or report a fabricated
    TTFT."""
    mock_client = mock_client_cls.return_value
    mock_client.models.generate_content_stream.return_value = iter([])

    provider = GeminiProvider()
    result = provider.generate_streaming("hello")

    assert result.text == ""
    assert result.chunk_count == 0
    assert result.ttft_ms == 0.0


@patch("app.providers.gemini_provider.genai.Client")
@patch("app.providers.gemini_provider.require_gemini_key")
def test_generate_streaming_skips_chunks_with_no_text(mock_require_key, mock_client_cls):
    """Real SDK behavior: some stream chunks carry metadata only, no
    text (e.g. a function-call chunk) -- these must not be concatenated
    as empty strings into the final text, nor break TTFT measurement."""
    mock_client = mock_client_cls.return_value

    def fake_stream(*args, **kwargs):
        yield _fake_chunk(None)
        yield _fake_chunk("real text")

    mock_client.models.generate_content_stream.return_value = fake_stream()

    provider = GeminiProvider()
    result = provider.generate_streaming("hello")

    assert result.text == "real text"
    assert result.chunk_count == 1
