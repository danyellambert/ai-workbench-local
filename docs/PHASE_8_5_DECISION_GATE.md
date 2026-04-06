# Phase 8.5 Decision Gate

This document describes the **Round 3 decision layer** for Phase 8.5.

The goal is **not** to turn the repository into a generic training platform.
The goal is to convert benchmark + eval evidence into a conservative decision framework that answers:

- when prompt + RAG + schema are already sufficient
- when runtime/model change is enough
- when embedding/reranker change is enough
- when lightweight adaptation might actually be justified

## Inputs used by the decision layer

The Round 3 decision layer reuses existing repository artifacts:

- Phase 8.5 benchmark outputs
  - `aggregated/summary.json`
  - `aggregated/latest_case_results.json`
  - `manifest.resolved.json`
  - `preflight.json`
- Phase 8 eval store / diagnosis
  - `.phase8_eval_runs.sqlite3`
  - `src/storage/phase8_eval_store.py`
  - `src/storage/phase8_eval_diagnosis.py`

This decision layer is also consumed by the final closure bundle:

- `scripts/report_phase8_5_closure.py`
- `docs/PHASE_8_5_CLOSURE.md`

## Conservative decision order

The repo now follows this order before suggesting any adaptation:

1. **Prompt + RAG + schema sufficient?**
   - If eval diagnosis marks a task as healthy, adaptation is not needed yet.

2. **Runtime/model swap enough?**
   - Round 3 computes a use-case-level local runtime matrix.
   - A runtime/model swap is only recommended when the quality gain is clear enough, or quality is preserved with a meaningful latency gain.

3. **Embedding/reranker change enough?**
   - Round 3 evaluates whether the top embedding strategy or reranker tradeoff beats the baseline by enough signal to justify a non-training change first.

4. **Adaptation justified?**
   - Adaptation is only justified when eval failures persist **and** benchmark evidence does not show a clearer non-training path.

## Why this stays conservative

- No full fine-tuning jobs are added in this round.
- No heavy LoRA/PEFT pipeline is created here.
- The output includes a **future experiment outline only** when a task is a serious candidate.
- If runtime/retrieval alternatives are still promising, the decision layer explicitly defers adaptation.

## Machine-readable output

The Round 3 script produces a JSON summary containing:

- `runtime_model_decisions`
- `embedding_decisions`
- `reranker_decisions`
- `ocr_vlm_observations`
- `adaptation_decision`
- `decision_matrix`

Important sections:

- `decision_matrix`
  - compact by-use-case view
- `adaptation_not_needed_yet`
  - healthy or still-better-served-by-non-training tasks
- `adaptation_candidates`
  - narrow tasks where lightweight adaptation may be justified

## Markdown report

The markdown report is designed to be operationally clear, auditable, and reusable.

It includes:

- use-case decision matrix
- runtime/model conclusions
- retrieval conclusions
- OCR/VLM supporting observations
- `Adaptation not needed yet`
- `Adaptation candidates`
- explicit conservative conclusion

## Final chosen stack from the completed non-smoke evidence bundle

The canonical final evidence bundle for Phase 8.5 is now the **completed non-smoke staged campaign**:

- benchmark run dir:
  - `benchmark_runs/phase8_5_matrix_campaigns/phase8-5-matrix-campaign-703f15ab4b/`
- machine-readable decision summary:
  - `phase5_eval/reports/phase8_5_decision_summary.json`
- closure summary:
  - `phase5_eval/reports/phase8_5_closure_summary.json`

This is the bundle that should be cited when someone asks:

- which models performed best
- which retrieval stack was chosen
- whether reranker/OCR/VLM changes were worth it
- whether adaptation was justified

## Final stack at a glance

### Visual summary table

| Area | Use case / scope | Final choice | Decision signal | Why it won |
| --- | --- | --- | --- | --- |
| 🟢 Generation | `ops_update_summary` | `ollama::phi4-mini:3.8b` | `baseline_remains_best` | Best simplicity/latency tradeoff with quality already sufficient |
| 🟢 Generation | `release_candidate_risk_review` | `ollama::phi4-mini:3.8b` | `baseline_remains_best` | Strong enough baseline for checklist/risk-review without justified swap |
| 🟢 Generation | `code_quality_review` | `huggingface_server::qwen2.5:7b-ollama` | `quality_held_with_latency_gain` | Preserved quality while improving latency vs baseline |
| 🟢 Generation | `cv_structured_extraction` | `huggingface_server::qwen2.5:7b-ollama` | `quality_gain_clear_enough` | Strongest extraction-quality tradeoff in the final bundle |
| 🔵 Embeddings | General retrieval | `ollama::bge-m3` | `quality_gain_clear_enough` | Best final retrieval strategy in the non-smoke bundle |
| 🟣 Reranking | Retrieval reranking | `hybrid_rerank_current_default` | `baseline_remains_best` | Hybrid default remained the most defendable tradeoff |
| 🟠 OCR fallback | Conservative OCR escalation | `evidence_no_vl` | best OCR tradeoff | Improved quality without paying VLM cost by default |
| 🟡 VLM fallback | Heavier escalation only when justified | `evidence_with_vl` | best VLM tradeoff | Best VLM-backed option when escalation really helps |

### Official stack decision table

