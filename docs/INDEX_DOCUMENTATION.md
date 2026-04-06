# Documentation Index

This file is the main entry point for the repository documentation.

## Reading order

1. `README.md`
2. `ROADMAP.md`
3. `docs/PROJECT_POSITIONING_TWO_TRACKS.md`
4. completed phase summaries in chronological order
5. technical appendices for the phase you want to inspect in more detail
6. planning docs in `docs/plans/` when you need forward-looking implementation context

## Documentation naming convention

- `PHASE_*` — phase summaries, validation docs, and bounded phase references
- `EXECUTIVE_DECK_GENERATION_*` — capability-specific docs for deck generation architecture, contracts, UX, quality, and rollout
- `*_CONTRACT_V1` — versioned contract docs intended to be stable references
- `GUIDE_*` — operational guides for generators, datasets, and benchmark execution helpers
- repo-level framing docs keep descriptive names such as `DOCUMENTATION_INDEX`, `PROJECT_POSITIONING_TWO_TRACKS`, and `PUBLICATION_GUIDE`

## Canonical completed-phase summaries

| Phase | Summary document | Focus |
| --- | --- | --- |
| 0 | `docs/PHASE_0_PUBLICATION_AND_POSITIONING.md` | Safe publication baseline |
| 0.5 | `docs/PHASE_0_5_REPOSITORY_GOVERNANCE.md` | Repository governance |
| 1 | `docs/PHASE_1_PRODUCT_FOUNDATION.md` | Product and UX baseline |
| 2 | `docs/PHASE_2_MODULAR_ARCHITECTURE.md` | Modular architecture |
| 3 | `docs/PHASE_3_MULTI_PROVIDER_FOUNDATION.md` | Multi-provider foundation |
| 4 | `docs/PHASE_4_DOCUMENT_RAG_FOUNDATION.md` | Document-grounded RAG |
| 4.5 | `docs/PHASE_4_5_VALIDATION.md` | Benchmarked RAG validation |
| 5 | `docs/PHASE_5_SUMMARY.md` | Structured outputs and evidence-grounded CV extraction |
| 5.5 | `docs/PHASE_5_5_FRAMEWORK_EVOLUTION.md` | LangChain and LangGraph evolution |
| 6 | `docs/PHASE_6_DOCUMENT_OPERATIONS_COPILOT.md` | Document Operations Copilot |
| 7 | `docs/PHASE_7_MODEL_COMPARISON.md` | Model comparison and benchmarking |

## Technical appendices by phase

### Phase 4.5

- `docs/PHASE_4_5_BENCHMARK_RESULTS.md`
- `docs/BENCHMARK_PDF_EXTRACTION_EN.md`
- `docs/assets/phase_4_5/`
- `docs/data/phase_4_5_benchmark_data.json`

### Phase 5

- `docs/PHASE_5_STRUCTURED_OUTPUT_FOUNDATION.md`
- `docs/PHASE_5_STRUCTURED_OUTPUTS_USAGE.md`
- `docs/PHASE_5_EVIDENCE_PACK.md`
- `docs/PHASE_5_EVIDENCE_EVAL_REPORT.md`
- `docs/PHASE_5_OCR_FIRST_VL_ON_DEMAND_PRODUCTION_READINESS.md`
- `docs/PHASE_5_OCR_FALLBACK_UPDATE_FINAL.md`
- `docs/PHASE_5_EVALS_AND_SYNTHETIC_BENCHMARKS.md`
- `docs/EVIDENCE_CV_PIPELINE.md`

### Phase 5.5

- `docs/PHASE_5_5_FRAMEWORK_EVOLUTION.md`

### Phase 6

- `scripts/report_phase6_document_agent_log.py`
- `tests/test_document_agent_unittest.py`
- `tests/test_phase6_document_agent_log.py`

### Phase 7

- `scripts/report_phase7_model_comparison_log.py`

## Planning docs

- `docs/plans/IMPLEMENTATION_PLAN.md`

## Operational guides

- `docs/GUIDE_GENERATE_MULTILAYOUT_RESUMES.md`
- `docs/GUIDE_GENERATE_SYNTHETIC_RESUMES_WITH_PDF.md`
- `docs/GUIDE_RESUME_DATASET_SPLITTER_V2.md`
- `docs/GUIDE_RUN_SYNTHETIC_RESUME_BENCHMARK.md`
- `docs/GUIDE_SYNTHETIC_RESUME_GENERATOR.md`

## Active or bounded later-phase references

The files below remain valuable technical references, but they are not part of the canonical completed-phase summary path yet:

- `docs/PHASE_8_EVAL_FOUNDATION.md`
- `docs/PHASE_8_EVAL_OPERATING_RHYTHM.md`
- `docs/PHASE_8_5_DECISION_GATE.md`
- `docs/PHASE_8_5_CLOSURE.md`
- `docs/PHASE_9_25_RUNTIME_ECONOMICS_AND_EVIDENCEOPS_LOCAL.md`
- `docs/PHASE_9_5_EVIDENCEOPS_MCP_LOCAL_SERVER.md`
- `docs/PHASE_10_ENGINEERING_PROFESSIONAL.md`
- `docs/PHASE_10_25_PRODUCT_SPLIT_GRADIO_AI_LAB.md`
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`

## Legacy aliases

Legacy transition files now live under `old/docs/`.

Reference map:

- `old/docs/PHASE_3_NOTES.md` -> `docs/PHASE_3_MULTI_PROVIDER_FOUNDATION.md`
- `old/docs/PHASE_4_NOTES.md` -> `docs/PHASE_4_DOCUMENT_RAG_FOUNDATION.md`
- `old/docs/README_evidence_cv_pipeline.md` -> `docs/EVIDENCE_CV_PIPELINE.md`
- `old/docs/PHASE_5_5_LANGCHAIN_EVOLUTION.md` -> `docs/PHASE_5_5_FRAMEWORK_EVOLUTION.md`
