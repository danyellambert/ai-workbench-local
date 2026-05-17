# Phase 8.5 Benchmark Report

- Run ID: `phase8-5-matrix-8bd1c776d7`
- Total case attempts recorded: **6**
- Latest unique cases considered: **6**
- Total cases: **6**
- Successful cases: **4**
- Failed cases: **2**

## Generation ranking

| Rank | Provider | Model | Runtime path | Backend | Success rate | Avg use-case fit | Avg latency (s) |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |

## Generation operational metrics

| Provider | Model | Avg total wall time (s) | Avg TTFT (s) | Avg throughput (tok/s) | TTFT status counts | Throughput status counts |
| --- | --- | ---: | ---: | ---: | --- | --- |

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
| `direct_runtime` | 4 | 4 | 0 | no | ollama::bge-m3:latest, ollama::embeddinggemma:300m, ollama::qwen3-embedding:0.6b |
| `hub_wrapped_runtime` | 2 | 0 | 2 | yes | huggingface_local::google/embeddinggemma-300m |

## Requested vs resolved model mapping

- Resolution counts: `{"closest_available": 1, "exact": 5}`

| Group | Provider | Requested model | Resolved model | Mapping status | Resolution source |
| --- | --- | --- | --- | --- | --- |
| `embeddings` | `ollama` | `bge-m3` | `bge-m3:latest` | `closest_available` | `provider_inventory` |

## Fairness notes

- Temperature, top_p, max output tokens, context windows, prompt profile, response format, runtime bucket, and quantization family are captured per case.
- Seed is recorded as requested metadata, but not all providers in this repo currently expose a universal deterministic seed control.
- Direct runtimes and hub-wrapped runtimes are now distinguished explicitly in the raw events, normalized tables, aggregated summaries, and this report.
- A `huggingface_server` alias backed by Ollama is treated as a wrapped runtime path, not as identical to direct Ollama, because it may add hub/router HTTP overhead.
- Comparisons are only apples-to-apples where provider/runtime semantics align; exact resolved runtime artifact details are stored in `environment_snapshot.json` and raw events.

