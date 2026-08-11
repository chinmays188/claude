from pydantic import BaseModel

from app.context.builder import ContextBuilder, ContextSection
from app.knowledge.secure_retrieval import SecureRetriever
from app.memory.retrieval import MemoryRetriever
from app.memory.models import MemoryRecord
from app.providers.base import LLMProvider

ANSWER_PROMPT = """{context}

Using the personal memory and documents above (if any are relevant), answer the
user's question. When you use a specific document, cite its chunk id in brackets,
e.g. [doc1::chunk0]. If nothing relevant was found, say so rather than guessing.

Question: {question}
"""


class Citation(BaseModel):
    chunk_id: str
    source: str


class PersonalRagResult(BaseModel):
    question: str
    answer: str
    memory_used: list[str] = []  # memory_ids
    citations: list[Citation] = []


class PersonalRagPipeline:
    """Section 14's pipeline: memory retrieval + document retrieval (hybrid
    search + reranking already live in Phase 1's HybridSearch/CrossEncoderReranker,
    reused here rather than reimplemented) -> context builder -> LLM -> citations.
    Distinguishes memory from retrieved knowledge (Section 2, capability #4) by
    keeping them as separate, separately-labeled context sections."""

    def __init__(
        self,
        llm: LLMProvider,
        secure_retriever: SecureRetriever,
        memory_retriever: MemoryRetriever,
        context_builder: ContextBuilder | None = None,
    ):
        self._llm = llm
        self._secure_retriever = secure_retriever
        self._memory_retriever = memory_retriever
        self._context_builder = context_builder or ContextBuilder()

    def answer(
        self,
        question: str,
        requester_id: str,
        requester_tenant_id: str,
        memory_candidates: list[MemoryRecord],
        top_k_documents: int = 5,
        top_k_memory: int = 5,
    ) -> PersonalRagResult:
        if not question or not question.strip():
            raise ValueError("Question must not be empty.")

        ranked_memories = self._memory_retriever.rank(question, memory_candidates, top_k=top_k_memory)
        document_results = self._secure_retriever.search(
            question, requester_id=requester_id, requester_tenant_id=requester_tenant_id,
            top_k=top_k_documents,
        )

        memory_text = "\n".join(f"- {rm.memory.content}" for rm in ranked_memories)
        docs_text = "\n".join(f"[{r.chunk.id} | source={r.chunk.source}] {r.chunk.text}" for r in document_results)

        context = self._context_builder.build(
            [
                ContextSection(name="memory", content=memory_text, priority=1),
                ContextSection(name="retrieved_context", content=docs_text, priority=2),
            ]
        )

        prompt = ANSWER_PROMPT.format(context=context, question=question)
        answer_text = self._llm.generate(prompt)

        return PersonalRagResult(
            question=question,
            answer=answer_text,
            memory_used=[rm.memory.memory_id for rm in ranked_memories],
            citations=[Citation(chunk_id=r.chunk.id, source=r.chunk.source) for r in document_results],
        )
