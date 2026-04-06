from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..storage.runtime_paths import get_phase8_eval_db_path
from ..storage.phase8_eval_diagnosis import build_eval_diagnosis
from ..storage.phase8_eval_store import load_eval_runs, summarize_eval_runs
from .phase8_5_decision_gate import find_latest_phase8_5_run_dir, load_phase8_5_benchmark_artifacts


REUSABLE_BENCHMARK_COMPONENTS = [
    {
        "path": "src/services/phase8_5_benchmark.py",
        "role": "round1 benchmark orchestrator, case building, normalization, aggregation, markdown reporting",
    },
    {
        "path": "src/services/phase8_5_benchmark_round2.py",
        "role": "round2 reranker + OCR/VLM slices reusing existing local repo logic",
    },
    {
        "path": "scripts/run_phase8_5_benchmark_matrix.py",
        "role": "CLI entrypoint for resumable benchmark execution by group",
    },
    {
        "path": "phase8_eval/configs/phase8_5_benchmark_matrix.json",
        "role": "manifest for benchmark groups, fairness, output policy and smoke limits",
    },
]

REUSABLE_COMPARISON_COMPONENTS = [
    {
        "path": "src/services/model_comparison.py",
        "role": "provider/model candidate execution and heuristic quality scoring",
    },
    {
        "path": "src/storage/phase7_model_comparison_log.py",
        "role": "leaderboards by provider/model/runtime bucket/quantization family/use case",
    },
    {
        "path": "src/providers/registry.py",
        "role": "provider/runtime capability resolution and model availability filtering",
    },
]

REUSABLE_RUNTIME_COMPONENTS = [
    {
        "path": "src/storage/phase8_eval_store.py",
        "role": "SQLite-backed eval store reused by diagnosis and decision logic",
    },
    {
        "path": "src/storage/phase8_eval_diagnosis.py",
        "role": "task health, persistent failure and adaptation candidate diagnosis",
    },
    {
        "path": "src/services/runtime_snapshot.py",
        "role": "environment/provider inventory snapshots and benchmark runtime metadata",
    },
    {
        "path": "scripts/report_phase7_model_comparison_log.py",
        "role": "model comparison reporting artifact generation",
    },
    {
        "path": "scripts/report_phase8_eval_diagnosis.py",
        "role": "eval diagnosis report generation from the Phase 8 store",
    },
]


def _load_json_file(path: Path) -> dict[str, object] | list[object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, (dict, list)) else None


