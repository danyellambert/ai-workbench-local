# Phase 8.5 Benchmark Report

- Run ID: `phase8-5-matrix-3ba8070849`
- Total case attempts recorded: **1**
- Latest unique cases considered: **1**
- Total cases: **1**
- Successful cases: **1**
- Failed cases: **0**

## Generation ranking

| Rank | Provider | Model | Runtime path | Backend | Success rate | Avg use-case fit | Avg latency (s) |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |

## Generation operational metrics

| Provider | Model | Avg total wall time (s) | Avg TTFT (s) | Avg throughput (tok/s) | TTFT status counts | Throughput status counts |
| --- | --- | ---: | ---: | ---: | --- | --- |

## Embedding ranking

| Rank | Provider | Model | Role | Runtime path | Backend | Avg MRR | Avg Hit@1 | Avg retrieval (s) |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |

## Runtime path breakdown

| Runtime path | Cases | Successful | Failed | Expected overhead | Backend examples |
| --- | ---: | ---: | ---: | --- | --- |
| `direct_runtime` | 1 | 1 | 0 | no | ollama::embeddinggemma:300m |

## Requested vs resolved model mapping

- Resolution counts: `{"exact": 1}`
- No requested-vs-resolved substitutions were needed for the latest case results.

## Reranker leaderboard

| Rank | Candidate | Provider | Model | Runtime path | Runtime family | Role | Avg MRR | Avg Hit@1 | Avg retrieval (s) | Avg groundedness proxy |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `vector_only_local_baseline` | `ollama` | `embeddinggemma:300m` | `direct_runtime` | `ollama_local` | `baseline` | 0.5000 | 0.5000 | 0.6028 | 0.5000 |

## OCR / VLM leaderboard

| Rank | Variant | Runtime family | Avg F1 | Avg latency (s) | Helped cases |
| --- | --- | --- | ---: | ---: | ---: |

## Round 2 tradeoff notes

- Best reranker tradeoff: `vector_only_local_baseline`
- Best OCR fallback tradeoff: `n/a`
- Best VLM fallback tradeoff: `n/a`
- Support is intentionally incremental: reranker comparisons are fully local and executable; OCR/VLM comparisons focus on reusable CV/contact-evidence slices already present in the repo.


## Fairness notes

- Temperature, top_p, max output tokens, context windows, prompt profile, response format, runtime bucket, and quantization family are captured per case.
- Seed is recorded as requested metadata, but not all providers in this repo currently expose a universal deterministic seed control.
- Direct runtimes and hub-wrapped runtimes are now distinguished explicitly in the raw events, normalized tables, aggregated summaries, and this report.
- A `huggingface_server` alias backed by Ollama is treated as a wrapped runtime path, not as identical to direct Ollama, because it may add hub/router HTTP overhead.
- Comparisons are only apples-to-apples where provider/runtime semantics align; exact resolved runtime artifact details are stored in `environment_snapshot.json` and raw events.

