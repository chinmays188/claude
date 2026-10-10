import wave

import numpy as np
import pytest

from app.voice_local.audio_io import load_wav_as_float_array
from tests.fakes.real_audio import generate_real_test_wav


def _write_silent_wav(path: str, duration_seconds: float = 1.0, sample_rate: int = 16_000, n_channels: int = 1) -> None:
    n_samples = int(duration_seconds * sample_rate)
    silence = np.zeros(n_samples * n_channels, dtype=np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(n_channels)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(silence.tobytes())


def test_loads_real_mono_wav_at_target_rate(tmp_path):
    path = str(tmp_path / "test.wav")
    _write_silent_wav(path, sample_rate=16_000)

    array = load_wav_as_float_array(path, target_sample_rate=16_000)

    assert array.dtype == np.float32
    assert len(array) == 16_000


def test_resamples_when_source_rate_differs(tmp_path):
    path = str(tmp_path / "test.wav")
    _write_silent_wav(path, duration_seconds=1.0, sample_rate=22_050)

    array = load_wav_as_float_array(path, target_sample_rate=16_000)

    # Real resample: 22050Hz * 1s -> 16000Hz * 1s, allow rounding slack
    assert abs(len(array) - 16_000) < 10


def test_downmixes_stereo_to_mono(tmp_path):
    path = str(tmp_path / "test.wav")
    _write_silent_wav(path, sample_rate=16_000, n_channels=2)

    array = load_wav_as_float_array(path, target_sample_rate=16_000)

    assert array.ndim == 1  # real downmix happened, not left as interleaved stereo


def test_rejects_non_16_bit_wav(tmp_path):
    path = str(tmp_path / "test.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)  # 8-bit, not supported
        w.setframerate(16_000)
        w.writeframes(bytes(100))

    with pytest.raises(ValueError):
        load_wav_as_float_array(path)


def test_loads_a_real_say_generated_wav():
    """Real, live audio -- not synthetic silence -- generated via macOS's
    free, local `say` command."""
    wav_path = generate_real_test_wav("Testing real audio loading.")

    array = load_wav_as_float_array(wav_path)

    assert len(array) > 0
    assert array.dtype == np.float32
