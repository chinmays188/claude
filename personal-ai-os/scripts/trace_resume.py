"""Trace the real Career domain's resume-optimization flow against your own
resume PDF and a job description, using real embeddings + real Gemini calls.

This is app/domains/career/resume_optimization.py's actual, tested flow:
retrieve grounded achievement excerpts from YOUR resume via RAG, match them
to a job description, and suggest changes -- never inventing an achievement
not present in your resume (Section 10 rule 6, checked here for real via
check_resume_suggestions_grounded).

Nothing here is written to the repo, seeded into any store, or committed --
your resume text and the JD only exist in this process's memory for the
duration of the run.

Usage:
    pdftotext /path/to/resume.pdf - > /tmp/resume.txt
    PYTHONPATH=. python scripts/trace_resume.py /tmp/resume.txt /path/to/jd.txt

    # or pass the JD text directly:
    PYTHONPATH=. python scripts/trace_resume.py /tmp/resume.txt --jd-text "..."
"""

import argparse
import sys
from datetime import datetime, timezone

from app.config import require_gemini_key
from app.domains.career.resume_optimization import (
    check_resume_suggestions_grounded,
    optimize_resume,
)
from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.gemini_provider import GeminiProvider
from app.retrieval.chunking import chunk_document
from app.retrieval.document import Document
from app.retrieval.embeddings import SentenceTransformerEmbedding
from app.retrieval.vector_search import VectorStore

REQUESTER_ID = "cli_user"
TENANT_ID = "cli_session"
DOCUMENT_ID = "resume_cli"


def _print_header(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def build_retriever(resume_text: str) -> SecureRetriever:
    """Real embedding model, real FAISS index, real chunking -- the same
    pipeline app/retrieval/* uses everywhere else, not a test double."""
    now = datetime.now(timezone.utc)
    document = Document(id=DOCUMENT_ID, text=resume_text, source="resume", created_at=now, updated_at=now)
    chunks = chunk_document(document, chunk_size=150, overlap=30)

    print(f"Chunked resume into {len(chunks)} chunk(s) (150 words, 30-word overlap).")

    embedding_model = SentenceTransformerEmbedding()
    store = VectorStore(embedding_model)
    store.add(chunks)

    metadata = PersonalDocumentMetadata(
        document_id=DOCUMENT_ID, source="resume", title="Resume (CLI trace)",
        created_at=now, updated_at=now, category="career",
        sensitivity=Sensitivity.PERSONAL, owner_id=REQUESTER_ID, tenant_id=TENANT_ID,
    )
    return SecureRetriever(store, {DOCUMENT_ID: metadata})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("resume_text_file", help="Path to your resume as plain text (use pdftotext to extract it first).")
    parser.add_argument("jd_file", nargs="?", help="Path to the job description as plain text.")
    parser.add_argument("--jd-text", help="Job description text directly, instead of a file.")
    args = parser.parse_args()

    if not args.jd_file and not args.jd_text:
        parser.error("Provide either a jd_file path or --jd-text.")

    resume_text = open(args.resume_text_file).read()
    jd_text = open(args.jd_file).read() if args.jd_file else args.jd_text

    if not resume_text.strip():
        print("Resume text file is empty -- did pdftotext extraction actually produce text?", file=sys.stderr)
        sys.exit(1)

    require_gemini_key()
    llm = GeminiProvider()

    _print_header("1. INDEXING (real embeddings, real FAISS)")
    retriever = build_retriever(resume_text)

    _print_header("2. RETRIEVAL + OPTIMIZATION (real Gemini call)")
    outcome = optimize_resume(
        llm, jd_text, retriever, requester_id=REQUESTER_ID, requester_tenant_id=TENANT_ID
    )

    print(f"Retrieved {len(outcome.valid_excerpt_ids)} grounded excerpt(s) from your resume.")
    print(f"\nMissing keywords:\n" + "\n".join(f"  - {k}" for k in outcome.result.missing_keywords))
    print(f"\nSuggested bullet changes:")
    for change, gid in zip(
        outcome.result.suggested_bullet_changes,
        outcome.result.grounding_achievement_ids or [""] * len(outcome.result.suggested_bullet_changes),
    ):
        print(f"  - {change}  [grounded in: {gid or '?'}]")

    _print_header("3. FACTUALITY CHECK (Section 10 rule 6)")
    is_grounded = check_resume_suggestions_grounded(outcome.result, set(outcome.valid_excerpt_ids))
    print(f"All suggestions traceable to a real retrieved excerpt: {is_grounded}")
    if not is_grounded:
        print("WARNING: at least one suggestion cited an excerpt id that was never retrieved -- "
              "this would be a real grounding failure, not expected behavior.")


if __name__ == "__main__":
    main()
