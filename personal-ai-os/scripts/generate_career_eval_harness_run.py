"""Runs the real career golden set (evals/career/*.json) through the real
live grading harness (career_golden_runner.py) against the real,
synthetic achievement fixtures, found missing while investigating
"AI Evaluation" (disclosed gap: domain-specific golden sets have no
live grading harness).

Usage:
    PYTHONPATH=. python scripts/generate_career_eval_harness_run.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import require_gemini_key
from app.evaluation.career_golden_runner import run_career_golden_suite
from app.evaluation.domain_golden import load_domain_cases
from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.gemini_provider import GeminiProvider
from app.retrieval.document import Chunk
from app.retrieval.vector_search import VectorStore
from app.retrieval.embeddings import SentenceTransformerEmbedding
from tests.fakes.example_resume import EXAMPLE_ACHIEVEMENTS

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "career_eval_harness_run.json"
REQUESTER_ID = "alice"
REQUESTER_TENANT_ID = "t1"
NOW = datetime.now(timezone.utc)


def build_retriever() -> SecureRetriever:
    store = VectorStore(SentenceTransformerEmbedding())
    metadata = {}
    for achv_id, text in EXAMPLE_ACHIEVEMENTS:
        store.add([Chunk(id=f"{achv_id}::c0", document_id=achv_id, text=text, source="resume", created_at=NOW, updated_at=NOW, chunk_index=0)])
        metadata[achv_id] = PersonalDocumentMetadata(
            document_id=achv_id, source="resume", title="Achievements", created_at=NOW, updated_at=NOW,
            owner_id=REQUESTER_ID, tenant_id=REQUESTER_TENANT_ID, sensitivity=Sensitivity.PERSONAL,
        )
    return SecureRetriever(store, metadata)


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()
    retriever = build_retriever()

    cases = load_domain_cases("career")
    results = run_career_golden_suite(llm, retriever, REQUESTER_ID, REQUESTER_TENANT_ID, cases)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.case_id} ({r.category}) -- {r.reason}")

    pass_rate = sum(1 for r in results if r.passed) / len(results) if results else 0.0
    print(f"\nPass rate: {pass_rate:.0%} ({sum(1 for r in results if r.passed)}/{len(results)})")

    out = {
        "domain": "career",
        "results": [r.model_dump() for r in results],
        "pass_rate": pass_rate,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote real career eval harness run to {OUT_PATH}")


if __name__ == "__main__":
    main()
