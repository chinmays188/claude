"""Generates REAL memory-extraction examples for the dashboard, found
missing while breaking context/memory down further per the user's ask
about "how does memory extraction happens to derive meaningful
context."

classify_for_memory() (app/memory/write_policy.py) is a real LLM call
that decides whether a piece of conversation is memory-worthy, and if
so extracts type/importance/summary in the SAME call. This script runs
it live against the real Gemini API for a small set of real
conversation excerpts -- including a deliberate negative case (small
talk that should NOT be extracted), so the dashboard shows an honest
mix, not only successes.

Usage:
    PYTHONPATH=. python scripts/generate_memory_extraction_examples.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import require_gemini_key
from app.memory.write_policy import classify_for_memory
from app.providers.gemini_provider import GeminiProvider

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "memory_extraction_examples.json"

CONVERSATION_EXCERPTS = [
    "I work as a Product Manager at an online travel agency, focused on post-sales customer experience.",
    "I'd prefer if you kept answers short and used bullet points instead of long paragraphs.",
    "lol ok thanks",
    "I've decided to go with RAG instead of fine-tuning for this project, since fine-tuning would need way more data than I have.",
    "What's the weather like today?",
]


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()

    examples = []
    for text in CONVERSATION_EXCERPTS:
        candidate = classify_for_memory(llm, text)
        examples.append({
            "conversation_text": text,
            "candidate": {
                "should_remember": candidate.should_remember,
                "type": candidate.type.value if candidate.type else None,
                "importance": candidate.importance,
                "summary": candidate.summary,
            },
        })
        print(f"[{candidate.should_remember}] {text[:50]!r} -> {candidate.summary!r}")

    OUT_PATH.write_text(json.dumps(examples, indent=2))
    print(f"\nWrote real memory extraction examples to {OUT_PATH}")


if __name__ == "__main__":
    main()
