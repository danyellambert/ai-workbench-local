# Evidence-Grounded CV Pipeline

## Purpose

This document describes the parallel CV extraction pipeline used to support auditable resume parsing without replacing the legacy document path unconditionally.

## Main goal

The pipeline prioritizes:

- traceability
- reduced hallucination risk
- explicit separation between confirmed evidence and weaker visual candidates

## Basic usage

```bash
python -m src.evidence_cv.cli parse path/to/cv.pdf --out out.json
```

## How it integrates with the main application

The `evidence_cv` path is integrated through the document loading layer without globally replacing the existing PDF flow.

Main integration point:

- `src/rag/loaders.py`

## Activation rules

The pipeline is only eligible when:

- the feature flag is enabled
- the file looks like a CV/resume, or the document is strongly scan-like
- the rollout gate allows the document into the new path

## Rollout model

The pipeline supports controlled rollout percentages and deterministic bucketing by file.

It also includes automated promotion, hold, and rollback helpers based on shadow-rollout evidence.

## Product contract

Even when the new pipeline is used, the rest of the application still receives a compatible payload contract, including:

- consolidated extracted text
- source type classification
- warnings
- evidence summary
- explicit product-consumption policy

## Product-consumption policy

The pipeline exposes explicit field status categories such as:

- `confirmed`
- `visual_candidate`
- `needs_review`
- `not_found`

The product flow is expected to consume `confirmed` values automatically and keep the other categories available for future UI and review workflows.
### Supporting references

- `old/docs/README_evidence_cv_pipeline.md`
- `scripts/auto_rollout_evidence_cv.py`
- `scripts/report_evidence_shadow_rollout.py`
- `tests/test_evidence_reconcile.py`
