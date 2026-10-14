# bg-rag-eval

Evaluating four retrieval-augmented generation (RAG) methods on rules questions about the board game **Sea Salt & Paper** and its expansions **Extra Pepper** and **Extra Salt**.

| Method | Retrieval |
|---|---|
| **Baseline** | Embedding search with the question |
| **RAG-Fusion** | The question plus 4 LLM rewrites, merged with Reciprocal Rank Fusion |
| **HyDE** | Search with an LLM-written hypothetical rulebook passage |
| **Reranking** | Top 20 by embedding search, reordered by a cross-encoder |

All methods share the same chunks, top-k (5), prompt and generator; only retrieval differs. Answers are scored by a `gpt-4o` judge (correctness, groundedness) and retrieval is scored exactly against labelled gold chunks.

## Results

| | Baseline | RAG-Fusion | HyDE | Reranking |
|---|---|---|---|---|
| Retrieval: all needed chunks found | 0.94 | 0.94 | 0.96 | **1.00** |
| Correctness, gpt-4o-mini generator (mean of 3 runs) | 0.86 | **0.89** | 0.86 | 0.81 |
| Correctness, gpt-4o generator (1 run) | 0.90 | 0.88 | **0.94** | 0.93 |

- **Reranking is the only reliable retrieval improvement.** It retrieved every needed rule for every question in every run, including a card-specific rule the baseline ranked just outside the top 5.
- **Query rewriting (RAG-Fusion, HyDE) did not help on this small corpus.** RAG-Fusion reordered the same chunks; HyDE's retrieval depended on the LLM guessing the answer.
- **With `gpt-4o-mini`, the generator was the bottleneck:** its errors (arithmetic, ignoring the top-ranked rule) were larger than the differences between methods. With `gpt-4o` they largely disappear, and the methods with complete retrieval come out on top.

The full write-up, with per-question examples, evaluation design choices and limitations, is in **[REPORT.md](REPORT.md)**.

## Project structure

```
data/
├── README.md              how the rulebooks were obtained and transcribed
├── eval_questions.jsonl   20 questions with expected answers and gold chunks
└── rulebooks/sources.yaml rulebook sources (URL, SHA-256) and indexing notes
src/bg_rag_eval/
├── indexing.py            chunking by heading + embedded vector index
├── prompt.py              system, query-rewrite and HyDE prompts
├── methods/               baseline, rag_fusion, hyde, reranking (+ shared generation in common.py)
├── run.py                 generate answers for all questions
└── evaluation.py          score answers (DeepEval judge + gold-chunk retrieval metrics)
REPORT.md                  results and analysis
```

## Running it

**Requirements:** Python 3.12+, [uv](https://docs.astral.sh/uv/) and an OpenAI API key.

```bash
uv sync                      # install dependencies
cp .env.example .env         # then set OPENAI_API_KEY in .env
```

**Corpus.** The rulebooks are copyrighted, so neither the PDFs nor their Markdown transcriptions are included. Download the PDFs and transcribe them following [`data/README.md`](data/README.md); the gold chunk IDs depend on the Markdown headings.

```bash
python -m bg_rag_eval.indexing                   # build the index (once)
python -m bg_rag_eval.run <method> [tag]         # answers  -> results/<method>[_tag].jsonl
python -m bg_rag_eval.evaluation <method>[_tag]  # scores   -> results/evaluated/<method>[_tag].jsonl
```

`<method>` is `baseline`, `rag_fusion`, `hyde` or `reranking`. Use a tag (e.g. `run2`, `gpt4o`) to keep separate runs. The generator model is `CHAT_MODEL` in `src/bg_rag_eval/methods/common.py`. Reranking downloads a ~1 GB model on first use; set `HF_HUB_OFFLINE=1` afterwards to load it from cache.
