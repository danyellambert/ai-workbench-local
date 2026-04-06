# Resume Dataset Splitter v2

This version improves the original script by:

- adding an `ocr_needed` bucket for PDFs with no/very poor text extraction
- preserving the original relative path when copying files, so repeated names do not overwrite each other
- storing the top-level source folder in the CSV
- recalibrating the simple / medium / hard thresholds

Dataset: https://www.kaggle.com/datasets/hadikp/resume-data-pdf

## Install

```bash
pip install pypdf kaggle
```

## Usage

### If you already extracted the dataset

```bash
python resume_dataset_splitter_v2.py \
  --input-dir data/external/resume_data_pdf/unzipped \
  --outdir data/eval/resume_split_v2 \
  --sample-per-bucket 10
```

### If you want to download via Kaggle API

```bash
python resume_dataset_splitter_v2.py \
  --dataset hadikp/resume-data-pdf \
  --download \
  --workdir data/external/resume_data_pdf \
  --outdir data/eval/resume_split_v2 \
  --sample-per-bucket 10
```

## Output

- `resume_features_all.csv`
- `resume_features_sample.csv`
- `summary.json`
- `all_buckets/simple|medium|hard|ocr_needed/`
- `sample_buckets/simple|medium|hard|ocr_needed/`

## Why `ocr_needed` matters

Many resume datasets contain image-based PDFs where standard text extraction returns zero or near-zero characters.
Those files are not the same thing as "hard but text-extractable" PDFs, so this version separates them.
