# Phase 8.5 Expanded Completion Roadmap

This document defines the remaining work required to upgrade Phase 8.5 from the current **technically closed local benchmark framework** into the broader **fully automated, reproducible local benchmarking system** described in the expanded prompt.

It is intentionally conservative:

- reuse the existing benchmark/eval architecture already in the repository
- avoid rebuilding the stack from scratch
- prefer local execution only
- never fake benchmark results
- never silently substitute a different model without logging the substitution

## 1. Current state

The repository already has a real Phase 8.5 benchmark foundation:

- [x] resumable manifest-driven benchmark execution
- [x] raw / normalized / aggregated outputs
- [x] environment and runtime snapshots
- [x] generation / embeddings / rerankers / OCR-VLM slices
- [x] audit / decision gate / closure artifacts
- [x] requested-vs-resolved model mapping for the benchmark matrix currently configured

At this point, the remaining work for the **expanded** target is mostly about **optional evidence amplification**, not missing core architecture. The repository now already covers the expanded local scope through:

1. explicit runtime-family/requested-vs-resolved handling
2. deeper operational runtime metrics
3. reranker and OCR/VLM expansion slices
4. a merged staged-campaign execution path for grouped evidence bundles

## 2. What “fully complete” means for the expanded Phase 8.5 scope

Phase 8.5 should only be considered fully complete against the expanded prompt when all of the following are true:

### A. Generation runtime matrix

- [x] the requested generation families are represented in the manifest
- [x] the benchmark can resolve them to exact or closest available local artifacts
- [x] Ollama vs HF-local / HF-service / MLX-local comparisons are explicit where the runtime path is clean in this repo
- [x] requested-vs-resolved runtime/model mapping is visible in reports

### B. Embedding matrix

- [x] the general embedding baseline and challengers are benchmarked
- [x] the code-subset embedding comparison is benchmarked explicitly
- [x] requested-vs-resolved embedding substitutions are logged honestly

### C. Reranker matrix

- [x] the current hybrid / non-neural baseline remains benchmarked
- [x] neural rerankers are benchmarked when locally available through a clean adapter path
- [x] unimplemented or missing runtime families are marked as `skipped`, not silently ignored

### D. OCR / VLM fallback matrix

- [x] the current `hybrid` and `complete` paths remain benchmarked
- [x] stronger local VLM / OCR challengers are benchmarked when installed and supported cleanly
- [x] reports explain when the fallback actually helped and what the latency tradeoff was

### E. Operational metrics

- [x] cold start latency when measurable
- [x] warm start latency when measurable
- [x] TTFT when stream semantics make it measurable
- [x] total wall time
- [x] throughput when supported
- [x] memory snapshot / peak estimate when supported
- [x] every metric explicitly marked as:
  - [x] `measured`
  - [x] `estimated`
  - [x] `not_supported`

### F. Final evidence bundle

- [x] smoke path passes
- [x] full matrix has a documented execution order
- [x] audit, decision gate, and closure are rerun after the expanded slices land
- [x] docs clearly state what is supported, what is intentionally skipped, and why

## 3. Work packages to finish the phase

## Work package A — runtime-family normalization and inventory hardening

### Goal

Turn the current partial HF runtime handling into explicit, reproducible runtime-family support.

### Tasks

- [x] inventory the actual local runtime families visible to the repo
  - [x] `ollama`
  - [x] `huggingface_local`
  - [x] `huggingface_server`
  - [x] MLX-local equivalents when the environment exposes them cleanly
- [x] distinguish requested vs resolved runtime family, not only requested vs resolved model
- [x] harden provider/runtime metadata so reports show:
  - [x] requested runtime family
  - [x] resolved runtime family
  - [x] requested model
  - [x] resolved model
  - [x] mapping reason
- [x] verify chat-template fairness for HF-local paths before comparing against Ollama
- [x] reproduce and resolve the `embeddinggemma` / `hf_local_llm_service` mismatch seen during Phase 8.5 benchmarking

Notes:

- HF-local fairness is now surfaced explicitly through `prompt_serialization_mode`, `chat_template_used`, and `chat_template_source` in benchmark events/results. On the current machine, no clean `huggingface_local` provider path is active in the registry, so no unfair HF-local-vs-Ollama comparison remains in the evidence bundle.
- The `embeddinggemma` via `hf_local_llm_service` discrepancy was reproduced and explained: the local hub exposes the alias, but the current environment can still block the backend embedding path under memory preflight. This is now an explicit support boundary rather than an unexplained mismatch.

### Definition of done

- no ambiguous “HF local” comparison remains in the benchmark logs
- runtime family labels are explicit and stable
- the `embeddinggemma` discrepancy is explained or fixed and documented

## Work package B — operational runtime metrics

### Goal

Add stronger benchmark metrics without inventing precision that some backends cannot provide.

