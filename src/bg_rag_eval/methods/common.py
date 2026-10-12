from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from bg_rag_eval.indexing import get_index
from bg_rag_eval.prompt import SYSTEM_PROMPT
from bg_rag_eval.schemas import RAGResult


TOP_K = 5

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
store = get_index()


def generate(question: str, docs: list[Document]) -> RAGResult:
    context = "\n\n---\n\n".join(doc.page_content for doc in docs)
    reply = llm.invoke([
        ("system", SYSTEM_PROMPT),
        ("user", f"Rulebook excerpts:\n\n{context}\n\nQuestion: {question}")
    ])

    return { 
        "answer": reply.text,
        "contexts": [doc.page_content for doc in docs],
        "chunk_ids": [doc.id or "" for doc in docs]
    }