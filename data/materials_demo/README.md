# Materials demo for evals and manual review

This directory concentrates local materials that can feed real-document evals and future Phase 8 / 8.5 experiments.

## Current recommended materials by task

- `checklist/`
  - WHO surgical checklist PDFs used for checklist regression and document-grounded checklist evaluation.
- `code_analysis/`
  - grounded code samples used for `code_analysis` gold-set evaluation.
- `cv_analysis/`
  - realistic resumes/CVs used for `cv_analysis` and `evidence_cv_gold_eval`.
- `extraction/`
  - legal/contracts style PDFs used for structured extraction evals.
- `summary/`
  - long reports used for executive-summary evals.

## Manually reviewed real-document gold sets currently mapped from these materials

- `CV - Lucas - gen.pdf`
- `Sample-Resume-1-07262023.pdf`
- `Sample-Resume-2-1.pdf`
- `Sample-Resume-3-.pdf`
- `demo_code_analysis.py`
- `exhib101.pdf`
- `exhibit10-3.pdf`
- `fy25-afr-final-tagged.pdf`
- `asap-2025-annual-report-tagged.pdf`

## Public-source reproducibility for selected extra materials

Some additional local materials can now be reproduced from a curated public-source map:

- source map: `data/materials_demo/public_material_sources.json`
- download helper: `scripts/download_phase8_public_materials.py`

Dry run:

```bash
python scripts/download_phase8_public_materials.py --dry-run
```

Download only the additional Harvard Law School sample resumes:

```bash
python scripts/download_phase8_public_materials.py --material-id hls_sample_resume_2_1 --material-id hls_sample_resume_3
```

## How to use these materials

1. Index the target documents in the app.
2. Run the appropriate eval scripts using the indexed document name/id.
3. Review the JSON report plus the Phase 8 SQLite diagnosis.
4. Only move to Phase 8.5 experiments when failures remain persistent after prompt/RAG/schema iteration.

## Notes

- These materials are local-first and intentionally versioned for reproducible manual review.
- Additional external downloads can still be added later, but the project already has enough local material to strengthen the current eval foundation.