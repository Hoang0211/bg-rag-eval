from typing import TypedDict


class RAGResult(TypedDict):
    answer: str
    contexts: list[str]
    chunk_ids: list[str]