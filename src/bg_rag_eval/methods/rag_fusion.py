import re

from langchain_core.documents import Document

from bg_rag_eval.methods.common import TOP_K, generate, llm, store
from bg_rag_eval.prompt import QUERY_GENERATION_PROMPT
from bg_rag_eval.schemas import RAGResult

NUM_QUERIES = 4


def retrieve(question: str) -> list[Document]:
    return store.similarity_search(question, k=TOP_K)


def generate_queries(question: str) -> list[str]:
    """Ask the LLM for alternative search queries for the question."""
    reply = llm.invoke(
        [
            ("system", QUERY_GENERATION_PROMPT.format(n=NUM_QUERIES)),
            ("user", question),
        ]
    )
    queries: list[str] = []
    for line in reply.text.splitlines():
        query = re.sub(r"^\s*(\d+[.)]|[-*•])\s*", "", line).strip()
        if query and query not in queries:
            queries.append(query)
    return queries[:NUM_QUERIES]


def reciprocal_rank_fusion(
    results: list[list[Document]], k: int = 60
) -> list[Document]:
    """Fuse several ranked lists of documents with Reciprocal Rank Fusion, best first."""

    fused_scores: dict[str, float] = {}
    docs_by_id: dict[str, Document] = {}

    for docs in results:
        for rank, doc in enumerate(docs):
            assert doc.id is not None
            docs_by_id[doc.id] = doc
            fused_scores[doc.id] = fused_scores.get(doc.id, 0.0) + 1 / (rank + k)

    ranked_ids = sorted(
        fused_scores, key=lambda doc_id: fused_scores[doc_id], reverse=True
    )

    return [docs_by_id[doc_id] for doc_id in ranked_ids]


def answer(question: str) -> RAGResult:
    queries = [question, *generate_queries(question)]
    fused = reciprocal_rank_fusion([retrieve(q) for q in queries])
    return generate(question, fused[:TOP_K])


if __name__ == "__main__":
    from bg_rag_eval.run import run

    run("rag_fusion", answer)