def _component_rows(project_root: Path, definitions: list[dict[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in definitions:
        relative_path = str(item.get("path") or "")
        if not relative_path:
            continue
        rows.append(
            {
                "path": relative_path,
                "exists": (project_root / relative_path).exists(),
                "role": item.get("role"),
            }
        )
    return rows


def build_phase8_5_audit(
    *,
    project_root: str | Path,
    benchmark_run_dir: str | Path | None = None,
    eval_db_path: str | Path | None = None,
) -> dict[str, object]:
    resolved_root = Path(project_root)
    repo_manifest_path = resolved_root / "phase8_eval" / "configs" / "phase8_5_benchmark_matrix.json"
    repo_manifest = _load_json_file(repo_manifest_path)
    resolved_run_dir = Path(benchmark_run_dir) if benchmark_run_dir else find_latest_phase8_5_run_dir(resolved_root)
    benchmark_artifacts = (
        load_phase8_5_benchmark_artifacts(resolved_run_dir)
        if resolved_run_dir is not None
        else {"summary": {}, "events": [], "manifest": {}, "preflight": {}, "run_dir": None}
    )
    environment_snapshot = (
        _load_json_file(Path(benchmark_artifacts.get("run_dir") or "") / "environment_snapshot.json")
        if benchmark_artifacts.get("run_dir")
        else None
    )
    run_manifest = benchmark_artifacts.get("manifest") if isinstance(benchmark_artifacts.get("manifest"), dict) else {}
    manifest = repo_manifest if isinstance(repo_manifest, dict) else run_manifest
    preflight = benchmark_artifacts.get("preflight") if isinstance(benchmark_artifacts.get("preflight"), dict) else {}
    events = [item for item in (benchmark_artifacts.get("events") or []) if isinstance(item, dict)]
    groups = manifest.get("groups") if isinstance(manifest.get("groups"), dict) else {}
    manifest_groups = sorted(str(key) for key in groups.keys())
    run_manifest_groups = sorted(
        str(key)
        for key in ((run_manifest.get("groups") if isinstance(run_manifest.get("groups"), dict) else {}) or {}).keys()
    )
    executed_groups = sorted({str(item.get("group") or "") for item in events if str(item.get("group") or "").strip()})
    selected_groups = [str(item) for item in (preflight.get("selected_groups") or []) if str(item).strip()]
    effective_groups = sorted(set(selected_groups) | set(executed_groups))

    resolved_eval_db = Path(eval_db_path) if eval_db_path else get_phase8_eval_db_path(resolved_root)
    eval_entries = load_eval_runs(resolved_eval_db)
    eval_summary = summarize_eval_runs(eval_entries)
    eval_diagnosis = build_eval_diagnosis(eval_entries)

    round0_missing: list[str] = []
    if resolved_run_dir is None:
        round0_missing.append("identify or generate at least one Phase 8.5 benchmark run directory")
    if not resolved_eval_db.exists():
        round0_missing.append("populate the Phase 8 eval SQLite store before final closure")

    round1_missing: list[str] = []
    if "generation" not in manifest_groups or "embeddings" not in manifest_groups:
        round1_missing.append("round 1 manifest coverage is incomplete")
    if resolved_run_dir is None or not {"generation", "embeddings"}.issubset(set(effective_groups)):
        round1_missing.append("produce one final evidence bundle containing generation + embeddings together")

    round2_missing: list[str] = []
    if "rerankers" not in manifest_groups or "ocr_vlm" not in manifest_groups:
        round2_missing.append("round 2 manifest coverage is incomplete")
    if not {"rerankers", "ocr_vlm"}.issubset(set(effective_groups)):
        round2_missing.append("produce one final evidence bundle containing rerankers + ocr_vlm together")

    round3_missing: list[str] = []
    if not (resolved_root / "scripts" / "report_phase8_5_decision_gate.py").exists():
        round3_missing.append("decision-gate runner script missing")
    if not eval_entries:
        round3_missing.append("decision gate has no eval evidence to operate on")
    if round2_missing:
        round3_missing.append("re-run the decision gate over a benchmark bundle that already includes round 2 groups")

    round0_ready = not round0_missing
    round1_ready = not round1_missing
    round2_ready = not round2_missing
    round3_ready = not round3_missing
    phase_ready = round0_ready and round1_ready and round2_ready and round3_ready

    return {
        "phase": "8.5",
        "audit_version": "phase8_5_audit.v1",
        "project_root": str(resolved_root),
        "benchmark_run_dir": str(resolved_run_dir) if resolved_run_dir else None,
        "benchmark_run_id": preflight.get("run_id") or (events[0].get("run_id") if events else None),
        "repo_manifest_path": str(repo_manifest_path),
        "manifest_groups": manifest_groups,
        "latest_run_manifest_groups": run_manifest_groups,
        "selected_groups": selected_groups,
        "executed_groups_in_latest_run": executed_groups,
        "effective_groups_in_run_dir": effective_groups,
        "provider_inventory_snapshot_available": isinstance(environment_snapshot, dict) and bool(environment_snapshot.get("provider_inventory")),
        "reusable_components": {
            "benchmark_and_eval": _component_rows(resolved_root, REUSABLE_BENCHMARK_COMPONENTS),
            "provider_model_comparison": _component_rows(resolved_root, REUSABLE_COMPARISON_COMPONENTS),
            "runtime_logging_reporting_store": _component_rows(resolved_root, REUSABLE_RUNTIME_COMPONENTS),
        },
        "eval_store": {
            "db_path": str(resolved_eval_db),
            "db_exists": resolved_eval_db.exists(),
            "total_runs": eval_summary.get("total_runs"),
            "pass_rate": eval_summary.get("pass_rate"),
            "fail_rate": eval_summary.get("fail_rate"),
            "global_recommendation": (eval_diagnosis.get("decision_summary") or {}).get("global_recommendation")
            if isinstance(eval_diagnosis.get("decision_summary"), dict)
            else None,
        },
        "missing_pieces": {
            "round0": round0_missing,
            "round1": round1_missing,
            "round2": round2_missing,
            "round3": round3_missing,
        },
        "support_status": {
            "round0": {"implemented": True, "evidence_bundle_complete": round0_ready},
            "round1": {"implemented": {"generation", "embeddings"}.issubset(set(manifest_groups)), "evidence_bundle_complete": round1_ready},
            "round2": {"implemented": {"rerankers", "ocr_vlm"}.issubset(set(manifest_groups)), "evidence_bundle_complete": round2_ready},
            "round3": {"implemented": (resolved_root / "scripts" / "report_phase8_5_decision_gate.py").exists(), "evidence_bundle_complete": round3_ready},
        },
        "smallest_extension_to_implement_first": {
            "title": "round0_audit_and_closure_bundle",
            "why": "The smallest safe extension is to consolidate one audit/closure layer over the existing benchmark + eval artifacts before expanding or rerunning anything heavier.",
        },
        "phase_closure_readiness": {
            "ready": phase_ready,
            "status": "ready_for_final_closure" if phase_ready else "needs_additional_evidence_bundle_or_reporting_completion",
        },
    }


def render_phase8_5_audit_markdown(audit: dict[str, object]) -> str:
    reusable = audit.get("reusable_components") if isinstance(audit.get("reusable_components"), dict) else {}
    support_status = audit.get("support_status") if isinstance(audit.get("support_status"), dict) else {}
    missing_pieces = audit.get("missing_pieces") if isinstance(audit.get("missing_pieces"), dict) else {}
    lines = [
        "# Phase 8.5 Audit",
        "",
        f"- Benchmark run dir: `{audit.get('benchmark_run_dir') or 'n/a'}`",
        f"- Benchmark run id: `{audit.get('benchmark_run_id') or 'n/a'}`",
        f"- Repo manifest groups: {', '.join(audit.get('manifest_groups') or []) or 'n/a'}",
        f"- Latest run manifest groups: {', '.join(audit.get('latest_run_manifest_groups') or []) or 'n/a'}",
        f"- Effective groups covered in run dir: {', '.join(audit.get('effective_groups_in_run_dir') or []) or 'n/a'}",
        f"- Executed groups in latest run: {', '.join(audit.get('executed_groups_in_latest_run') or []) or 'n/a'}",
        f"- Eval DB exists: `{((audit.get('eval_store') or {}).get('db_exists'))}`",
        f"- Phase closure readiness: `{((audit.get('phase_closure_readiness') or {}).get('status')) or 'n/a'}`",
        "",
    ]

    for section_title, key in [
        ("Reusable benchmark and eval components", "benchmark_and_eval"),
        ("Reusable provider/model comparison logic", "provider_model_comparison"),
        ("Reusable runtime logging/reporting/store logic", "runtime_logging_reporting_store"),
    ]:
        lines.extend([f"## {section_title}", ""])
        for item in reusable.get(key) or []:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- `{item.get('path')}` → {item.get('role')} ({'present' if item.get('exists') else 'missing'})"
            )
        lines.append("")

    lines.extend(["## Missing pieces by round", ""])
    for round_name in ["round0", "round1", "round2", "round3"]:
        readiness = (support_status.get(round_name) or {}).get("evidence_bundle_complete") if isinstance(support_status.get(round_name), dict) else False
        lines.append(f"- `{round_name}` → {'ready' if readiness else 'still missing pieces'}")
        for item in missing_pieces.get(round_name) or []:
            lines.append(f"  - {item}")
    lines.extend(
        [
            "",
            "## Smallest extension to implement first",
            "",
            f"- `{((audit.get('smallest_extension_to_implement_first') or {}).get('title')) or 'n/a'}`",
            f"- {((audit.get('smallest_extension_to_implement_first') or {}).get('why')) or 'n/a'}",
            "",
        ]
    )
    return "\n".join(lines)