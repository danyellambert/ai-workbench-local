# Phase 8.5 Benchmark Report

- Run ID: `phase8-5-matrix-campaign-703f15ab4b`
- Total case attempts recorded: **46**
- Latest unique cases considered: **46**
- Total cases: **46**
- Successful cases: **42**
- Failed cases: **4**

## Generation ranking

| Rank | Provider | Model | Runtime path | Backend | Success rate | Avg use-case fit | Avg latency (s) |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 1 | `huggingface_server` | `qwen2.5:7b-ollama` | `hub_wrapped_runtime` | `ollama::qwen2.5:7b` | 1.0000 | 1.0000 | 8.8160 |
| 2 | `ollama` | `qwen3.5:4b` | `direct_runtime` | `ollama::qwen3.5:4b` | 1.0000 | 1.0000 | 14.7373 |
| 3 | `ollama` | `qwen2.5-coder:7b` | `direct_runtime` | `ollama::qwen2.5-coder:7b` | 1.0000 | 1.0000 | 15.8775 |
| 4 | `ollama` | `phi4-mini:3.8b` | `direct_runtime` | `ollama::phi4-mini:3.8b` | 1.0000 | 0.8750 | 7.7393 |

## Generation operational metrics

| Provider | Model | Avg total wall time (s) | Avg TTFT (s) | Avg throughput (tok/s) | TTFT status counts | Throughput status counts |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `huggingface_server` | `qwen2.5:7b-ollama` | 8.8160 | 8.8153 | 0.0000 | `{"measured": 8}` | `{"not_supported": 8}` |
| `ollama` | `qwen3.5:4b` | 14.7373 | 1.9121 | 15.7018 | `{"measured": 8}` | `{"measured": 8}` |
| `ollama` | `qwen2.5-coder:7b` | 15.8775 | 1.9368 | 16.2823 | `{"measured": 8}` | `{"measured": 8}` |
| `ollama` | `phi4-mini:3.8b` | 7.7393 | 1.1756 | 26.5336 | `{"measured": 8}` | `{"measured": 8}` |

## Embedding ranking

| Rank | Provider | Model | Role | Runtime path | Backend | Avg MRR | Avg Hit@1 | Avg retrieval (s) |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 1 | `ollama` | `bge-m3` | `challenger_general_retrieval` | `direct_runtime` | `ollama::bge-m3:latest` | 1.0000 | 1.0000 | 0.8626 |
| 2 | `ollama` | `embeddinggemma:300m` | `baseline_general_retrieval` | `direct_runtime` | `ollama::embeddinggemma:300m` | 0.9062 | 0.8750 | 0.7704 |
| 3 | `ollama` | `qwen3-embedding:0.6b` | `challenger_general_retrieval` | `direct_runtime` | `ollama::qwen3-embedding:0.6b` | 0.8750 | 0.8750 | 0.8326 |
| 4 | `ollama` | `embeddinggemma:300m` | `baseline_general_retrieval` | `direct_runtime` | `ollama::embeddinggemma:300m` | 0.6667 | 0.6667 | 0.1722 |
| 5 | `huggingface_server` | `embeddinggemma:300m` | `optional_local_hub` | `hub_wrapped_runtime` | `huggingface_local::google/embeddinggemma-300m` | 0.0000 | 0.0000 | 0.0000 |
| 6 | `huggingface_server` | `embeddinggemma:300m` | `optional_local_hub` | `hub_wrapped_runtime` | `huggingface_local::google/embeddinggemma-300m` | 0.0000 | 0.0000 | 0.0000 |

### Embedding subset notes

- `Code retrieval subset`: The code subset currently reuses `ollama::embeddinggemma:300m` as the best available local code fallback because no stronger dedicated code embedding won cleanly in this environment.

## Runtime path breakdown

| Runtime path | Cases | Successful | Failed | Expected overhead | Backend examples |
| --- | ---: | ---: | ---: | --- | --- |
| `direct_runtime` | 30 | 30 | 0 | no | ollama::bge-m3:latest, ollama::embeddinggemma:300m, ollama::phi4-mini:3.8b, ollama::qwen2.5-coder:7b, ollama::qwen3-embedding:0.6b |
| `hub_wrapped_runtime` | 10 | 8 | 2 | yes | huggingface_local::google/embeddinggemma-300m, ollama::qwen2.5:7b |
| `local_native_runtime` | 2 | 0 | 2 | no | huggingface_local::bge-reranker-v2-m3, huggingface_local::jina-reranker-v3-mlx |
| `unknown_runtime_path` | 4 | 4 | 0 | no | - |

## Requested vs resolved model mapping

- Resolution counts: `{"closest_available": 1, "exact": 45}`

| Group | Provider | Requested model | Resolved model | Mapping status | Resolution source |
| --- | --- | --- | --- | --- | --- |
| `embeddings` | `ollama` | `bge-m3` | `bge-m3:latest` | `closest_available` | `provider_inventory` |

## Reranker leaderboard

| Rank | Candidate | Provider | Model | Runtime path | Runtime family | Role | Avg MRR | Avg Hit@1 | Avg retrieval (s) | Avg groundedness proxy |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `hybrid_rerank_current_default` | `ollama` | `embeddinggemma:300m` | `direct_runtime` | `ollama_local` | `current_default` | 0.9062 | 0.8750 | 0.6913 | 0.9062 |
| 2 | `vector_only_local_baseline` | `ollama` | `embeddinggemma:300m` | `direct_runtime` | `ollama_local` | `baseline` | 0.8125 | 0.7500 | 0.7643 | 0.8438 |
| 3 | `neural_rerank_bge_v2_m3` | `huggingface_local` | `bge-reranker-v2-m3` | `local_native_runtime` | `huggingface_local` | `challenger_neural` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 4 | `neural_rerank_jina_v3_mlx` | `huggingface_local` | `jina-reranker-v3-mlx` | `local_native_runtime` | `mlx_local` | `challenger_neural` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## OCR / VLM leaderboard

| Rank | Variant | Runtime family | Avg F1 | Avg latency (s) | Helped cases |
| --- | --- | --- | ---: | ---: | ---: |
| 1 | `evidence_with_vl` | `ollama_local` | 0.7500 | 2.4790 | 4 |
| 2 | `evidence_no_vl_docling_disabled` | `huggingface_local` | 0.7500 | 2.5584 | 4 |
| 3 | `evidence_no_vl` | `huggingface_local` | 0.7500 | 2.8014 | 4 |
| 4 | `pdf_hybrid` | `pdf_hybrid_local` | 0.2500 | 0.0251 | 0 |
| 5 | `legacy_pdf` | `legacy_pdf_text_extraction` | 0.2500 | 0.0414 | 0 |
| 6 | `pdf_complete` | `pdf_complete_local` | 0.2292 | 9.6686 | 0 |

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

