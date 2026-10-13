from typing import TypedDict


class RAGResult(TypedDict):
    answer: str
    contexts: list[str]
    chunk_ids: list[str]


class EvalQuestion(TypedDict):
    question: str
    expected_answer: str
    gold_chunks: list[str]  # chunks a complete answer needs; empty if unanswerable


class EvalRecord(TypedDict):
    question: str
    expected_answer: str
    actual_answer: str
    context: list[str]
    chunk_ids: list[str]


class ScoredRecord(EvalRecord):
    correctness: float | None
    correctness_reason: str | None
    groundedness: float | None
    groundedness_reason: str | None
    gold_chunks: list[str]
    retrieval_recall: float | None  # share of gold chunks retrieved
    retrieval_complete: float | None  # 1 if ALL gold chunks were retrieved, else 0 (stricter than hit@k)
    retrieval_mrr: float | None  # 1 / rank of the first gold chunk retrieved
