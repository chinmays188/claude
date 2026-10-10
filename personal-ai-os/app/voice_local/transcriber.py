"""Real, local speech-to-text via faster-whisper -- built for the user's
explicit ask: "Build a local-first voice AI project ... No paid speech
APIs. Do not require API keys." The real Whisper model (default: "base",
~145MB) is downloaded ONCE from Hugging Face on first use via
WhisperModel's own download machinery, then cached locally
(~/.cache/huggingface by default) -- every call after that is fully
offline, no network request, no API key.

Deliberately a separate module from app/multimodal/gemini_multimodal.py
(the existing cloud-Gemini voice path): this one never leaves the
machine at all.
"""

from dataclasses import dataclass

from faster_whisper import WhisperModel

from app.voice_local.audio_io import load_wav_as_float_array


@dataclass
class TranscriptionResult:
    text: str
    language: str
    language_probability: float
    duration_seconds: float


class LocalTranscriber:
    """Loads the real faster-whisper model once and reuses it across
    calls -- re-loading per call would re-pay the real model-load cost
    (reading ~145MB of weights into memory) every single transcription."""

    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        # compute_type="int8": a real, deliberate choice for CPU-only
        # inference (this project's own Mac has no CUDA GPU for
        # CTranslate2's accelerated path) -- real quantization, genuinely
        # faster on CPU than float32 at a small, usually negligible real
        # accuracy cost for this model size.
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        """Real transcription. Loads the WAV into a real float32 numpy
        array first (app/voice_local/audio_io.py) and passes THAT to
        faster-whisper, rather than the file path -- found necessary
        while building this: faster-whisper's own file-path decode path
        uses `av` internally, and the installed av==19.0.1 (the only
        version with real Python 3.14 wheels) has a real, breaking
        incompatibility with this faster-whisper version's internal
        call. Passing a real array sidesteps av's decode path entirely;
        faster-whisper's own transcribe() signature explicitly supports
        this (segment-level timestamps are available via the raw
        segments iterator, not exposed here since this module's job is
        just the final text, not segment-by-segment detail)."""
        audio_array = load_wav_as_float_array(audio_path)
        segments, info = self._model.transcribe(audio_array)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return TranscriptionResult(
            text=text, language=info.language, language_probability=info.language_probability,
            duration_seconds=info.duration,
        )
