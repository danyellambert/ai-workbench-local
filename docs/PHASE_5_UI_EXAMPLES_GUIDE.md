# Phase 5 — recommended examples for UI screenshots

Use these four types of examples to assemble the evidence for Phase 5:

## 1. Clean text-based example with PASS
Objective: show that `cv_analysis` works well on a text-based PDF.

Recommended example:
- `modern_two_column` with `PASS` status

Look for a file such as:
- `0001_medium_modern_two_column_*.pdf`

What to show in the UI:
- selected document
- **Structured document** tab
- `cv_analysis` task
- `Use selected documents`
- `document_scan`
- output with:
  - name
  - email
  - location
  - skills
  - languages
  - education
  - experience

## 2. More visually dense text-based example with PASS
Objective: show robustness beyond a simple layout.

Recommended example:
- `compact_sidebar` with `PASS` status
or
- `dense_executive` with `PASS` status

Look for a file such as:
- `0007_medium_compact_sidebar_*.pdf`
- `0003_simple_dense_executive_*.pdf`

What to show:
- the same flow as above
- highlight that the layout is more difficult, but the result remains good

## 3. Scan-like example with OCR fallback and improvement
Objective: show that the OCR fallback is working.

Recommended example:
- `scan_like_image_pdf` with `WARN` status

Look for a file such as:
- `0004_medium_scan_like_image_pdf_*.pdf`
or
- `0014_hard_scan_like_image_pdf_*.pdf`

What to show:
- selected scan-like document
- partial structured result
- a note that OCR fallback was triggered
- make it clear that this is an image-based case

## 4. Still-difficult scan-like example
Objective: document a known limitation honestly.

Recommended example:
- `scan_like_image_pdf` with `FAIL` status or a low score

Look for a file such as:
- `0009_simple_scan_like_image_pdf_*.pdf`

What to show:
- that the pipeline attempted to handle the case
- that difficult scans still have limitations
- that this is documented as a known limitation

## Minimum evidence package

I recommend saving:

- 2 screenshots of text-based PASS cases
- 1 screenshot of a scan-like case improved via OCR
- 1 screenshot of a scan-like case that is still difficult
- 2 good JSON files exported by the app
- 1 excerpt from the synthetic benchmark
- 1 excerpt from the Phase 5 smoke eval

## Suggested file names

- `phase5_ui_01_textual_pass.png`
- `phase5_ui_02_visual_pass.png`
- `phase5_ui_03_scanlike_ocr_warn.png`
- `phase5_ui_04_scanlike_limit.png`
- `phase5_structured_output_cv_good.json`
- `phase5_structured_output_summary_good.json`
- `phase5_benchmark_resume_excerpt.csv`
- `phase5_smoke_eval_excerpt.txt`
