# Phase 5 Automated Smoke Eval

## Purpose

This local smoke eval helps answer a simple question: are the structured-output tasks producing output that is not only valid JSON, but also minimally useful and grounded?

It is not a benchmark and it does not replace manual review, but it gives the project a reproducible local check.

## Command

Run all structured tasks covered by the smoke eval:

```bash
PYTHONPATH=. python scripts/run_phase5_structured_eval.py --task all
```

Run a single task:

```bash
PYTHONPATH=. python scripts/run_phase5_structured_eval.py --task extraction
PYTHONPATH=. python scripts/run_phase5_structured_eval.py --task code_analysis
```

Use a real PDF for CV analysis:

```bash
PYTHONPATH=. python scripts/run_phase5_structured_eval.py --task cv_analysis --cv-pdf "/path/to/cv.pdf"
```

## Covered tasks

- `extraction`
- `summary`
- `checklist`
- `cv_analysis`
- `code_analysis`

## Fixtures

Default fixtures live in:

- `phase5_eval/fixtures/01_extraction_input.txt`
- `phase5_eval/fixtures/02_summary_input.txt`
- `phase5_eval/fixtures/03_checklist_input.txt`
- `phase5_eval/fixtures/04_cv_sample.txt`
- `phase5_eval/fixtures/05_code_sample.py`

## PASS / WARN / FAIL semantics

- `PASS`: valid and semantically healthy enough for a smoke test
- `WARN`: valid, but too shallow, too generic, or missing useful secondary structure
- `FAIL`: invalid or clearly unusable for the intended task

## Notes

- `summary`, `checklist`, `cv_analysis`, and `code_analysis` are already expected to be functional in smoke tests.
- `extraction` should also pass now, but it remains the task most sensitive to prompt/model quality.
- This eval is intentionally lightweight and local; it is meant to support iteration during Phase 5, not replace the later benchmark work planned for later phases.
