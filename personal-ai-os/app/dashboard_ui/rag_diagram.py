"""Mermaid source for the RAG-specific architecture diagram shown on the
dashboard's RAG page. Every box/edge traces to real code, verified by
reading it directly:

  chunking (app/retrieval/chunking.py) -> embeddings
  (app/retrieval/embeddings.py, real SentenceTransformerEmbedding) ->
  VectorStore (real FAISS) + KeywordSearch (real BM25) -> HybridSearch
  (real reciprocal rank fusion) -> CrossEncoderReranker (real
  cross-encoder) -> ContextBuilder (real priority-based compression) ->
  LLM generation (PersonalRagPipeline) -> citations -> evaluation
  (evaluate_grounding, citation_quality, evaluate_retrieval).

Built after the user asked for "an entire RAG focused architecture
diagram showing the journey from input -> retrieve -> generate -> output."

HONEST GAP, checked directly in specs/personal_rag.md's own "Non-goals"
section: hybrid search + reranking are real, independently-tested
components, but are NOT actually wired into PersonalRagPipeline (the real
production RAG pipeline) yet -- SecureRetriever currently wraps plain
vector search only. The diagram below shows both the real hybrid+rerank
path (as components that genuinely exist and work) AND marks the actual
production path with a dashed line to make this gap visible, not implied
to already be connected.
"""

RAG_DIAGRAM = r"""
flowchart TB
    INPUT["Input document(s)\n(pasted text, e.g. a resume, notes, JD)"]
    QUERY["User query\n(what you're asking about the documents)"]

    INPUT --> CHUNK["chunk_document()\nsplits by whitespace-separated words\n(word count as a token proxy)\nchunk_size=150, overlap=30 (typical)"]

    CHUNK --> EMBED["SentenceTransformerEmbedding\nreal all-MiniLM-L6-v2 model\nreal 384-dim vectors"]

    EMBED --> VECSTORE["VectorStore\nreal FAISS IndexFlatL2"]
    CHUNK --> BM25["KeywordSearch\nreal BM25Okapi (rank_bm25)\nlexical/keyword scoring"]

    QUERY --> VECSEARCH["VectorStore.search(query)\nembeds the query, L2 distance\nto every chunk vector"]
    QUERY --> BM25SEARCH["KeywordSearch.search(query)\nBM25 score per chunk"]
    VECSTORE --> VECSEARCH
    BM25 --> BM25SEARCH

    VECSEARCH --> FUSION["reciprocal_rank_fusion()\nmerges both ranked lists by 1/(k+rank)\n-- avoids comparing incompatible\nscore scales (L2 distance vs BM25)\n⚠️ NOT wired into PersonalRagPipeline yet"]
    BM25SEARCH --> FUSION

    FUSION --> RERANK["CrossEncoderReranker\nreal cross-encoder/ms-marco-MiniLM-L-6-v2\nscores each (query, chunk) pair directly --\nmore accurate than embedding similarity alone\n⚠️ NOT wired into PersonalRagPipeline yet"]

    RERANK -.->|"real, tested, independently\nrunnable -- but not this edge\nin production today"| CONTEXTBUILD["ContextBuilder\nreal priority-based compression --\ndrops LOWEST-priority sections first\nwhen over a token budget, never\nblindly truncates"]

    VECSEARCH ==>|"ACTUAL production path:\nSecureRetriever.search() ==\nplain vector search only"| CONTEXTBUILD

    MEMORY["PersistentMemoryStore\n(naive keyword overlap --\nNOT semantic, separate from\nthe document retrieval above)"] --> CONTEXTBUILD

    CONTEXTBUILD --> PROMPT["Final prompt:\nmemory section + retrieved_context section\n+ the question, each explicitly labeled"]

    PROMPT --> LLM["LLM generate()\nprompted to cite chunk ids\nin brackets, e.g. [doc::chunk0],\nand to say 'not found' rather\nthan guess if nothing relevant"]

    LLM --> OUTPUT["PersonalRagResult\nanswer + memory_used + citations"]

    OUTPUT --> GROUNDING["evaluate_grounding()\nLLM-as-judge: what fraction of\nthe answer's claims are actually\nsupported by the retrieved evidence?"]
    OUTPUT --> CITATION["citation_quality()\ndeterministic: does every cited\nchunk id actually exist among\nwhat was retrieved?"]
    FUSION -.->|"if a labeled ground-truth\nexists for this query"| RETRIEVALEVAL["evaluate_retrieval()\nrecall@k / precision@k --\nneeds relevant_chunk_ids labeled\nby a human, not inferred"]

    subgraph FAILUREMODES["Real failure modes -- what actually happens"]
        direction TB
        F1["Retrieval returns nothing\n-> prompt explicitly says\n'if nothing relevant, say so\nrather than guessing'"]
        F2["Generation hallucinates a citation\n-> citation_quality() catches it:\nchunk id not in the retrieved set"]
        F3["Generation makes an ungrounded claim\n-> evaluate_grounding() catches it:\nclaim not supported by evidence"]
        F4["Context exceeds token budget\n-> ContextBuilder drops lowest-\npriority sections first, never\nblindly truncates mid-section"]
    end
"""
