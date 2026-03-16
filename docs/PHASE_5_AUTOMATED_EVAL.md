# Phase 5 automated smoke evaluation

This project now includes a lightweight automated evaluation harness for Phase 5 structured outputs.

## Goal
Provide a single command that runs the current structured-output tasks on controlled fixtures and reports whether the outputs look acceptable.

## Scope
This is a **smoke eval**, not a full benchmark.

It checks:
- whether each structured task runs successfully
- whether the validated payload is non-empty enough to be useful
- whether outputs contain obvious prompt placeholders
- whether the task returns the expected task type

It does **not** replace:
- end-to-end UI testing
- RAG integration testing through Streamlit state
- human review for semantic quality on business documents

## Command
Run all smoke evals:

```bash
python scripts/run_phase5_structured_eval.py --task all
```

Run only CV analysis with a PDF:

```bash
python scripts/run_phase5_structured_eval.py --task cv_analysis --cv-pdf /path/to/resume.pdf
```

## Output
The script prints a PASS / WARN / FAIL summary and writes a JSON report under `phase5_eval/reports/`.
