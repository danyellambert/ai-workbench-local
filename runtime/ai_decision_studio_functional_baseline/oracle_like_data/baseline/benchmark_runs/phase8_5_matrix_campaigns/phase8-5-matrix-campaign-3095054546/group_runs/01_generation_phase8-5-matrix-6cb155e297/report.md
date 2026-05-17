# Phase 8.5 Benchmark Report

- Run ID: `phase8-5-matrix-6cb155e297`
- Total case attempts recorded: **2**
- Latest unique cases considered: **2**
- Total cases: **2**
- Successful cases: **2**
- Failed cases: **0**

## Generation ranking

| Rank | Provider | Model | Runtime path | Backend | Success rate | Avg use-case fit | Avg latency (s) |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 1 | `ollama` | `qwen3.5:4b` | `direct_runtime` | `ollama::qwen3.5:4b` | 1.0000 | 1.0000 | 9.9082 |

## Generation operational metrics

| Provider | Model | Avg total wall time (s) | Avg TTFT (s) | Avg throughput (tok/s) | TTFT status counts | Throughput status counts |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `ollama` | `qwen3.5:4b` | 9.9082 | 3.2036 | 13.0309 | `{"measured": 2}` | `{"measured": 2}` |

## Embedding ranking

| Rank | Provider | Model | Role | Runtime path | Backend | Avg MRR | Avg Hit@1 | Avg retrieval (s) |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |

## Runtime path breakdown

| Runtime path | Cases | Successful | Failed | Expected overhead | Backend examples |
| --- | ---: | ---: | ---: | --- | --- |
| `direct_runtime` | 2 | 2 | 0 | no | ollama::qwen3.5:4b |

## Requested vs resolved model mapping

- Resolution counts: `{"exact": 2}`
- No requested-vs-resolved substitutions were needed for the latest case results.

## Fairness notes

- Temperature, top_p, max output tokens, context windows, prompt profile, response format, runtime bucket, and quantization family are captured per case.
- Seed is recorded as requested metadata, but not all providers in this repo currently expose a universal deterministic seed control.
- Direct runtimes and hub-wrapped runtimes are now distinguished explicitly in the raw events, normalized tables, aggregated summaries, and this report.
- A `huggingface_server` alias backed by Ollama is treated as a wrapped runtime path, not as identical to direct Ollama, because it may add hub/router HTTP overhead.
- Comparisons are only apples-to-apples where provider/runtime semantics align; exact resolved runtime artifact details are stored in `environment_snapshot.json` and raw events.

