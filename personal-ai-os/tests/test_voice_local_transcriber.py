from app.voice_local.transcriber import LocalTranscriber
from tests.fakes.real_audio import generate_real_test_wav


def test_transcribes_real_speech_correctly():
    """Real, live local transcription -- no mocking, no API key, no
    network call after the one-time model download. Same honesty
    standard as the project's existing Gemini-based multimodal tests:
    a real spoken sentence must come back as real matching text."""
    wav_path = generate_real_test_wav("The quick brown fox jumps over the lazy dog.")
    transcriber = LocalTranscriber()

    result = transcriber.transcribe(wav_path)

    assert "fox" in result.text.lower()
    assert "dog" in result.text.lower()
    assert result.language == "en"
    assert result.duration_seconds > 0
