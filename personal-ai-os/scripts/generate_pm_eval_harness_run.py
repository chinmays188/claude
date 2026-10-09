"""Runs the real PM golden set (evals/pm/*.json) through the real live
grading harness (pm_golden_runner.py) against a real, synthetic roadmap
fixture, found missing while investigating "AI Evaluation" (disclosed
gap: domain-specific golden sets have no live grading harness). Same
pattern as generate_career_eval_harness_run.py.

Usage:
    PYTHONPATH=. python scripts/generate_pm_eval_harness_run.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import require_gemini_key
from app.evaluation.domain_golden import load_domain_cases
from app.evaluation.pm_golden_runner import run_pm_golden_suite
from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.gemini_provider import GeminiProvider
from app.retrieval.document import Chunk
from app.retrieval.embeddings import SentenceTransformerEmbedding
from app.retrieval.vector_search import VectorStore

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "pm_eval_harness_run.json"
REQUESTER_ID = "alice"
REQUESTER_TENANT_ID = "t1"
NOW = datetime.now(timezone.utc)

# Real, synthetic roadmap/decision documents -- not real company data, same
# convention as every other fixture in this project.
ROADMAP_DOCS = [
    ("roadmap1", "Q3 roadmap: automated refund approval for amounts under $50 is already planned and prioritized."),
    ("decision1", "Decision log: the team chose a deterministic rule engine over an LLM for simple refund approval to avoid unnecessary complexity."),
    ("feedback1", "Prior customer feedback: refund turnaround time is the #1 complaint across support tickets this quarter."),
]


def build_retriever() -> SecureRetriever:
    store = VectorStore(SentenceTransformerEmbedding())
    metadata = {}
    for doc_id, text in ROADMAP_DOCS:
        store.add([Chunk(id=f"{doc_id}::c0", document_id=doc_id, text=text, source="roadmap", created_at=NOW, updated_at=NOW, chunk_index=0)])
        metadata[doc_id] = PersonalDocumentMetadata(
            document_id=doc_id, source="roadmap", title="Roadmap & Decisions", created_at=NOW, updated_at=NOW,
            owner_id=REQUESTER_ID, tenant_id=REQUESTER_TENANT_ID, sensitivity=Sensitivity.PERSONAL,
        )
    return SecureRetriever(store, metadata)


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()
    retriever = build_retriever()

    cases = load_domain_cases("pm")
    results = run_pm_golden_suite(llm, retriever, REQUESTER_ID, REQUESTER_TENANT_ID, cases)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.case_id} ({r.category}) -- {r.reason}")

    pass_rate = sum(1 for r in results if r.passed) / len(results) if results else 0.0
    print(f"\nPass rate: {pass_rate:.0%} ({sum(1 for r in results if r.passed)}/{len(results)})")

    out = {
        "domain": "pm",
        "results": [r.model_dump() for r in results],
        "pass_rate": pass_rate,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote real PM eval harness run to {OUT_PATH}")


if __name__ == "__main__":
    main()
