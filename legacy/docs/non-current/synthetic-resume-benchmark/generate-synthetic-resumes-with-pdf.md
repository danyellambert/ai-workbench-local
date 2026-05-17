# Synthetic Resume Generator with PDF Support

This version supports:

- JSON output
- Markdown output
- PDF output

## Install

```bash
pip install reportlab
```

## Usage

### JSON + PDF
```bash
python generate_synthetic_resumes_with_pdf.py \
  --bank data/processed/resume_component_bank/components_manual.json \
  --outdir data/synthetic/resumes \
  --count 60 \
  --formats json pdf
```

### JSON + MD + PDF
```bash
python generate_synthetic_resumes_with_pdf.py \
  --bank data/processed/resume_component_bank/components_manual.json \
  --outdir data/synthetic/resumes \
  --count 60 \
  --formats json md pdf
```

## Important note

Use the manual strong component bank if your public PDF dataset has poor extractable text.