| If the task is... | Prefer this stack | Practical interpretation |
| --- | --- | --- |
| Summary / executive update | `ollama::phi4-mini:3.8b` | Fast, simple, good enough without overpaying in latency |
| Risk review / checklist | `ollama::phi4-mini:3.8b` | Baseline remains sufficient for this slice |
| Code review | `huggingface_server::qwen2.5:7b-ollama` | Better runtime/model tradeoff for technical review |
| Structured extraction | `huggingface_server::qwen2.5:7b-ollama` | Strongest final structured-output performer |
| General retrieval embeddings | `ollama::bge-m3` | Best chosen embedding strategy from the final bundle |
| Reranking | `hybrid_rerank_current_default` | Keep the current hybrid default |
| OCR fallback | `evidence_no_vl` | Conservative escalation path |
| VLM fallback | `evidence_with_vl` | Use only when heavier escalation is justified |

### 1. Generation choices by use case

There was **no single universal winner** across all generation tasks. The final decision is intentionally **use-case-specific**.

#### A. Best choice for `code_quality_review`

- chosen stack:
  - `huggingface_server::qwen2.5:7b-ollama`
- why:
  - preserved top use-case fit and format adherence
  - delivered a meaningful latency gain versus the local lightweight baseline
  - therefore counted as a runtime/model change worth recommending

#### B. Best choice for `cv_structured_extraction`

- chosen stack:
  - `huggingface_server::qwen2.5:7b-ollama`
- why:
  - held the strongest overall extraction performance in the final bundle
  - showed a clear improvement on the decision criteria used by Round 3
  - beat the relevant local baseline strongly enough to justify the swap

#### C. Best choice for `ops_update_summary`

- chosen stack:
  - `ollama::phi4-mini:3.8b`
- why:
  - the baseline remained sufficient
  - no stronger alternative produced enough additional value to justify a switch
  - it kept the best tradeoff between simplicity, latency, and output quality for this summary-style use case

#### D. Best choice for `release_candidate_risk_review`

- chosen stack:
  - `ollama::phi4-mini:3.8b`
- why:
  - the baseline remained best enough for the checklist/risk-review slice
  - other candidates did not clear the Round 3 threshold for a justified switch

### 2. Embedding choice

- chosen stack:
  - `ollama::bge-m3::general_retrieval`
- why:
  - the final decision layer selected it as the best embedding strategy in the completed non-smoke bundle
  - this is a strong example of why Phase 8.5 did **not** jump directly to adaptation: retrieval quality still moved materially by changing embeddings alone

### 3. Reranker choice

- chosen stack:
  - `hybrid_rerank_current_default`
- why:
  - it remained the best reranker tradeoff in the final decision output
  - this means the currently integrated hybrid reranking path was still the most defendable choice versus the available challengers
  - the conclusion is not “neural rerankers never matter,” but rather “the current hybrid default is still the best supported choice on this machine and evidence bundle”

### 4. OCR / VLM choices

#### A. Best OCR fallback tradeoff

- chosen stack:
  - `evidence_no_vl`
- why:
  - it was the strongest conservative OCR fallback tradeoff in the final evidence bundle
  - it improved quality without requiring the heavier VLM path by default

#### B. Best VLM fallback tradeoff

- chosen stack:
  - `evidence_with_vl`
- why:
  - it was the strongest VLM-backed slice when that heavier path was justified
  - the Phase 8.5 conclusion is therefore **conditional use of VLM**, not “always use VLM”

## Official Phase 8.5 stack decision

If you need one short, canonical summary of the final choices, use this:

- for **summary** and **risk-review/checklist** style tasks:
  - prefer `ollama::phi4-mini:3.8b`
- for **code review** and **structured extraction** style tasks:
  - prefer `huggingface_server::qwen2.5:7b-ollama`
- for **general retrieval embeddings**:
  - prefer `ollama::bge-m3`
- for **reranking**:
  - prefer `hybrid_rerank_current_default`
- for **OCR fallback**:
  - prefer `evidence_no_vl`
- for **VLM fallback when escalation is justified**:
  - prefer `evidence_with_vl`

## Why this decision is stronger than “one model won everything”

The most important conclusion of the phase is not that one model dominated all tasks.
The more defensible conclusion is:

> the best stack is **task-specific**, and the engineering decision should be made per use case rather than by chasing a single universal winner.

That is exactly why the repo now records the decision matrix by use case instead of pretending that one benchmark score settles the whole system.

## Minimal scaffold when adaptation is justified

When the evidence is strong enough, the repo now exports a **validated adaptation scaffold** in the closure bundle.

That scaffold records:

- task scope
- failure pattern
- baseline quality
- target quality
- primary success metric
- scope constraints for a future minimal LoRA/PEFT experiment

This still does **not** execute training jobs in this phase.

## Minimal adaptation candidate framework

When a task becomes a real candidate, the repo records a **small experiment outline** only:

- candidate task
- failure pattern
- current baseline quality
- target quality
- why prompt/RAG/retrieval were not enough
- what a minimal future LoRA/PEFT experiment would target

This is a decision artifact, **not** a training pipeline.

## Recommended interpretation

The strongest interpretation of this phase is:

- adaptation was not treated as the default answer
- runtime/model wins were separated from retrieval wins
- eval diagnosis was used to identify where the current stack was already sufficient
- adaptation remains a narrow and explicit candidate only when simpler levers are not enough
- the final stack is documented by use case because the correct outcome was task-specific rather than a single universal winner