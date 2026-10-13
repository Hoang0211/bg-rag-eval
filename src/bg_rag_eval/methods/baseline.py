from langchain_core.documents import Document

from bg_rag_eval.methods.common import TOP_K, generate, store
from bg_rag_eval.schemas import RAGResult


def retrieve(question: str) -> list[Document]:
    return store.similarity_search(question, k=TOP_K)


def answer(question: str) -> RAGResult:
    return generate(question, retrieve(question))


if __name__ == "__main__":
    from bg_rag_eval.run import run
    run("baseline", answer)