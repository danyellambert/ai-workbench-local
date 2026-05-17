# Phase 8.5 Benchmark Report

- Run ID: `phase8-5-matrix-campaign-3095054546`
- Total case attempts recorded: **6**
- Latest unique cases considered: **6**
- Total cases: **6**
- Successful cases: **6**
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
| 1 | `ollama` | `embeddinggemma:300m` | `baseline_general_retrieval` | `direct_runtime` | `ollama::embeddinggemma:300m` | 0.5000 | 0.5000 | 0.1586 |
| 2 | `ollama` | `embeddinggemma:300m` | `baseline_general_retrieval` | `direct_runtime` | `ollama::embeddinggemma:300m` | 0.5000 | 0.5000 | 0.6989 |

### Embedding subset notes

- `Code retrieval subset`: The code subset currently reuses `ollama::embeddinggemma:300m` as the best available local code fallback because no stronger dedicated code embedding won cleanly in this environment.

## Runtime path breakdown

| Runtime path | Cases | Successful | Failed | Expected overhead | Backend examples |
| --- | ---: | ---: | ---: | --- | --- |
| `direct_runtime` | 5 | 5 | 0 | no | ollama::embeddinggemma:300m, ollama::qwen3.5:4b |
| `unknown_runtime_path` | 1 | 1 | 0 | no | - |

## Requested vs resolved model mapping

- Resolution counts: `{"exact": 6}`
- No requested-vs-resolved substitutions were needed for the latest case results.

## Reranker leaderboard

| Rank | Candidate | Provider | Model | Runtime path | Runtime family | Role | Avg MRR | Avg Hit@1 | Avg retrieval (s) | Avg groundedness proxy |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `vector_only_local_baseline` | `ollama` | `embeddinggemma:300m` | `direct_runtime` | `ollama_local` | `baseline` | 0.5000 | 0.5000 | 0.6028 | 0.5000 |

## OCR / VLM leaderboard

| Rank | Variant | Runtime family | Avg F1 | Avg latency (s) | Helped cases |
| --- | --- | --- | ---: | ---: | ---: |
| 1 | `evidence_with_vl` | `ollama_local` | 1.0000 | 0.5099 | 1 |
| 2 | `evidence_no_vl_docling_disabled` | `huggingface_local` | 1.0000 | 0.5351 | 1 |
| 3 | `evidence_no_vl` | `huggingface_local` | 1.0000 | 1.3580 | 1 |
| 4 | `legacy_pdf` | `legacy_pdf_text_extraction` | 0.2500 | 0.0380 | 0 |
| 5 | `pdf_hybrid` | `pdf_hybrid_local` | 0.2500 | 0.0391 | 0 |
| 6 | `pdf_complete` | `pdf_complete_local` | 0.2500 | 14.2009 | 0 |

## Round 2 tradeoff notes

- Best reranker tradeoff: `vector_only_local_baseline`
- Best OCR fallback tradeoff: `evidence_no_vl`
- Best VLM fallback tradeoff: `evidence_with_vl`
- Support is intentionally incremental: reranker comparisons are fully local and executable; OCR/VLM comparisons focus on reusable CV/contact-evidence slices already present in the repo.


## Fairness notes

- Temperature, top_p, max output tokens, context windows, prompt profile, response format, runtime bucket, and quantization family are captured per case.
- Seed is recorded as requested metadata, but not all providers in this repo currently expose a universal deterministic seed control.
- Direct runtimes and hub-wrapped runtimes are now distinguished explicitly in the raw events, normalized tables, aggregated summaries, and this report.
- A `huggingface_server` alias backed by Ollama is treated as a wrapped runtime path, not as identical to direct Ollama, because it may add hub/router HTTP overhead.
- Comparisons are only apples-to-apples where provider/runtime semantics align; exact resolved runtime artifact details are stored in `environment_snapshot.json` and raw events.

