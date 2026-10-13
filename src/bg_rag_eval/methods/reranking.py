from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

from bg_rag_eval.methods.common import TOP_K, generate, store
from bg_rag_eval.schemas import RAGResult

CANDIDATES = 20
RERANKER_MODEL = "BAAI/bge-reranker-base"

reranker = CrossEncoder(RERANKER_MODEL)


def retrieve(question: str) -> list[Document]:
    candidates = store.similarity_search(question, k=CANDIDATES)
    pairs = [(question, doc.page_content) for doc in candidates]
    scores: list[float] = reranker.predict(pairs).tolist()  # pyright: ignore[reportUnknownMemberType]
    ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
    return [doc for doc, _ in ranked[:TOP_K]]


def answer(question: str) -> RAGResult:
    return generate(question, retrieve(question))


if __name__ == "__main__":
    from bg_rag_eval.run import run

    run("reranking", answer)
