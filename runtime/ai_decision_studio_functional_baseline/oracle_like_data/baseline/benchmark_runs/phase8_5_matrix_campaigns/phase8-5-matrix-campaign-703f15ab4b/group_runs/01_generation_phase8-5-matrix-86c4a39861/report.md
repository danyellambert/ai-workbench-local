# Phase 8.5 Benchmark Report

- Run ID: `phase8-5-matrix-86c4a39861`
- Total case attempts recorded: **32**
- Latest unique cases considered: **32**
- Total cases: **32**
- Successful cases: **32**
- Failed cases: **0**

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

## Runtime path breakdown

| Runtime path | Cases | Successful | Failed | Expected overhead | Backend examples |
| --- | ---: | ---: | ---: | --- | --- |
| `direct_runtime` | 24 | 24 | 0 | no | ollama::phi4-mini:3.8b, ollama::qwen2.5-coder:7b, ollama::qwen3.5:4b |
| `hub_wrapped_runtime` | 8 | 8 | 0 | yes | ollama::qwen2.5:7b |

## Requested vs resolved model mapping

- Resolution counts: `{"exact": 32}`
- No requested-vs-resolved substitutions were needed for the latest case results.

## Fairness notes

- Temperature, top_p, max output tokens, context windows, prompt profile, response format, runtime bucket, and quantization family are captured per case.
- Seed is recorded as requested metadata, but not all providers in this repo currently expose a universal deterministic seed control.
- Direct runtimes and hub-wrapped runtimes are now distinguished explicitly in the raw events, normalized tables, aggregated summaries, and this report.
- A `huggingface_server` alias backed by Ollama is treated as a wrapped runtime path, not as identical to direct Ollama, because it may add hub/router HTTP overhead.
- Comparisons are only apples-to-apples where provider/runtime semantics align; exact resolved runtime artifact details are stored in `environment_snapshot.json` and raw events.

