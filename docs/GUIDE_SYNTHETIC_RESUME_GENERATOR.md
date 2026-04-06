# Synthetic Resume Generator from Public Resume PDFs

This bundle contains two scripts:

1. `build_resume_component_bank.py`
   - reads public resume PDFs
   - extracts reusable components (skills, roles, degree lines, experience/project phrases, locations, languages)
   - saves them into a component bank JSON

2. `generate_synthetic_resumes_from_public_bank.py`
   - loads the component bank
   - generates synthetic but realistic resumes
   - writes `.json` and `.md` outputs

## Recommended folder layout

```text
your_project/
├── data/
│   ├── external/
│   │   └── resume_data_pdf/
│   │       └── unzipped/
│   │           └── ... public PDFs ...
│   ├── processed/
│   │   └── resume_component_bank/
│   │       └── components.json
│   └── synthetic/
│       └── resumes/
│           ├── json/
│           └── md/
└── scripts/
```

## Install

```bash
pip install pypdf
```

## Step 1 — Build the component bank

```bash
python build_resume_component_bank.py \
  --input-dir data/external/resume_data_pdf/unzipped \
  --output data/processed/resume_component_bank/components.json
```

## Step 2 — Generate synthetic resumes

```bash
python generate_synthetic_resumes_from_public_bank.py \
  --bank data/processed/resume_component_bank/components.json \
  --outdir data/synthetic/resumes \
  --count 60
```

## Output

- `data/synthetic/resumes/json/*.json`
- `data/synthetic/resumes/md/*.md`

These are synthetic resumes that reuse public structural patterns and vocabulary, without copying a real person's full identity.
