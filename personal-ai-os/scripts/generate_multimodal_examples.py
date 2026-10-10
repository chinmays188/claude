"""Generates REAL multimodal examples for the dashboard, run live once
and committed as app/dashboard_ui/multimodal_examples.json -- same
pattern as every other *_examples.json in this project (the dashboard
never makes a live LLM call itself).

Reuses scripts/trace_multimodal.py's exact 4 real demos -- text, image,
PDF, and voice (audio) -- but captures each real result as structured
JSON instead of print statements.

Usage:
    PYTHONPATH=. python scripts/generate_multimodal_examples.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.orchestrator import ClarificationNeeded, Orchestrator
from app.config import require_gemini_key
from app.multimodal.gemini_multimodal import GeminiMultimodalProvider
from app.multimodal.multimodal_orchestrator import InputKind, MultimodalInput, MultimodalOrchestrator
from app.providers.gemini_provider import GeminiProvider
from scripts.trace_multimodal import _MINIMAL_PDF, _generate_real_test_audio, _generate_real_test_image

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "multimodal_examples.json"
ASSETS_DIR = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "multimodal_assets"


def _result_to_dict(result) -> dict:
    if isinstance(result, ClarificationNeeded):
        return {"outcome": "clarification_needed", "message": result.message}
    return {"outcome": "answered", "output": result.output, "agent": result.agent, "tool_calls": result.tool_calls}


def run_example(
    kind: str, orchestrator: MultimodalOrchestrator, multimodal_input: MultimodalInput,
    asset_filename: str | None = None,
) -> dict:
    """asset_filename, when given, saves multimodal_input.media_bytes to
    ASSETS_DIR so the dashboard can render the REAL file that was fed into
    extraction -- found missing while investigating the 'Multimodal AI'
    gap further: the dashboard only ever showed the extracted TEXT, never
    the source image/PDF itself, even though the bytes already exist
    right here before being discarded."""
    result = orchestrator.handle(multimodal_input)
    conversion = orchestrator.last_conversion

    asset_path = None
    if asset_filename and multimodal_input.media_bytes:
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        (ASSETS_DIR / asset_filename).write_bytes(multimodal_input.media_bytes)
        asset_path = asset_filename

    return {
        "kind": kind,
        "extracted_text": conversion.extracted_text if conversion else None,
        "multimodal_model": conversion.model_used if conversion else None,
        "result": _result_to_dict(result),
        "asset_path": asset_path,
    }


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()
    multimodal_provider = GeminiMultimodalProvider()
    orchestrator = MultimodalOrchestrator(Orchestrator(llm), multimodal_provider)

    examples = {}

    examples["text"] = run_example(
        "text", orchestrator, MultimodalInput(kind=InputKind.TEXT, text="What is RAG?")
    )
    print(f"[text] {examples['text']['result']['outcome']}")

    image_bytes = _generate_real_test_image()
    examples["image"] = run_example(
        "image", orchestrator,
        MultimodalInput(
            kind=InputKind.IMAGE, media_bytes=image_bytes, mime_type="image/png",
            user_prompt="Is this good or bad news?",
        ),
        asset_filename="image.png",
    )
    print(f"[image] {examples['image']['result']['outcome']}")

    examples["pdf"] = run_example(
        "pdf", orchestrator,
        MultimodalInput(kind=InputKind.PDF, media_bytes=_MINIMAL_PDF, mime_type="application/pdf"),
        asset_filename="pdf.pdf",
    )
    print(f"[pdf] {examples['pdf']['result']['outcome']}")

    audio_bytes = _generate_real_test_audio("What is the difference between RAG and fine tuning?")
    examples["audio"] = run_example(
        "audio", orchestrator,
        MultimodalInput(kind=InputKind.AUDIO, media_bytes=audio_bytes, mime_type="audio/wav"),
    )
    print(f"[audio] {examples['audio']['result']['outcome']}")

    OUT_PATH.write_text(json.dumps(examples, indent=2))
    print(f"\nWrote real multimodal examples to {OUT_PATH}")


if __name__ == "__main__":
    main()