### Tasks

- [x] define a small metric contract per benchmark case for:
  - [x] cold-start wall time
  - [x] warm-start wall time
  - [x] TTFT
  - [x] total wall time
  - [x] throughput
  - [x] memory snapshot / peak estimate
- [x] implement collection wrappers per provider/runtime where possible
- [x] mark unsupported metrics explicitly instead of leaving silent gaps
- [x] expose those metrics in:
  - [x] raw events
  - [x] normalized CSVs
  - [x] aggregated summaries
  - [x] markdown report

### Definition of done

- metrics are visible and honest across the benchmark output stack
- unsupported metrics are explicit instead of implied

## Work package C — embedding expansion

### Goal

Finish the expanded embedding benchmark target for both general retrieval and code retrieval.

### Tasks

- [x] benchmark the currently configured general retrieval candidates
- [x] add stronger locally available HF/MLX-style embedding challengers when cleanly executable
- [x] add an explicit code-subset evaluation slice
- [x] document when a general embedding is being reused as the best available code fallback

### Definition of done

- the benchmark can answer:
  - best general local embedding
  - best code-subset local embedding

## Work package D — neural reranker expansion

### Goal

Go beyond the current repository hybrid baseline without turning reranking into a giant platform rewrite.

### Tasks

- [x] define a small reranker adapter interface for local challengers
- [x] integrate only locally available reranker models that already have a clean path in the environment
- [x] benchmark:
  - [x] current baseline / vector-only
  - [x] current hybrid rerank path
  - [x] neural reranker challengers when actually available
- [x] preserve `skipped` results for unavailable or unsupported challengers

### Definition of done

- the benchmark can answer the best reranker tradeoff on this machine with explicit support boundaries

## Work package E — OCR / VLM expanded fallback matrix

### Goal

Turn the current real-but-bounded OCR/VLM slice into a broader local fallback comparison.

### Tasks

- [x] keep `hybrid` and `complete` as baseline paths
- [x] add explicit benchmarked local fallbacks when installed and cleanly supported
- [x] compare base path vs fallback on gold-backed difficult PDFs
- [x] record:
  - [x] field-level quality deltas
  - [x] latency cost
  - [x] whether the fallback actually helped

### Definition of done

- the benchmark can answer the best local OCR/VLM fallback strategy with honest caveats

## Work package F — rerun, reports, and final closure

### Goal

Re-run the evidence bundle once the missing slices are implemented.

### Tasks

- [x] rerun preflight
- [x] rerun smoke
- [x] rerun the expanded full matrix in staged groups
- [x] regenerate:
  - [x] audit
  - [x] decision gate
  - [x] closure
- [x] confirm that the final closure statement matches the expanded benchmark scope rather than the smaller current local slice only

### Definition of done

- the expanded benchmark scope is supported and evidenced
- final docs no longer describe those items as pending

Current support-boundary note:

- The repo now supports a merged staged campaign via `scripts/run_phase8_5_benchmark_matrix.py --staged-campaign`.
- A corrected staged smoke bundle was generated at `benchmark_runs/phase8_5_matrix_campaigns/phase8-5-matrix-campaign-3095054546`.
- A larger non-smoke staged bundle was also generated at `benchmark_runs/phase8_5_matrix_campaigns/phase8-5-matrix-campaign-703f15ab4b`, and audit / decision gate / closure were regenerated against it.

## 4. Recommended execution order on a 16 GB Apple Silicon machine

Recommended order:

1. preflight all groups
2. smoke run all groups
3. generation full run
4. embeddings full run
5. rerankers full run
6. OCR / VLM full run
7. decision gate
8. closure

This avoids forcing the heaviest retrieval/document slices to run at the same time as the most unstable runtime experiments.

## 5. Rules for honest completion

The expanded Phase 8.5 is still allowed to mark individual candidates as:

- `exact`
- `closest_available`
- `skipped`

That is still considered valid completion **if**:

- the requested target is preserved in the logs
- the resolved artifact is preserved in the logs
- the mapping reason is preserved in the logs
- the final report explains the limitation clearly

It is **not** considered complete if a runtime family is claimed as supported while still lacking a clean executable path in the repository.

## 6. Final completion criterion

For the expanded prompt, Phase 8.5 should be considered complete only when:

- the current benchmark foundation is preserved
- runtime-family coverage is explicit and fair enough
- requested-vs-resolved substitutions are fully auditable
- operational metrics are materially richer than simple wall-time only
- neural reranker and OCR/VLM expansions are either implemented or explicitly skipped with evidence-backed reasons
- the final closure report can truthfully say the expanded local benchmark scope is complete on this machine

Optional follow-up, if you want even stronger evidence later:

- rerun a fresh non-smoke staged campaign after changing the local provider inventory or benchmark manifest, to compare against the current stronger evidence bundle
