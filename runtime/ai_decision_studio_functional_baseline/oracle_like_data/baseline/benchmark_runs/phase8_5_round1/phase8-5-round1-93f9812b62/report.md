# Phase 8.5 Benchmark Report

- Run ID: `phase8-5-matrix-983d3bfc57`
- Total case attempts recorded: **41**
- Latest unique cases considered: **34**
- Total cases: **34**
- Successful cases: **33**
- Failed cases: **1**

## Generation ranking

| Rank | Provider | Model | Runtime path | Backend | Success rate | Avg use-case fit | Avg latency (s) |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 1 | `huggingface_server` | `qwen2.5:7b-ollama` | `hub_wrapped_runtime` | `ollama::qwen2.5:7b` | 1.0000 | 1.0000 | 9.5002 |
| 2 | `ollama` | `qwen2.5-coder:7b` | `direct_runtime` | `ollama::qwen2.5-coder:7b` | 1.0000 | 1.0000 | 14.2387 |
| 3 | `ollama` | `qwen2.5:7b` | `direct_runtime` | `ollama::qwen2.5:7b` | 1.0000 | 0.9840 | 13.4402 |

## Embedding ranking

| Rank | Provider | Model | Role | Runtime path | Backend | Avg MRR | Avg Hit@1 | Avg retrieval (s) |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 1 | `ollama` | `bge-m3:latest` | `challenger` | `direct_runtime` | `ollama::bge-m3:latest` | 0.9375 | 0.8750 | 0.9834 |
| 2 | `ollama` | `embeddinggemma:300m` | `baseline` | `direct_runtime` | `ollama::embeddinggemma:300m` | 0.9062 | 0.8750 | 0.7629 |
| 3 | `ollama` | `qwen3-embedding:0.6b` | `challenger` | `direct_runtime` | `ollama::qwen3-embedding:0.6b` | 0.8750 | 0.8750 | 0.8929 |
| 4 | `huggingface_server` | `embeddinggemma:300m` | `optional_local_hub` | `hub_wrapped_runtime` | `huggingface_local::google/embeddinggemma-300m` | 0.0000 | 0.0000 | 0.0000 |

## Runtime path breakdown

| Runtime path | Cases | Successful | Failed | Expected overhead | Backend examples |
| --- | ---: | ---: | ---: | --- | --- |
| `direct_runtime` | 21 | 21 | 0 | no | ollama::bge-m3:latest, ollama::embeddinggemma:300m, ollama::qwen2.5-coder:7b, ollama::qwen2.5:7b, ollama::qwen3-embedding:0.6b |
| `hub_wrapped_runtime` | 9 | 8 | 1 | yes | huggingface_local::google/embeddinggemma-300m, ollama::qwen2.5:7b |
| `unknown_runtime_path` | 4 | 4 | 0 | no | - |

## Reranker leaderboard

| Rank | Candidate | Provider | Model | Runtime path | Role | Avg MRR | Avg Hit@1 | Avg retrieval (s) | Avg groundedness proxy |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `hybrid_rerank_current_default` | `ollama` | `embeddinggemma:300m` | `direct_runtime` | `current_default` | 0.9062 | 0.8750 | 0.6673 | 0.9062 |
| 2 | `vector_only_local_baseline` | `ollama` | `embeddinggemma:300m` | `direct_runtime` | `baseline` | 0.8125 | 0.7500 | 1.6168 | 0.8438 |

## OCR / VLM leaderboard

| Rank | Variant | Avg F1 | Avg latency (s) | Helped cases |
| --- | --- | ---: | ---: | ---: |
| 1 | `evidence_with_vl` | 0.7500 | 2.4093 | 4 |
| 2 | `evidence_no_vl` | 0.7500 | 2.4303 | 4 |
| 3 | `legacy_pdf` | 0.2500 | 0.0303 | 0 |

## Round 2 tradeoff notes

- Best reranker tradeoff: `hybrid_rerank_current_default`
- Best OCR fallback tradeoff: `evidence_no_vl`
- Best VLM fallback tradeoff: `evidence_with_vl`
- Support is intentionally incremental: reranker comparisons are fully local and executable; OCR/VLM comparisons focus on reusable CV/contact-evidence slices already present in the repo.


## Fairness notes

- Temperature, top_p, max output tokens, context windows, prompt profile, response format, runtime bucket, and quantization family are captured per case.
- Seed is recorded as requested metadata, but not all providers in this repo currently expose a universal deterministic seed control.
- Direct runtimes and hub-wrapped runtimes are now distinguished explicitly in the raw events, normalized tables, aggregated summaries, and this report.
- A `huggingface_server` alias backed by Ollama is treated as a wrapped runtime path, not as identical to direct Ollama, because it may add hub/router HTTP overhead.
- Comparisons are only apples-to-apples where provider/runtime semantics align; exact resolved runtime artifact details are stored in `environment_snapshot.json` and raw events.

