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
