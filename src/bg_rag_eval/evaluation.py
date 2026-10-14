import json

from deepeval import evaluate  # pyright: ignore[reportUnknownVariableType]
from deepeval.evaluate import AsyncConfig, CacheConfig, ErrorConfig
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from bg_rag_eval.run import QUESTIONS_PATH, RESULTS_DIR
from bg_rag_eval.schemas import EvalQuestion, EvalRecord, ScoredRecord

EVALUATED_DIR = RESULTS_DIR / "evaluated"
JUDGE_MODEL = "gpt-4o"


def retrieval_scores(
    retrieved: list[str], gold: list[str]
) -> tuple[float | None, float | None, float | None]:
    """Recall, completeness and MRR of the retrieved chunk IDs against the gold chunks.

    Completeness is 1 only if ALL gold chunks were retrieved. That is stricter than
    the usual hit@k, which counts a hit when at least one relevant chunk is retrieved.
    Returns (None, None, None) for unanswerable questions, which have no gold chunks.
    """
    if not gold:
        return None, None, None
    found = [chunk for chunk in gold if chunk in retrieved]
    recall = len(found) / len(gold)
    complete = 1.0 if len(found) == len(gold) else 0.0
    ranks = [rank for rank, chunk in enumerate(retrieved, start=1) if chunk in gold]
    mrr = 1 / ranks[0] if ranks else 0.0
    return recall, complete, mrr


def evaluation(method_name: str, questions: list[int] | None = None) -> None:
    with open(RESULTS_DIR / f"{method_name}.jsonl", "r", encoding="utf-8") as file:
        results: list[EvalRecord] = [json.loads(line) for line in file]

    with open(QUESTIONS_PATH, "r", encoding="utf-8") as file:
        eval_questions: list[EvalQuestion] = [json.loads(line) for line in file]
    gold_by_question = {q["question"]: q["gold_chunks"] for q in eval_questions}

    if questions:
        results = [r for n, r in enumerate(results, start=1) if n in questions]

    questions_tests: list[LLMTestCase] = []

    for result in results:
        test_case = LLMTestCase(
            input=result["question"],
            actual_output=result["actual_answer"],
            expected_output=result["expected_answer"],
            retrieval_context=[*result["context"]],
        )

        questions_tests.append(test_case)

    groundedness = GEval(
        name="Groundedness",
        evaluation_steps=[
            "Check that every claim in the actual output is supported by the retrieval context.",
            (
                "Rules from an expansion or an event card apply only when that expansion or card is in play, and "
                "they override the base-game rule they modify. A base rule and an event rule that changes it are "
                "NOT a contradiction; an answer that states both correctly is fully supported."
            ),
            (
                "Each excerpt starts with its rulebook location (e.g. 'Extra Pepper > Change a Rule > The Treasure "
                "Chest'); the last part of that path is the name of the rule or card."
            ),
            (
                "Penalize claims that are not stated in the context, including statements about rules or cards the "
                "context does not describe."
            ),
            (
                "Penalize claims that apply an event card's rule to the whole expansion, or to situations the "
                "context does not cover."
            ),
            (
                "Penalize presenting the specific result of a worked example as if it were the general rule "
                "(e.g. stating an example's point total as what always happens)."
            ),
        ],
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.RETRIEVAL_CONTEXT,
        ],
        threshold=0.7,
        model=JUDGE_MODEL,
    )
    correctness = GEval(
        name="Correctness",
        evaluation_steps=[
            "Identify the facts in the expected output that are needed to answer the input question.",
            "Check whether the actual output states each of those facts correctly.",
            "Heavily penalize any statement in the actual output that contradicts the expected output.",
            "Do not penalize the actual output for leaving out details of the expected output that the question did not ask about.",
            "Do not penalize the actual output for extra information, unless it is wrong or contradicts the expected output.",
            (
                "Penalize statements that apply a rule more broadly than the expected output does, such as presenting "
                "a worked example's specific result as the general rule, or an event card's rule as a rule of the "
                "whole expansion."
            ),
            (
                "Only if the expected output says the rulebooks do not give the answer: the actual output is correct "
                "if it also says the information is not given, and incorrect if it states an answer as fact."
            ),
        ],
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        threshold=0.7,
        model=JUDGE_MODEL,
    )

    evaluation_results = evaluate(
        test_cases=questions_tests,
        metrics=[correctness, groundedness],
        async_config=AsyncConfig(max_concurrent=2),
        error_config=ErrorConfig(ignore_errors=True),
        cache_config=CacheConfig(use_cache=False, write_cache=False),
    )

    evaluated_results: list[ScoredRecord] = []

    for test_result in evaluation_results.test_results:
        assert test_result.index is not None
        original_result = results[test_result.index]

        correctness_score = None
        groundedness_score = None

        correctness_reason = None
        groundedness_reason = None

        for metric in test_result.metrics_data or []:
            metric_name = metric.name.strip().lower()

            if metric_name.startswith("correctness"):
                correctness_score = metric.score
                correctness_reason = metric.reason
            elif metric_name.startswith("groundedness"):
                groundedness_score = metric.score
                groundedness_reason = metric.reason

        gold_chunks = gold_by_question[original_result["question"]]
        recall, complete, mrr = retrieval_scores(original_result["chunk_ids"], gold_chunks)

        evaluated_result: ScoredRecord = {
            **original_result,
            "correctness": correctness_score,
            "correctness_reason": correctness_reason,
            "groundedness": groundedness_score,
            "groundedness_reason": groundedness_reason,
            "gold_chunks": gold_chunks,
            "retrieval_recall": recall,
            "retrieval_complete": complete,
            "retrieval_mrr": mrr,
        }

        evaluated_results.append(evaluated_result)

    suffix = "_subset" if questions else ""
    EVALUATED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EVALUATED_DIR / f"{method_name}{suffix}.jsonl"

    with open(output_path, "w", encoding="utf-8") as file:
        for result in evaluated_results:
            file.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(f"\nSaved to {output_path}")
    for key in ("correctness", "groundedness", "retrieval_recall", "retrieval_complete", "retrieval_mrr"):
        values = [v for r in evaluated_results if (v := r[key]) is not None]
        if values:
            print(f"  {key:<17} {sum(values) / len(values):.3f}  (n={len(values)})")


if __name__ == "__main__":
    import sys

    method = sys.argv[1]
    questions = [int(n) for n in sys.argv[2:]]
    evaluation(method, questions or None)
