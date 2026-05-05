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

## Expanded target matrix and substitution policy

The manifest now records both:

- the **requested benchmark target**
- the **resolved local artifact actually used**

This is important because the expanded Phase 8.5 target matrix is broader than the smallest clean set of locally executable artifacts that are always guaranteed to exist in the repo environment.

Current policy:

- `mapping_status=exact`
  - the requested model exists locally and was used directly
- `mapping_status=closest_available`
  - the requested model was not available, and the benchmark used the closest explicitly configured local candidate
- `mapping_status=skipped`
  - no acceptable local candidate was available for that provider/runtime path

Examples now covered in the manifest:

- generation targets
  - `qwen3.5:4b`
  - `phi4-mini:3.8b`
  - `qwen2.5-coder:7b`
  - local HF equivalents / closest available variants when configured
- embedding targets
  - `embeddinggemma:300m`
  - `qwen3-embedding:0.6b`
  - strongest locally configured HF/MLX-style challengers via explicit candidate lists
  - smoke runs now cover both a **general retrieval subset** and a **code retrieval subset** when compatible candidates are configured

- reranker targets
  - vector-only and hybrid lexical baselines remain the default clean comparison path
  - local **neural reranker challengers** can now be included when a local `sentence-transformers` `CrossEncoder` runtime and artifacts are available
  - if that runtime/artifact path is unavailable, those candidates are recorded as skipped rather than silently substituted

- OCR / VLM targets
  - the benchmark now runs a configurable **variant matrix** covering:
    - `pdf_hybrid`
    - `pdf_complete`
    - `legacy_pdf`
    - `evidence_no_vl`
    - `evidence_no_vl_docling_disabled`
    - `evidence_with_vl`
  - each variant records its requested/resolved runtime family and operational timing support metadata

Important limitation:

- the repo now **logs substitutions honestly**, but it still only benchmarks slices that have a clean executable path in the current codebase.
- neural reranker families and broader OCR/VLM runtime families remain bounded by what is already cleanly implemented in the repository.

Primary files:

- manifest: `phase8_eval/configs/phase8_5_benchmark_matrix.json`
- orchestrator: `scripts/run_phase8_5_benchmark_matrix.py`

## Round 0 audit / preflight artifact

Before relying on any specific run as the final evidence bundle, generate the repository audit for Phase 8.5:

```bash
python scripts/report_phase8_5_audit.py
```

This produces a concise view of:

- reusable components already present
- latest benchmark run coverage
- eval-store readiness
- missing pieces by round (`round0` / `round1` / `round2` / `round3`)

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

If you want the expanded evidence bundle to run in **stable staged group order** and then merge the artifacts into one campaign directory:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --staged-campaign
```

## 4. Resume an interrupted run

Resume uses the stable run id derived from the selected matrix and skips cases already recorded as successful in `raw/events.jsonl`.

```bash
python scripts/run_phase8_5_benchmark_matrix.py --resume
```

Resume a staged campaign:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --staged-campaign --resume
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
benchmark_runs/phase8_5_matrix/<stable-run-id>/
```

This root now covers the full manifest matrix, including the original Round 1 slices and the Round 2 reranker / OCR-VLM extensions.

When you use `--staged-campaign`, the merged campaign bundle is written under:

```text
benchmark_runs/phase8_5_matrix_campaigns/<campaign-id>/
```

and each stage also gets its own per-group run directory under:

```text
benchmark_runs/phase8_5_matrix_campaigns/<campaign-id>/group_runs/
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

## Staged campaign commands

Preview the merged staged campaign plan:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --staged-campaign --preflight
```

Run the smallest safe grouped evidence bundle across all groups:

```bash
python scripts/run_phase8_5_benchmark_matrix.py --staged-campaign --smoke --resume
```

The current repo already has a corrected staged smoke campaign evidence bundle under:

