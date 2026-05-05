# Phase 8.5 Audit

- Benchmark run dir: `baseline://workspace/benchmark_runs/phase8_5_matrix_campaigns/phase8-5-matrix-campaign-703f15ab4b`
- Benchmark run id: `phase8-5-matrix-campaign-703f15ab4b`
- Repo manifest groups: embeddings, generation, ocr_vlm, rerankers
- Latest run manifest groups: embeddings, generation, ocr_vlm, rerankers
- Effective groups covered in run dir: embeddings, generation, ocr_vlm, rerankers
- Executed groups in latest run: embeddings, generation, ocr_vlm, rerankers
- Eval DB exists: `True`
- Phase closure readiness: `ready_for_final_closure`

## Reusable benchmark and eval components

- `src/services/phase8_5_benchmark.py` → round1 benchmark orchestrator, case building, normalization, aggregation, markdown reporting (present)
- `src/services/phase8_5_benchmark_round2.py` → round2 reranker + OCR/VLM slices reusing existing local repo logic (present)
- `scripts/run_phase8_5_benchmark_matrix.py` → CLI entrypoint for resumable benchmark execution by group (present)
- `phase8_eval/configs/phase8_5_benchmark_matrix.json` → manifest for benchmark groups, fairness, output policy and smoke limits (present)

## Reusable provider/model comparison logic

- `src/services/model_comparison.py` → provider/model candidate execution and heuristic quality scoring (present)
- `src/storage/phase7_model_comparison_log.py` → leaderboards by provider/model/runtime bucket/quantization family/use case (present)
- `src/providers/registry.py` → provider/runtime capability resolution and model availability filtering (present)

## Reusable runtime logging/reporting/store logic

- `src/storage/phase8_eval_store.py` → SQLite-backed eval store reused by diagnosis and decision logic (present)
- `src/storage/phase8_eval_diagnosis.py` → task health, persistent failure and adaptation candidate diagnosis (present)
- `src/services/runtime_snapshot.py` → environment/provider inventory snapshots and benchmark runtime metadata (present)
- `scripts/report_phase7_model_comparison_log.py` → model comparison reporting artifact generation (present)
- `scripts/report_phase8_eval_diagnosis.py` → eval diagnosis report generation from the Phase 8 store (present)

## Missing pieces by round

- `round0` → ready
- `round1` → ready
- `round2` → ready
- `round3` → ready

## Smallest extension to implement first

- `round0_audit_and_closure_bundle`
- The smallest safe extension is to consolidate one audit/closure layer over the existing benchmark + eval artifacts before expanding or rerunning anything heavier.

