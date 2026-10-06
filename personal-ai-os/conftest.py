import os

# Real, found issue while wiring the real SentenceTransformerEmbedding into
# app/voice/session.py's default construction (investigating "AI Memory"):
# running the full test suite segfaults with a libomp double-initialization
# conflict on macOS when both faiss (faiss-cpu, used by RAG/retrieval tests)
# and torch (used by sentence-transformers) load their own OpenMP runtime
# into the same process. This is the standard, documented workaround for
# exactly this known faiss-cpu/torch conflict -- set here, before any test
# module imports either library, rather than requiring every contributor to
# remember to export it manually before running pytest.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
