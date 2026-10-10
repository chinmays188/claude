"""Generates REAL screenshot/table multimodal examples for the dashboard,
found missing while investigating "Multimodal AI" (disclosed gap:
"screenshots and tables aren't separately exercised"). The existing
image test case (multimodal_examples.json's "image" entry) is a single
line of rendered text -- a distinct, genuinely harder extraction task:
a real screenshot (multiple labeled UI fields, spatial layout) and a
real data table (rows/columns, each value tied to its header), both
rendered locally, fed through the real GeminiMultimodalProvider +
MultimodalOrchestrator, same as every other real input type.

Usage:
    PYTHONPATH=. python scripts/generate_multimodal_screenshot_table_examples.py
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
from scripts.trace_multimodal import _generate_real_test_screenshot, _generate_real_test_table_image

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "multimodal_screenshot_table_examples.json"
ASSETS_DIR = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "multimodal_assets"


def _result_to_dict(result) -> dict:
    if isinstance(result, ClarificationNeeded):
        return {"outcome": "clarification_needed", "message": result.message}
    return {"outcome": "answered", "output": result.output, "agent": result.agent, "tool_calls": result.tool_calls}


def run_example(
    kind: str, orchestrator: MultimodalOrchestrator, multimodal_input: MultimodalInput,
    asset_filename: str | None = None,
) -> dict:
    """asset_filename, when given, saves the real source image bytes to
    ASSETS_DIR so the dashboard can render the actual screenshot/table
    image that was fed into extraction, not just the extracted text."""
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

    screenshot_bytes = _generate_real_test_screenshot()
    examples["screenshot"] = run_example(
        "screenshot",
        orchestrator,
        MultimodalInput(
            kind=InputKind.IMAGE, media_bytes=screenshot_bytes, mime_type="image/png",
            user_prompt="What username is shown, and are notifications enabled or disabled?",
        ),
        asset_filename="screenshot.png",
    )
    print(f"[screenshot] extracted: {examples['screenshot']['extracted_text'][:150]!r}")
    print(f"[screenshot] {examples['screenshot']['result']}")

    table_bytes = _generate_real_test_table_image()
    examples["table"] = run_example(
        "table",
        orchestrator,
        MultimodalInput(
            kind=InputKind.IMAGE, media_bytes=table_bytes, mime_type="image/png",
            user_prompt="Which quarter had negative growth, and what was its revenue?",
        ),
        asset_filename="table.png",
    )
    print(f"[table] extracted: {examples['table']['extracted_text'][:150]!r}")
    print(f"[table] {examples['table']['result']}")

    OUT_PATH.write_text(json.dumps(examples, indent=2))
    print(f"\nWrote real screenshot/table multimodal examples to {OUT_PATH}")


if __name__ == "__main__":
    main()
