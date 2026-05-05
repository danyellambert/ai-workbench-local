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
| 0 | `legacy/docs/phases/publication-and-positioning.md` | Safe publication baseline |
| 0.5 | `legacy/docs/phases/repository-governance.md` | Repository governance |
| 1 | `legacy/docs/phases/product-foundation.md` | Product and UX baseline |
| 2 | `legacy/docs/phases/modular-architecture.md` | Modular architecture |
| 3 | `legacy/docs/phases/multi-provider-foundation.md` | Multi-provider foundation |
| 4 | `legacy/docs/phases/document-grounded-rag-foundation.md` | Document-grounded RAG |
| 4.5 | `legacy/docs/phases/phase-4-5-validation.md` | Benchmarked RAG validation |
| 5 | `legacy/docs/phases/structured-outputs-and-evidence-grounded-cv-extraction.md` | Structured outputs and evidence-grounded CV extraction |
| 5.5 | `legacy/docs/phases/framework-evolution-with-langchain-and-langgraph.md` | LangChain and LangGraph evolution |
| 6 | `legacy/docs/phases/document-operations-copilot.md` | Document Operations Copilot |
| 7 | `legacy/docs/phases/phase-7-model-comparison.md` | Model comparison and benchmarking |

## Technical appendices by phase

### Phase 4.5

- `legacy/docs/phases/phase-4-5-benchmark-results.md`
- `docs/BENCHMARK_PDF_EXTRACTION_EN.md`
- `docs/assets/phase_4_5/`
- `docs/data/phase_4_5_benchmark_data.json`

### Phase 5

- `legacy/docs/phases/phase-5-structured-output-foundation.md`
- `legacy/docs/phases/phase-5-structured-outputs-usage-guide.md`
- `legacy/docs/phases/phase-5-evidence-pack.md`
- `legacy/docs/phases/phase-5-evidence-cv-evaluation-report.md`
- `legacy/docs/phases/ocr-first-vl-on-demand-production-readiness-for-cv-parsing.md`
- `legacy/docs/phases/ocr-fallback-and-synthetic-cv-benchmark.md`
- `legacy/docs/phases/evaluations-and-synthetic-cv-benchmark.md`
- `docs/EVIDENCE_CV_PIPELINE.md`

### Phase 5.5

- `legacy/docs/phases/framework-evolution-with-langchain-and-langgraph.md`

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

- `legacy/docs/phases/eval-foundation.md`
- `docs/architecture/evals/operating-rhythm.md`
- `docs/architecture/evals/decision-gate.md`
- `docs/architecture/evals/closure.md`
- `legacy/docs/phases/runtime-economics-and-evidenceops-foundation.md`
- `legacy/docs/phases/local-evidenceops-mcp-server.md`
- `legacy/docs/phases/engineering-hardening.md`
- `legacy/docs/phases/product-split-gradio-ai-lab.md`
- `docs/architecture/executive-deck-generation/product-capability.md`

## Legacy aliases

Legacy transition files now live under `old/docs/`.

Reference map:

- `old/docs/PHASE_3_NOTES.md` -> `legacy/docs/phases/multi-provider-foundation.md`
- `old/docs/PHASE_4_NOTES.md` -> `legacy/docs/phases/document-grounded-rag-foundation.md`
- `old/docs/README_evidence_cv_pipeline.md` -> `docs/EVIDENCE_CV_PIPELINE.md`
- `old/docs/PHASE_5_5_LANGCHAIN_EVOLUTION.md` -> `legacy/docs/phases/framework-evolution-with-langchain-and-langgraph.md`
