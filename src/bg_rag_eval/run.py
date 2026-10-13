import json
from collections.abc import Callable

from bg_rag_eval.indexing import ROOT
from bg_rag_eval.schemas import EvalQuestion, RAGResult

QUESTIONS_PATH = ROOT / "data" / "eval_questions.jsonl"
RESULTS_DIR = ROOT / "results"


def run(method_name: str, answer_fn: Callable[[str], RAGResult]) -> None:
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as file:
        test_cases: list[EvalQuestion] = [json.loads(line) for line in file]

    RESULTS_DIR.mkdir(exist_ok=True)
    output_path = RESULTS_DIR / f"{method_name}.jsonl"

    with open(output_path, "w", encoding="utf-8") as out:
        for test_case in test_cases:
            question = test_case["question"]
            expected_answer = test_case["expected_answer"]

            print(f"\nQuestion: {question}")
            rag_result = answer_fn(question)
            print(f"Answer: {rag_result['answer']}")

            result: dict[str, str | list[str]] = {
                "question": question,
                "expected_answer": expected_answer,
                "actual_answer": rag_result["answer"],
                "context": rag_result["contexts"],
                "chunk_ids": rag_result["chunk_ids"],
            }

            out.write(json.dumps(result) + "\n")

    print(f"\nDone! {len(test_cases)} results saved to {output_path}")
