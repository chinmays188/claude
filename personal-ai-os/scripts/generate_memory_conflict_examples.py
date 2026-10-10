"""Generates REAL memory-conflict-resolution examples for the dashboard,
found missing while breaking context/memory down further per the
user's ask about "how conflicting info of the user is handled during
consolidation."

ConflictResolver.resolve() (app/memory/conflict_resolution.py) is a
real LLM call that judges whether new information genuinely
CONTRADICTS an existing memory, or is merely a restatement (SAME).
This script runs it live against the real Gemini API for a small set
of real existing-memory/new-information pairs -- including a
deliberate non-conflict case, so the dashboard shows the real
distinction, not only conflicts.

Usage:
    PYTHONPATH=. python scripts/generate_memory_conflict_examples.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import require_gemini_key
from app.memory.conflict_resolution import ConflictResolver
from app.memory.models import MemoryRecord, MemoryType
from app.providers.gemini_provider import GeminiProvider

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "memory_conflict_examples.json"

NOW = datetime.now(timezone.utc)

CASES = [
    # (existing_content, new_content, new_importance)
    ("Prefers dark mode for all interfaces.", "Actually, prefers light mode now.", 0.4),
    ("Wants to become an engineering manager within 2 years.", "No longer wants to become an engineering manager -- decided to stay as an IC.", 0.9),
    ("Prefers concise, bullet-point explanations.", "Likes when answers are kept short and use bullet points.", 0.5),
]


def _memory(content: str) -> MemoryRecord:
    return MemoryRecord(
        memory_id="existing", tenant_id="demo", user_id="demo", type=MemoryType.PREFERENCE,
        content=content, source="conversation", created_at=NOW, updated_at=NOW,
    )


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()
    resolver = ConflictResolver(llm, approval_threshold=0.7)

    examples = []
    for existing_content, new_content, new_importance in CASES:
        existing = _memory(existing_content)
        resolution = resolver.resolve(existing, new_content, new_importance)
        examples.append({
            "existing_content": existing_content,
            "new_content": new_content,
            "verdict": resolution.judgment.verdict.value,
            "reasoning": resolution.judgment.reasoning,
            "superseded": resolution.superseded,
            "requires_approval": resolution.requires_approval,
        })
        print(f"[{resolution.judgment.verdict.value}] {existing_content[:40]!r} vs {new_content[:40]!r}")

    OUT_PATH.write_text(json.dumps(examples, indent=2))
    print(f"\nWrote real memory conflict examples to {OUT_PATH}")


if __name__ == "__main__":
    main()
