from app.voice_local.vad import LocalVAD, SpeechSegment
from tests.fakes.real_audio import generate_real_test_wav


def test_detects_speech_in_a_real_spoken_clip():
    wav_path = generate_real_test_wav("This sentence contains real detectable speech.")
    vad = LocalVAD()

    segments = vad.detect_speech(wav_path)

    assert len(segments) >= 1
    assert isinstance(segments[0], SpeechSegment)
    assert segments[0].end_seconds > segments[0].start_seconds


def test_returns_empty_list_for_real_silence(tmp_path):
    import wave

    import numpy as np

    path = str(tmp_path / "silence.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16_000)
        w.writeframes(np.zeros(16_000 * 2, dtype=np.int16).tobytes())  # 2s of real silence

    vad = LocalVAD()
    segments = vad.detect_speech(path)

    assert segments == []  # a real, honest empty result, not an error
