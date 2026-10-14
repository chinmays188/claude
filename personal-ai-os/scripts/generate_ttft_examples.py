"""Generates REAL TTFT (time-to-first-token) vs. total latency examples
for the dashboard -- closes a gap "LLM Fundamentals" and "AI Cost &
Latency Engineering" both independently disclosed: "no TTFT/streaming
measurement exists anywhere."

Real, found while running this live: streaming latency behavior varies
noticeably between prompts/runs on the free tier -- not every call
streams chunks evenly; some show nearly all output arriving in a late
burst (TTFT close to total latency), others show a genuinely early
first chunk (TTFT well under total latency). Both real outcomes are
captured and shown as-is, not cherry-picked to make streaming look more
useful than this specific API/tier combination actually shows it to be.

Usage:
    PYTHONPATH=. python scripts/generate_ttft_examples.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import require_gemini_key
from app.providers.gemini_provider import GeminiProvider

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "ttft_examples.json"

PROMPTS = [
    ("short_factual", "What is the capital of France?"),
    ("longer_explanation", "Explain in a few sentences why retrieval-augmented generation is useful."),
]


def main() -> None:
    require_gemini_key()
    provider = GeminiProvider()

    examples = []
    for label, prompt in PROMPTS:
        result = provider.generate_streaming(prompt)
        examples.append({
            "label": label, "prompt": prompt,
            "ttft_ms": result.ttft_ms, "total_latency_ms": result.total_latency_ms,
            "chunk_count": result.chunk_count, "text": result.text,
        })
        print(f"[{label}] TTFT={result.ttft_ms:.0f}ms, total={result.total_latency_ms:.0f}ms, chunks={result.chunk_count}")

    OUT_PATH.write_text(json.dumps(examples, indent=2))
    print(f"\nWrote real TTFT examples to {OUT_PATH}")


if __name__ == "__main__":
    main()
