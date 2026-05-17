# Phase 8.5 Decision Gate Report

- Benchmark run: `phase8-5-matrix-campaign-703f15ab4b`
- Benchmark directory: `baseline://workspace/benchmark_runs/phase8_5_matrix_campaigns/phase8-5-matrix-campaign-703f15ab4b`
- Global adaptation recommendation: `defer_adaptation_until_runtime_and_retrieval_changes_are_exhausted`

## Decision matrix by use case

| Use case | Task type | Best local candidate | Runtime/model change enough? | Prompt+RAG+schema status | Adaptation status |
| --- | --- | --- | --- | --- | --- |
| `code_quality_review` | `code_analysis` | `huggingface_server::qwen2.5:7b-ollama` | `True` | `needs_iteration` | `iterate_before_adaptation` |
| `cv_structured_extraction` | `extraction` | `huggingface_server::qwen2.5:7b-ollama` | `True` | `needs_iteration` | `iterate_before_adaptation` |
| `ops_update_summary` | `summary` | `ollama::phi4-mini:3.8b` | `False` | `needs_iteration` | `iterate_before_adaptation` |
| `release_candidate_risk_review` | `checklist` | `ollama::phi4-mini:3.8b` | `False` | `needs_iteration` | `iterate_before_adaptation` |

## Runtime / model conclusions

- Runtime/model change recommended for any use case: `True`
- `code_quality_review` → best local candidate `huggingface_server::qwen2.5:7b-ollama`; change decision: `change_recommended` (quality_held_with_latency_gain).
- `cv_structured_extraction` → best local candidate `huggingface_server::qwen2.5:7b-ollama`; change decision: `change_recommended` (quality_gain_clear_enough).
- `ops_update_summary` → best local candidate `ollama::phi4-mini:3.8b`; change decision: `current_baseline_sufficient` (baseline_remains_best).
- `release_candidate_risk_review` → best local candidate `ollama::phi4-mini:3.8b`; change decision: `current_baseline_sufficient` (baseline_remains_best).

## Retrieval conclusions

- Best embedding strategy: `ollama::bge-m3::general_retrieval`
- Embedding change recommended: `True` (quality_gain_clear_enough)
- Best reranker tradeoff: `hybrid_rerank_current_default`
- Reranker change recommended: `False` (baseline_remains_best)

## Supporting OCR / VLM observations

- Best OCR fallback tradeoff: `evidence_no_vl`
- Best VLM fallback tradeoff: `evidence_with_vl`

## Adaptation not needed yet

- `langgraph_guardrails` → `prompt_rag_schema_sufficient`
- `document_agent_routing` → `prompt_rag_schema_sufficient`
- `cv_analysis` → `prompt_rag_schema_sufficient`
- `extraction` → `non_training_alternatives_remaining`
- `cv_contacts` → `non_training_alternatives_remaining`

## Adaptation candidates

- No lightweight adaptation candidate is justified yet from the current benchmark + eval evidence.

## Conservative conclusion

- This round does not implement full fine-tuning or training jobs.
- Runtime/model swaps are considered first for use-case-level wins.
- Embedding and reranker changes are considered before any adaptation recommendation for retrieval-sensitive tasks.
- Lightweight adaptation is only justified when eval failures persist and benchmark evidence does not show a clearer non-training path.

