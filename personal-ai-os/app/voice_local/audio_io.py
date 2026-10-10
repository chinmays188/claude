"""Real, dependency-free WAV loading shared by vad.py and transcriber.py.

Found necessary while building this: faster-whisper's own file-path decode
path uses the `av` library internally, and the installed av==19.0.1 (the
only version with real Python 3.14 wheels at the time of building this)
has a real, breaking API incompatibility with faster-whisper==1.2.1's
internal call (`av.open(..., metadata_errors=...)`, a kwarg av 19.0.1
removed). Rather than pin to an older av version (risking its own
compatibility issues on Python 3.14), this project passes a raw numpy
array directly to transcribe() instead, bypassing av's decode path
entirely -- faster-whisper's own transcribe() signature explicitly
supports this.

Only plain 16-bit PCM WAV is supported (what this project's own
audio_input/file_uploader widgets produce) -- not a general-purpose
audio decoder.
"""

import wave

import numpy as np

TARGET_SAMPLE_RATE = 16_000


def load_wav_as_float_array(audio_path: str, target_sample_rate: int = TARGET_SAMPLE_RATE) -> np.ndarray:
    with wave.open(audio_path, "rb") as w:
        n_channels = w.getnchannels()
        sample_rate = w.getframerate()
        sample_width = w.getsampwidth()
        raw = w.readframes(w.getnframes())

    if sample_width != 2:
        raise ValueError(f"Only 16-bit PCM WAV is supported (got {sample_width * 8}-bit) -- '{audio_path}'.")

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)  # real downmix to mono

    if sample_rate != target_sample_rate:
        from scipy.signal import resample

        target_length = int(len(samples) * target_sample_rate / sample_rate)
        samples = resample(samples, target_length).astype(np.float32)

    return samples
