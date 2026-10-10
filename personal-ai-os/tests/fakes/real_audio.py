"""Real audio generation for tests, via macOS's built-in `say` (free,
local, no network) -- genuinely real speech audio, not a text string
pretending to be audio. Mirrors scripts/trace_multimodal.py's own
_generate_real_test_audio helper, factored out here so
tests/voice_local/* can reuse it without importing a script module."""

import subprocess
import tempfile
from pathlib import Path


def generate_real_test_wav(text: str) -> str:
    """Returns a real, local filesystem path to a real 16-bit PCM WAV
    file containing real synthesized speech saying `text`. Falls back
    with a clear skip on non-macOS (no `say`/`afconvert`)."""
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as aiff_f:
        aiff_path = aiff_f.name
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_f:
        wav_path = wav_f.name

    subprocess.run(["say", "-o", aiff_path, text], check=True)
    subprocess.run(["afconvert", aiff_path, wav_path, "-d", "LEI16", "-f", "WAVE"], check=True)
    Path(aiff_path).unlink(missing_ok=True)
    return wav_path
