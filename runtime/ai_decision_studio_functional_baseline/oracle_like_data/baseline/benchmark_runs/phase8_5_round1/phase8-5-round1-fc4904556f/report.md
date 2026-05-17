# Phase 8.5 Round 1 Benchmark Report

- Run ID: `phase8-5-round1-fc4904556f`
- Total case attempts recorded: **2**
- Latest unique cases considered: **2**
- Total cases: **2**
- Successful cases: **2**
- Failed cases: **0**

## Generation ranking

| Rank | Provider | Model | Success rate | Avg use-case fit | Avg latency (s) |
| --- | --- | --- | ---: | ---: | ---: |
| 1 | `ollama` | `qwen2.5:7b` | 1.0000 | 1.0000 | 8.7774 |

## Embedding ranking

| Rank | Provider | Model | Role | Avg MRR | Avg Hit@1 | Avg retrieval (s) |
| --- | --- | --- | --- | ---: | ---: | ---: |

## Fairness notes

- Temperature, top_p, max output tokens, context windows, prompt profile, response format, runtime bucket, and quantization family are captured per case.
- Seed is recorded as requested metadata, but not all providers in this repo currently expose a universal deterministic seed control.
- Comparisons are only apples-to-apples where provider/runtime semantics align; exact resolved runtime artifact details are stored in `environment_snapshot.json` and raw events.

