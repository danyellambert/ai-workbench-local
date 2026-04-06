# Phase 5 — Evaluations and Synthetic CV Benchmark

This document records the evaluation and synthetic-benchmark layer that was added during Phase 5 in addition to the initial structured-output foundation.

It should now be read as an **intermediate appendix inside the completed Phase 5 package**, not as the final closure document for the phase.

## 1. What was consolidated during this stage

During this stage, the repository evolved from a structured-output foundation into a broader task-oriented workflow with:

- technical structured-output modules in `src/structured/`
- an initial UI for structured analysis
- explicit separation between:
  - **chat with RAG**
  - **structured analysis**
- automated local smoke evaluation
- an initial synthetic benchmark for `cv_analysis`
- multi-layout synthetic CV generators for testing

## 2. Automated smoke evaluation

Phase 5 introduced a local smoke evaluation through:

- `scripts/run_phase5_structured_eval.py`

That consolidated smoke evaluation passed for:

- `extraction`
- `summary`
- `checklist`
- `cv_analysis`
- `code_analysis`

### Interpretation

This confirmed that the structured layer was already working for:

- schema definition
- parsing
- validation
- basic execution per task

At the same time, this smoke evaluation was never meant to replace validation with real documents or richer layout-oriented benchmarks.

## 3. Separation between chat and structured analysis

An important architectural separation was consolidated during this stage:

- **Chat with RAG** as the conversational flow
- **Structured analysis** as the task- and schema-oriented flow

The document base remained shared, but:

- prompting
- context assembly
- execution
- rendering

were treated as distinct pipelines.

### Why this mattered

This reduced confusion between:

- open conversational answers
- predictable structured artifacts

and made the system easier to evolve as an applied AI platform rather than a single mixed interaction mode.

## 4. Synthetic CV benchmark

This stage also introduced a synthetic benchmark path for `cv_analysis` with:

- realistic synthetic CV generation
- multi-layout CV generation
- automated PDF/JSON pair benchmarking

### Layouts used

The benchmark used layouts such as:

- `classic_one_column`
- `modern_two_column`
- `compact_sidebar`
- `dense_executive`
- `scan_like_image_pdf`

### What the benchmark revealed

The benchmark showed that:

- textual layouts tended to remain mostly in `WARN`
- `scan_like_image_pdf` layouts failed without OCR
- the main bottleneck in `cv_analysis` was not concentrated in name, email, location, or skills
- the harder fields were:
  - `languages`
  - `education`
  - `experience_titles`

## 5. How this benchmark should be interpreted

The synthetic benchmark did **not** mean the Phase 5 structured layer was broken.

Instead, it showed that:

- the structured foundation was already working
- `cv_analysis` could already extract core fields such as:
  - `full_name`
  - `email`
  - `location`
  - `skills`
- but still needed refinement for:
  - `languages`
  - `education`
  - `experience_titles`

### About `scan_like_image_pdf`

The `scan_like_image_pdf` cases should be interpreted as:

- **OCR-needed** cases
- not as unexpected failures of the baseline text-only path

That distinction matters because it points to the correct technical response: improve the document-extraction path rather than misclassify the entire structured pipeline as unstable.

## 6. How this appendix fits after Phase 5 closure

At the time this appendix was first written, Phase 5 still required:

- UI/UX refinement
- validation with real documents
- stronger evidence packaging

Those later steps were completed through the broader Phase 5 package, especially through:

- `docs/PHASE_5_SUMMARY.md`
- `docs/PHASE_5_EVIDENCE_PACK.md`
- `docs/PHASE_5_EVIDENCE_EVAL_REPORT.md`
- `docs/PHASE_5_OCR_FIRST_VL_ON_DEMAND_PRODUCTION_READINESS.md`

So this document should now be read as an intermediate engineering checkpoint that captured the first meaningful eval and benchmark layer inside the completed phase.

## 7. Relevant files and artifacts

### Structured foundation

- `src/structured/`
- `src/ui/structured_outputs.py`
- `main.py`

### Evaluations

- `scripts/run_phase5_structured_eval.py`
- `phase5_eval/reports/`

### Synthetic CV benchmark

- `scripts/run_synthetic_resume_benchmark.py`
- `data/synthetic/resumes_multilayout/`
- `phase5_eval/resume_benchmark*/`

### Synthetic generation helpers

- synthetic resume generation with PDF output
- multi-layout generation
- auxiliary PDF/JSON pair benchmarking

## 8. Conclusion

This appendix records the moment when Phase 5 stopped being only a schema foundation and started to accumulate measurable evidence.

Its main value is historical and architectural:

- it shows when structured outputs first became measurable
- it shows how the project started distinguishing conversational and structured flows
- it shows how synthetic benchmarking identified concrete refinement targets before the broader phase reached closure