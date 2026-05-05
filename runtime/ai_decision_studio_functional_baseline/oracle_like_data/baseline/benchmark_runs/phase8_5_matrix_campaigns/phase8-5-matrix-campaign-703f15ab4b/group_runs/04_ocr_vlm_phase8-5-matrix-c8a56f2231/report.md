# Phase 8.5 Benchmark Report

- Run ID: `phase8-5-matrix-c8a56f2231`
- Total case attempts recorded: **4**
- Latest unique cases considered: **4**
- Total cases: **4**
- Successful cases: **4**
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
| `unknown_runtime_path` | 4 | 4 | 0 | no | - |

## Requested vs resolved model mapping

- Resolution counts: `{"exact": 4}`
- No requested-vs-resolved substitutions were needed for the latest case results.

## Reranker leaderboard

| Rank | Candidate | Provider | Model | Runtime path | Runtime family | Role | Avg MRR | Avg Hit@1 | Avg retrieval (s) | Avg groundedness proxy |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |

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

- Best reranker tradeoff: `n/a`
- Best OCR fallback tradeoff: `evidence_no_vl`
- Best VLM fallback tradeoff: `evidence_with_vl`
- Support is intentionally incremental: reranker comparisons are fully local and executable; OCR/VLM comparisons focus on reusable CV/contact-evidence slices already present in the repo.


## Fairness notes

- Temperature, top_p, max output tokens, context windows, prompt profile, response format, runtime bucket, and quantization family are captured per case.
- Seed is recorded as requested metadata, but not all providers in this repo currently expose a universal deterministic seed control.
- Direct runtimes and hub-wrapped runtimes are now distinguished explicitly in the raw events, normalized tables, aggregated summaries, and this report.
- A `huggingface_server` alias backed by Ollama is treated as a wrapped runtime path, not as identical to direct Ollama, because it may add hub/router HTTP overhead.
- Comparisons are only apples-to-apples where provider/runtime semantics align; exact resolved runtime artifact details are stored in `environment_snapshot.json` and raw events.

