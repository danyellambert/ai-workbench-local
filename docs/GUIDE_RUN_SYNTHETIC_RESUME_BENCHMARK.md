# Synthetic Resume Benchmark

This script benchmarks your project's `cv_analysis` task using generated resume PDF/JSON pairs.

## What it does

- reads PDFs from `--pdf-dir`
- reads matching JSON ground-truth files from `--json-dir`
- calls the project's `structured_service.run(...)` with `task_name="cv_analysis"`
- compares output against the generated ground truth
- writes:
  - CSV results
  - JSON results
  - summary JSON

## Requirements

This script assumes it is placed inside your project `scripts/` folder and that the project already runs.

## Typical usage

```bash
PYTHONPATH=. python scripts/run_synthetic_resume_benchmark.py \
  --pdf-dir data/synthetic/resumes_multilayout/pdf \
  --json-dir data/synthetic/resumes_multilayout/json \
  --outdir phase5_eval/resume_benchmark
```

## Quick test on 10 files

```bash
PYTHONPATH=. python scripts/run_synthetic_resume_benchmark.py \
  --pdf-dir data/synthetic/resumes_multilayout/pdf \
  --json-dir data/synthetic/resumes_multilayout/json \
  --outdir phase5_eval/resume_benchmark_quick \
  --limit 10
```

## Output

- `resume_benchmark_results.csv`
- `resume_benchmark_results.json`
- `resume_benchmark_summary.json`

## Notes

- `scan_like_image_pdf` files are expected to be harder.
- If your PDF parser extracts zero text from those files, that is useful signal.
- This benchmark is for relative comparison and regression tracking, not perfect absolute truth.
