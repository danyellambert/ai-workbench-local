# Phase 8.5 Benchmark Execution

This document describes how to run the **Phase 8.5 benchmark workflow** for:

- Round 1 core slices:
  - generation/runtime comparisons
  - embedding comparisons
- Round 2 extensions:
  - reranker benchmark slices
  - OCR / VLM fallback benchmark slices

## What this workflow does

- runs a **resumable** benchmark matrix for:
  - generation provider/model/runtime comparisons
  - embedding comparisons
  - reranker comparisons
  - OCR / VLM fallback comparisons
- records a stable **run id** and stable **case ids**
- writes:
  - raw JSONL event logs
  - normalized CSV outputs
  - aggregated JSON summaries
  - markdown report summary
- captures per-run environment/runtime inventory, including resolved provider/model/runtime artifacts actually used

Primary files:

- manifest: `phase8_eval/configs/phase8_5_benchmark_matrix.json`
- orchestrator: `scripts/run_phase8_5_benchmark_matrix.py`

## 1. Preflight only

Use this to validate the resolved matrix, output location, provider/model availability, and resume inventory without executing benchmark cases.

```bash
python scripts/run_phase8_5_benchmark_matrix.py --preflight
```

## 2. Smoke run

Use this for the smallest safe execution path. It uses the smoke limits defined in the manifest.

```bash
python scripts/run_phase8_5_benchmark_matrix.py --smoke
```

If you want to preview the smoke plan without writing outputs or executing anything:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --smoke --dry-run
```

## 3. Full benchmark run

Run the full local Phase 8.5 matrix:

```bash
python scripts/run_phase8_5_benchmark_matrix.py
```

## 4. Resume an interrupted run

Resume uses the stable run id derived from the selected matrix and skips cases already recorded as successful in `raw/events.jsonl`.

```bash
python scripts/run_phase8_5_benchmark_matrix.py --resume
```

## 5. Run a single benchmark group

Generation only:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --group generation
```

Embeddings only:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --group embeddings
```

Rerankers only:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --group rerankers
```

OCR / VLM only:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --group ocr_vlm
```

## 6. Filter to a single provider/model

Single provider:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --group generation --provider ollama
```

Single exact provider/model pair:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --group generation --provider ollama --model qwen2.5:7b
```

## Outputs

By default, runs are written under:

```text
benchmark_runs/phase8_5_round1/<stable-run-id>/
```

Important outputs:

- `raw/events.jsonl`
- `normalized/generation_cases.csv`
- `normalized/embedding_cases.csv`
- `normalized/embedding_questions.csv`
- `normalized/reranker_cases.csv`
- `normalized/reranker_questions.csv`
- `normalized/ocr_vlm_cases.csv`
- `aggregated/summary.json`
- `aggregated/generation_summary.json`
- `aggregated/embedding_summary.json`
- `aggregated/reranker_summary.json`
- `aggregated/ocr_vlm_summary.json`
- `environment_snapshot.json`
- `manifest.resolved.json`
- `report.md`

## Round 2 smoke-safe commands

Preview reranker slice only:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --group rerankers --smoke --dry-run
```

Preview OCR / VLM slice only:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --group ocr_vlm --smoke --dry-run
```

Run preflight for both Round 2 groups:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --group rerankers --group ocr_vlm --preflight
```

## Fairness and comparison notes

- This workflow records prompt profile, response format, temperature, top_p, max output tokens, context window, runtime bucket, quantization family, and resolved runtime artifact details per case where available.
- Seed is recorded as metadata, but not every provider/runtime in this repository currently exposes a universal deterministic seed control.
- Some comparisons are not perfectly apples-to-apples across runtimes. When semantics differ, the workflow preserves the requested configuration and records the resolved runtime/provider/model artifact details instead of silently substituting alternatives.
- The reranker slice is currently a **clean local benchmark path** built on the repo’s existing hybrid retrieval/reranking implementation.
- The OCR / VLM slice is intentionally **partial but real**: it reuses the existing CV/evidence fallback pipeline and focuses on reusable gold-backed CV/contact evidence rather than inventing a broader document evaluation path.