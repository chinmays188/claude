"""Real, local speech-activity detection via Silero VAD -- built for the
user's explicit ask: "Build a local-first voice AI project on my machine
... understand the architecture rather than just generate code."
Deliberately a separate module from app/multimodal/ (the existing
cloud-Gemini voice path): the whole point of this one is that NOTHING
leaves the machine and no API key is ever required.

Silero VAD's real model is tiny (~2MB, ONNX/JIT, downloaded once from
its own package data on first load_silero_vad() call, then cached
locally -- not from Hugging Face). It outputs a real speech probability
per audio chunk; get_speech_timestamps() turns that into real
start/end-second spans where actual speech was detected, so silence
(dead air, background noise with no speech) can be skipped before the
more expensive Whisper transcription step runs on it.
"""

from dataclasses import dataclass

import torch
from silero_vad import get_speech_timestamps, load_silero_vad

from app.voice_local.audio_io import load_wav_as_float_array

SILERO_SAMPLE_RATE = 16_000


@dataclass
class SpeechSegment:
    start_seconds: float
    end_seconds: float


class LocalVAD:
    """Loads the real Silero VAD model once (expensive-ish relative to
    its own tiny size, cheap in absolute terms -- a few hundred ms) and
    reuses it across calls, rather than reloading per detection."""

    def __init__(self):
        self._model = load_silero_vad()

    def detect_speech(self, audio_path: str) -> list[SpeechSegment]:
        """Real detection: loads the real audio file (resampled to
        Silero's required 16kHz mono), runs the real VAD model over it,
        and returns real speech segments in seconds. An empty list is a
        real, honest result (no speech detected), not an error."""
        audio = torch.from_numpy(load_wav_as_float_array(audio_path))
        timestamps = get_speech_timestamps(audio, self._model, sampling_rate=SILERO_SAMPLE_RATE, return_seconds=True)
        return [SpeechSegment(start_seconds=t["start"], end_seconds=t["end"]) for t in timestamps]
