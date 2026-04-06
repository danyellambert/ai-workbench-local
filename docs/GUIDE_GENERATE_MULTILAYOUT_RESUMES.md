# Multi-layout Synthetic Resume Generator

This generator creates synthetic but realistic resumes in multiple layouts:

- `classic_one_column`
- `modern_two_column`
- `compact_sidebar`
- `dense_executive`
- `scan_like_image_pdf`

It can output:

- JSON
- Markdown
- PDF

## Requirements

```bash
pip install reportlab pillow
```

## Recommended bank

Use the strong manual bank:
- `components_manual_strong.json`

## Usage

### Auto-mix layouts
```bash
python generate_multilayout_resumes.py \
  --bank data/processed/resume_component_bank/components_manual.json \
  --outdir data/synthetic/resumes_multilayout \
  --count 60 \
  --formats json pdf \
  --layout auto
```

### Force two-column only
```bash
python generate_multilayout_resumes.py \
  --bank data/processed/resume_component_bank/components_manual.json \
  --outdir data/synthetic/resumes_two_column \
  --count 30 \
  --formats json pdf \
  --layout modern_two_column
```

### Generate scan-like PDFs
```bash
python generate_multilayout_resumes.py \
  --bank data/processed/resume_component_bank/components_manual.json \
  --outdir data/synthetic/resumes_scan_like \
  --count 30 \
  --formats json pdf \
  --layout scan_like_image_pdf
```

## Why this helps

This gives you a stronger test set for `cv_analysis` because it no longer only produces clean one-column resumes.
It also introduces visually richer and OCR-like cases.
