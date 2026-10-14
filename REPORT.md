# RAG Methods on Board Game Rules: Evaluation Report

This project compares four retrieval-augmented generation (RAG) methods on question answering over the rulebooks of **Sea Salt & Paper** and its expansions **Extra Pepper** and **Extra Salt**: a naive baseline, RAG-Fusion, HyDE and cross-encoder reranking.

**Main finding:** with `gpt-4o-mini` generating the answers, no method improved answer quality over the baseline: the generator's own errors were larger than the differences between retrieval methods. With `gpt-4o` generating, those errors largely disappear and the methods that retrieve every needed rule (reranking reliably, HyDE in that run) gain 0.07–0.13 in answer correctness. **Better retrieval only paid off once the generator was strong enough to use it.** Reranking was the only method that retrieved all needed rules for every question, in every run.

## Setup

| | |
|---|---|
| **Corpus** | 3 English rulebooks, hand-transcribed to Markdown ([`data/README.md`](data/README.md)), split into **50 chunks**, one per heading (rule, card or example) |
| **Questions** | **20**: 17 answerable (10 single-rule, 3 multi-rule, 4 combining a base rule with an expansion rule) and 3 the rulebooks cannot answer |
| **Embeddings** | `text-embedding-3-large`, in-memory vector store |
| **Retrieval** | top **k = 5** chunks passed to the generator, for every method |
| **Generator** | `gpt-4o-mini` (main runs) and `gpt-4o` (one run per method), temperature 0, same system prompt for all methods |
| **Judge** | `gpt-4o` via DeepEval, with the same settings for every method |

### Methods

| Method | How retrieval works |
|---|---|
| **Baseline** | Embedding search with the question |
| **RAG-Fusion** | The question plus 4 LLM-generated rewrites, each searched; results merged with Reciprocal Rank Fusion (k = 60) |
| **HyDE** | An LLM writes a hypothetical rulebook passage answering the question; the search uses that passage |
| **Reranking** | Embedding search for 20 candidates, reordered by a local cross-encoder (`BAAI/bge-reranker-base`) |

Only retrieval differs between methods; answer generation (`methods/common.py`) is shared.

### Metrics

| Metric | Measures | How |
|---|---|---|
| **Correctness** | Is the answer right? | GEval judge against the expected answer, with explicit evaluation steps |
| **Groundedness** | Is every claim supported by the retrieved chunks? | GEval judge against the retrieved context |
| **Retrieval recall** | Share of the needed chunks that were retrieved | Exact match against labelled **gold chunks**, no judge |
| **Retrieval complete** | Were *all* needed chunks retrieved (1/0)? Stricter than the usual hit@k | Gold chunks |
| **Retrieval MRR** | How high the first needed chunk ranked | Gold chunks |

Retrieval metrics are averaged over the 17 answerable questions; correctness and groundedness are reported for the 17 answerable questions and, separately, correctness for the 3 unanswerable ones.

## Results

### With gpt-4o-mini (3 runs per method: mean [lowest – highest run])

| | Baseline | RAG-Fusion | HyDE | Reranking |
|---|---|---|---|---|
| Correctness | 0.863 [0.84–0.90] | **0.885** [0.87–0.91] | 0.860 [0.85–0.87] | 0.806 [0.79–0.82] |
| Groundedness | **0.945** [0.93–0.96] | 0.943 [0.93–0.95] | 0.929 [0.92–0.94] | 0.917 [0.91–0.92] |
| Correctness, unanswerable | **0.936** | 0.922 | 0.924 | 0.917 |
| Retrieval recall | 0.971 | 0.971 | 0.971 [0.94–1.00] | **1.000** |
| Retrieval complete | 0.941 | 0.941 | 0.961 [0.94–1.00] | **1.000** |
| Retrieval MRR | **0.843** | 0.763 | 0.801 | 0.835 |

### With gpt-4o (1 run per method)

| | Baseline | RAG-Fusion | HyDE | Reranking |
|---|---|---|---|---|
| Correctness | 0.896 | 0.876 | **0.935** | 0.933 |
| Groundedness | 0.964 | 0.967 | **0.985** | 0.968 |
| Correctness, unanswerable | 0.917 | **0.924** | 0.896 | 0.919 |
| Retrieval complete | 0.941 | 0.941 | **1.000** | **1.000** |
| Retrieval MRR | **0.843** | 0.828 | **0.843** | 0.835 |

Change in correctness from gpt-4o-mini (mean) to gpt-4o: **reranking +0.13, HyDE +0.08** (both well outside the gpt-4o-mini run-to-run range), baseline +0.03 and RAG-Fusion −0.01 (both within it).

## Findings

### 1. Reranking is the only reliable retrieval improvement

The baseline already retrieves every needed chunk for 16 of 17 answerable questions, so there is little room to improve. The one failure is **q14** ("*If the Diodon Fish event is active and I end the round, but an opponent ends up with more points than me, what do I score?*"): the Diodon Fish rule ranks 6th, just outside the top 5.

| Diodon Fish rule retrieved for q14 | Baseline | RAG-Fusion | HyDE | Reranking |
|---|---|---|---|---|
| gpt-4o-mini runs | 0 of 3 | 0 of 3 | 1 of 3 | **3 of 3** |
| gpt-4o run | no | no | yes | **yes** |

