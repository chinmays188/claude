from pydantic import BaseModel

from app.retrieval.vector_search import VectorStore
from app.tools.base import Tool


class RetrievalArgs(BaseModel):
    query: str
    top_k: int = 3


class RetrievalTool(Tool):
    name = "retrieve"
    description = (
        "Search the local knowledge base for information relevant to a query. "
        "Use this to ground answers in ingested documents rather than guessing."
    )
    permissions = ["read:retrieval"]
    retry_safe = True
    args_schema = RetrievalArgs

    def __init__(self, store: VectorStore):
        self._store = store

    def run(self, args: RetrievalArgs) -> str:
        results = self._store.search(args.query, top_k=args.top_k)
        if not results:
            return "No relevant documents found."

        lines = []
        for r in results:
            lines.append(f"[{r.chunk.id} | source={r.chunk.source} | score={r.score:.4f}] {r.chunk.text}")
        return "\n".join(lines)
