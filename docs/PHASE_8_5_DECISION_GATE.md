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

The markdown report is designed to be interview-defendable.

It includes:

- use-case decision matrix
- runtime/model conclusions
- retrieval conclusions
- OCR/VLM supporting observations
- `Adaptation not needed yet`
- `Adaptation candidates`
- explicit conservative conclusion

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

## Interview framing

The strongest way to defend this phase is:

- I did not jump directly to fine-tuning.
- I first separated runtime/model wins from retrieval wins.
- I used eval diagnosis to prove where the current stack is sufficient.
- I only keep adaptation as a narrow, explicit candidate when the simpler levers are not enough.