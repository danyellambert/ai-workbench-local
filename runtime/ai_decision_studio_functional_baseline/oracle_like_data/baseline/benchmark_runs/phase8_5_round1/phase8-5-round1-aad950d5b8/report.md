# Phase 8.5 Round 1 Benchmark Report

- Run ID: `phase8-5-round1-aad950d5b8`
- Total case attempts recorded: **3**
- Latest unique cases considered: **3**
- Total cases: **3**
- Successful cases: **3**
- Failed cases: **0**

## Generation ranking

| Rank | Provider | Model | Success rate | Avg use-case fit | Avg latency (s) |
| --- | --- | --- | ---: | ---: | ---: |
| 1 | `ollama` | `qwen2.5:7b` | 1.0000 | 1.0000 | 10.9924 |

## Embedding ranking

| Rank | Provider | Model | Role | Avg MRR | Avg Hit@1 | Avg retrieval (s) |
| --- | --- | --- | --- | ---: | ---: | ---: |
| 1 | `ollama` | `embeddinggemma:300m` | `baseline` | 0.5000 | 0.5000 | 1.1738 |

## Fairness notes

- Temperature, top_p, max output tokens, context windows, prompt profile, response format, runtime bucket, and quantization family are captured per case.
- Seed is recorded as requested metadata, but not all providers in this repo currently expose a universal deterministic seed control.
- Comparisons are only apples-to-apples where provider/runtime semantics align; exact resolved runtime artifact details are stored in `environment_snapshot.json` and raw events.

