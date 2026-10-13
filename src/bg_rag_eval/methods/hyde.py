from langchain_core.documents import Document

from bg_rag_eval.methods.common import TOP_K, generate, llm, store
from bg_rag_eval.prompt import HYDE_PROMPT
from bg_rag_eval.schemas import RAGResult


def hypothetical_passage(question: str) -> str:
    """Ask the LLM to write a rulebook-style passage that would answer the question."""
    reply = llm.invoke([("system", HYDE_PROMPT), ("user", question)])
    return reply.text


def retrieve(question: str) -> list[Document]:
    return store.similarity_search(hypothetical_passage(question), k=TOP_K)


def answer(question: str) -> RAGResult:
    return generate(question, retrieve(question))


if __name__ == "__main__":
    from bg_rag_eval.run import run

    run("hyde", answer)