- `benchmark_runs/phase8_5_matrix_campaigns/phase8-5-matrix-campaign-3095054546/`

The repo also now has a larger non-smoke staged campaign evidence bundle under:

- `benchmark_runs/phase8_5_matrix_campaigns/phase8-5-matrix-campaign-703f15ab4b/`

## Round 3 decision-gate command

After at least one benchmark run and after the Phase 8 eval store has data, generate the conservative Phase 8.5 decision summary:

```bash
python scripts/report_phase8_5_decision_gate.py --benchmark-run-dir benchmark_runs/phase8_5_matrix/<run-id>
```

If you omit `--benchmark-run-dir`, the script tries to use the latest detected run under:

- `benchmark_runs/phase8_5_matrix/`
- fallback: `benchmark_runs/phase8_5_round1/`

To also write explicit artifacts:

```bash
python scripts/report_phase8_5_decision_gate.py \
  --benchmark-run-dir benchmark_runs/phase8_5_matrix/<run-id> \
  --out-json phase5_eval/reports/phase8_5_decision_summary.json \
  --out-md phase5_eval/reports/phase8_5_decision_report.md
```

This Round 3 layer is intentionally conservative:

- it does **not** start training jobs
- it does **not** add full fine-tuning
- it only turns benchmark + eval evidence into a decision framework for runtime/model, embeddings, rerankers, and adaptation justification

## Final Phase 8.5 closure bundle

To generate the final closure artifact for the whole phase:

```bash
python scripts/report_phase8_5_closure.py
```

This closure bundle combines:

- Round 0 audit
- benchmark evidence from the latest selected run
- Round 3 decision gate
- explicit `fully supported` vs `partially supported` closure notes

## Fairness and comparison notes

- This workflow records prompt profile, response format, temperature, top_p, max output tokens, context window, runtime bucket, quantization family, and resolved runtime artifact details per case where available.
- For Ollama generation benchmarks, the manifest requests `think=false` so reasoning-capable models emit final answers instead of spending the token budget on hidden reasoning traces.
- Requested-vs-resolved model mappings are written to raw events, environment snapshots, aggregated summaries, and the markdown report.
- Seed is recorded as metadata, but not every provider/runtime in this repository currently exposes a universal deterministic seed control.
- Some comparisons are not perfectly apples-to-apples across runtimes. When semantics differ, the workflow preserves the requested configuration and records the resolved runtime/provider/model artifact details instead of silently substituting alternatives.
- The reranker slice is currently a **clean local benchmark path** built on the repo’s existing hybrid retrieval/reranking implementation.
- When configured local neural reranker artifacts are available, the reranker slice can also compare cross-encoder challengers on top of the existing retrieval pool; otherwise those candidates are explicitly skipped and preserved in the run evidence.
- The benchmark report now emits an explicit note when the **code retrieval subset** ends up reusing a general embedding winner as the best available local code fallback.
- The OCR / VLM slice is intentionally **partial but real**: it reuses the existing CV/evidence fallback pipeline and focuses on reusable gold-backed CV/contact evidence rather than inventing a broader document evaluation path.
- The current `huggingface_server` catalog should only expose aliases that are working end-to-end on that provider path. If a model such as DeepSeek R1 is failing via `huggingface_server`, keep it out of the catalog/benchmark matrix until that runtime path is fixed.
- In the current environment, the `embeddinggemma` alias exposed via the local hub was reproduced as a **memory-preflight support boundary** for the backend HF-local embedding path, and is documented honestly instead of being treated as a silent benchmark failure.
- Staged campaigns are now first-class evidence bundles: audit, decision-gate, and closure discovery all recognize merged campaign directories under `benchmark_runs/phase8_5_matrix_campaigns/`.
- Cold start / warm start / TTFT / full peak-memory benchmarking for every runtime family is still only **partially supported**. This workflow now records measured vs estimated vs not-supported operational metrics honestly instead of pretending universal parity.