Reranking puts it **first**: the cross-encoder reads the question and chunk together and catches the exact card-name match that embedding similarity underweights. With it, the answer finally states the real rule (you must say LAST CHANCE, and a lost bet scores only the color bonus).

### 2. Query rewriting did not help on this corpus

- **RAG-Fusion** retrieved the same chunks as the baseline, only reordered. RRF rewards chunks matched by many rewrites, which favours examples and broadly related rules over the specific one, lowering MRR (0.84 → 0.76).
- **HyDE** depends on the LLM's guess of the answer. For an unfamiliar card it guessed wrong (it invented a scoring rule for the Diodon Fish), so its retrieval for q14 succeeded in only some runs. In one run the final answer repeated the invented rule.
- Both rewrites assume what an unknown card does; neither can fix the embedding model's weakness with rare names.

### 3. The generator, not retrieval, limited answer quality with gpt-4o-mini

- **Inconsistent arithmetic:** the same question with the same chunks gave "11", "17" and "21 points" across three runs (q07). Only 2 of 20 baseline answers were identical across runs, despite temperature 0.
- **Ignoring the top-ranked rule:** with reranking's context, gpt-4o-mini ignored the Kraken rule ranked 1st and answered "9 points" instead of 4 in **all three runs** (q12, correctness ≈ 0.13).
- **Over-literal reading:** it said the jellyfish "has no effect" because the effect belongs to the swimmer + jellyfish duo (q17), although that rule was retrieved.

With gpt-4o these cases are answered correctly (q07 ≈ 1.00 for all methods, q12 reranking 1.00, q17 0.85–0.98), and the methods with complete retrieval move to the top.

### 4. Unanswerable questions are handled well by every method

All methods decline correctly on the three unanswerable questions (correctness 0.88–0.94). gpt-4o did not improve this; it sometimes adds more loosely related detail when declining.

## Evaluation design notes

Several choices were made after inspecting baseline results; they apply equally to all methods.

- **Gold chunks replaced judged contextual recall.** DeepEval's contextual recall gave q14 a perfect 1.00 although the needed rule was missing (it matched "LAST CHANCE" in another chunk), and 0.50 on q12 although both rules were retrieved. Exact gold-chunk matching is free, deterministic and correct on both.
- **Custom groundedness replaced DeepEval's faithfulness metric.** Faithfulness treated a base rule and the event card that overrides it ("7 points" vs "10 points instead of 7") as a contradiction and scored correct answers 0.00. A GEval metric told how expansion and event rules relate fixed this.
- **Event-card scope notes added at indexing.** Every Extra Pepper rule is an event card, but only the expansion's rules section says so, so retrieved event chunks read like permanent rules. A short note restating this is added to each event chunk when indexing; the Markdown stays a faithful transcription.
- **The answer prompt was revised** after the baseline review to cover exceptions, worked examples and which rulebook a fact comes from. Examples that would give away eval answers were removed.

## Limitations

- **Small question set.** 20 questions, 17 answerable; one question can move a method's average by about 0.05.
- **One gpt-4o run per method.** Reranking's and HyDE's gains are large relative to run-to-run variation, but the baseline and RAG-Fusion changes are not conclusive.
- **Judge and generator are the same model in the gpt-4o runs,** which may inflate absolute scores (self-preference). Comparisons between methods are unaffected.
- **Tuned on the test set.** The prompt, event-card notes and judge steps were adjusted after reviewing baseline answers on these same 20 questions, so absolute scores are optimistic. No separate tuning set was used.
- **Known judge weakness.** The judges under-penalize answers that apply a rule too broadly, e.g. presenting a worked example's result as the general rule (q09, "two mermaids always score 7 points").
- **Single small corpus.** Results may differ for large corpora or vaguer questions, where query rewriting is usually more useful.

## Reproducing

**1. Install and configure**

```bash
uv sync                      # install dependencies
cp .env.example .env         # then set OPENAI_API_KEY in .env
```

**2. Prepare the corpus.** The rulebooks are copyrighted, so neither the PDFs nor their Markdown conversions are in the repository. Download the PDFs and check their SHA-256 as described in [`data/README.md`](data/README.md), then transcribe each one to the `markdown` path listed in [`data/rulebooks/sources.yaml`](data/rulebooks/sources.yaml), following the conversion rules in `data/README.md`. The chunk IDs, and therefore the gold chunks in `data/eval_questions.jsonl`, depend on those headings.

**3. Run**

```bash
python -m bg_rag_eval.indexing                           # build the index (also built automatically on first use)
python -m bg_rag_eval.run <method> [tag]                 # generate answers -> results/<method>[_tag].jsonl
python -m bg_rag_eval.evaluation <method>[_tag]          # score them -> results/evaluated/<method>[_tag].jsonl
```

`<method>` is `baseline`, `rag_fusion`, `hyde` or `reranking`; the optional `tag` names a separate run (e.g. `run2`, `gpt4o`) so earlier results are not overwritten. The generator model is set by `CHAT_MODEL` in `src/bg_rag_eval/methods/common.py` (`gpt-4o-mini` by default; change it to `gpt-4o` for the comparison runs).

Reranking downloads `BAAI/bge-reranker-base` (about 1 GB) from Hugging Face on first use. Afterwards, set `HF_HUB_OFFLINE=1` to load it from the local cache and avoid Hugging Face rate limits.
