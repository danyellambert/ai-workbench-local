# Phase 8 — Eval Foundation

## Goal

Create a reusable local evaluation layer that persists quality signals over time instead of relying only on isolated JSON reports.

## What is already in place

- SQLite-backed local eval store in `.phase8_eval_runs.sqlite3`
- shared storage helpers in `src/storage/phase8_eval_store.py`
- automatic persistence for:
  - `structured_smoke_eval`
  - `checklist_regression`
  - `evidence_cv_gold_eval`
- historical backfill from legacy JSON reports
- diagnostic report for persistent failures and adaptation candidates
- explicit decision summary showing when the current prompt+RAG stack seems sufficient and when targeted adaptation may be justified
- runtime snapshot/sidebar integration exposing recent eval readiness signals directly in the app, including:
  - global recommendation for Phase 8.5 readiness
  - top failure reasons
  - healthy tasks where prompt+RAG still seem sufficient
  - adaptation candidates and next eval priorities
- explicit threshold catalog per suite/task in `src/evals/phase8_thresholds.py`
- additional manually reviewed real-document gold sets for:
  - `asap-2025-annual-report-tagged.pdf`
  - `exhibit10-3.pdf`
  - `Sample-Resume-1-07262023.pdf`
  - `Sample-Resume-2-1.pdf`
  - `Sample-Resume-3-.pdf`
- curated public-source registry for selected extra local materials in `data/materials_demo/public_material_sources.json`
- helper script to reproduce/download selected public materials:

```bash
python scripts/download_phase8_public_materials.py --dry-run
```

- live/local eval orchestration script for prepared provider + RAG environments:

```bash
python scripts/run_phase8_live_evals.py --preflight-only
python scripts/run_phase8_live_evals.py --limit-structured-docs 3
```
- separate GitHub Actions workflow for environment-dependent live evals in `.github/workflows/phase8-evals-live.yml`
- operating routine document for continuous use in `docs/PHASE_8_EVAL_OPERATING_RHYTHM.md`
- GitHub Actions workflow for deterministic eval/test coverage in `.github/workflows/phase8-evals.yml`
- aggregated report script:

```bash
python scripts/report_phase8_eval_store.py
```

- historical import/backfill script:

```bash
python scripts/import_phase8_eval_history.py
```

- diagnostic report script:

```bash
python scripts/report_phase8_eval_diagnosis.py
```

## Why SQLite first

The project is still local-first and free-first.

SQLite is currently the best trade-off for:

- zero extra infrastructure
- reproducible local runs
- easy benchmark/eval accumulation
- future migration path to Postgres if/when the Oracle public deploy needs stronger concurrency

## Current suites writing to the store

### 1. Structured smoke eval

```bash
python scripts/run_phase5_structured_eval.py --task all
```

Writes one eval run per task execution.

### 2. Checklist regression

```bash
python scripts/evaluate_checklist_regression.py --document-name "<document-name>"
```

Writes one eval run for the checklist regression execution.

This suite now also exposes groundedness/citation proxies such as:

- checklist coverage
- grounded item rate
- citation precision proxy (`source_text` + `evidence` present)

### 3. Evidence CV gold eval

```bash
python scripts/evaluate_evidence_cv_gold_set.py
```

Default gold set fixture:

- `phase5_eval/fixtures/evidence_cv_mini_gold_set.json`

Writes one eval run per file and per variant:

- `legacy`
- `evidence_no_vl`
- `evidence_with_vl`

### 4. Document-agent routing and LangGraph workflow eval

```bash
python scripts/run_phase8_agent_workflow_eval.py
```

This deterministic suite covers:

- intent-routing accuracy
- tool-selection accuracy
- document-comparison routing cases
- LangGraph guardrail decisions
- transition accuracy
- retry useful vs unnecessary
- latency for routing/guardrail evaluation

### 5. Live eval orchestration for prepared local environments

```bash
python scripts/run_phase8_live_evals.py --preflight-only
python scripts/run_phase8_live_evals.py --limit-structured-docs 3
```

This orchestration layer is intended for local/self-hosted environments where the following are already available:

- local provider runtime (for example Ollama)
- local/accessible embedding runtime
- indexed documents in the RAG store
- local real-document gold fixtures

It can also optionally attempt to index missing manifest documents before execution.

## Historical backfill

If the SQLite store is still empty, you can import the already existing JSON reports:

```bash
python scripts/import_phase8_eval_history.py
```

This imports historical runs from `phase5_eval/reports/` into `.phase8_eval_runs.sqlite3` and avoids duplicates through a deterministic `run_key`.

## Report usage

Global summary:

```bash
python scripts/report_phase8_eval_store.py
```

Filtered by suite:

```bash
python scripts/report_phase8_eval_store.py --suite structured_smoke_eval
python scripts/report_phase8_eval_store.py --suite checklist_regression
python scripts/report_phase8_eval_store.py --suite evidence_cv_gold_eval
```

Filtered by task:

```bash
python scripts/report_phase8_eval_store.py --task checklist
```

Diagnostic report:

```bash
python scripts/report_phase8_eval_diagnosis.py
python scripts/report_phase8_eval_diagnosis.py --suite structured_smoke_eval
```

The diagnosis report now highlights:

- persistent failure tasks
- top repeated failure reasons
- tasks where the current prompt+RAG+schema stack looks sufficient
- tasks that still need iteration before any model adaptation
- tasks that may become candidates for targeted adaptation later

## DeepEval decision

DeepEval was considered at this stage, but intentionally deferred.

Reason:

- the project now has its own local-first eval foundation
- current priority is expanding grounded, reproducible local suites before adding another evaluation framework
- DeepEval remains a possible future integration, but it no longer blocks the technical closure of the Phase 8 local foundation

## What this unlocks next

This foundation prepares the project for the next Phase 8 steps:

- expanding real eval suites by task/use case
- tracking pass/warn/fail trends over time
- connecting eval outcomes to workflow decisions and quality scores
- deciding more objectively when prompt/RAG changes are enough and when model adaptation is justified