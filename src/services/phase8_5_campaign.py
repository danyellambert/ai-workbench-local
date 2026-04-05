from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..config import BASE_DIR
from .phase8_5_benchmark import (
    append_jsonl_record,
    build_preflight_payload,
    build_run_id,
    collect_relevant_environment_values,
    resolve_repo_path,
    run_phase8_5_benchmark,
    slugify,
    stable_hash,
    write_benchmark_outputs,
)
from .phase8_5_decision_gate import load_phase8_5_benchmark_artifacts
from .runtime_snapshot import build_benchmark_environment_snapshot


DEFAULT_PHASE8_5_STAGE_ORDER = ("generation", "embeddings", "rerankers", "ocr_vlm")


def _resolve_stage_order(manifest: dict[str, object], selected_groups: list[str]) -> list[str]:
    policy = manifest.get("staged_campaign_policy") if isinstance(manifest.get("staged_campaign_policy"), dict) else {}
    configured_order = [
        str(item).strip()
        for item in (policy.get("stage_order") or [])
        if str(item).strip()
    ]
    base_order = configured_order or list(DEFAULT_PHASE8_5_STAGE_ORDER)
    ordered_groups = [group for group in base_order if group in selected_groups]
    ordered_groups.extend(group for group in selected_groups if group not in ordered_groups)
    return ordered_groups


def build_phase8_5_campaign_id(
    manifest: dict[str, object],
    *,
    selected_groups: list[str],
    provider_filter: str | None,
    model_filter: str | None,
    smoke: bool,
) -> str:
    manifest_fingerprint_source = {key: value for key, value in manifest.items() if key != "_manifest_path"}
    identity = {
        "benchmark_id": manifest.get("benchmark_id"),
        "manifest_version": manifest.get("manifest_version"),
        "manifest_fingerprint": stable_hash(manifest_fingerprint_source, length=16),
        "campaign_mode": "staged_full_matrix",
        "selected_groups": list(selected_groups),
        "provider_filter": str(provider_filter or "").strip().lower() or None,
        "model_filter": str(model_filter or "").strip() or None,
        "smoke": bool(smoke),
    }
    benchmark_slug = slugify(str(manifest.get("benchmark_id") or "phase8-5"))
    return f"{benchmark_slug}-campaign-{stable_hash(identity, length=10)}"


def resolve_phase8_5_campaign_dir(
    manifest: dict[str, object],
    *,
    campaign_id: str,
    output_dir_override: str | None,
) -> Path:
    if output_dir_override:
        return resolve_repo_path(output_dir_override)
    policy = manifest.get("staged_campaign_policy") if isinstance(manifest.get("staged_campaign_policy"), dict) else {}
    root_dir = resolve_repo_path(str(policy.get("root_dir") or "benchmark_runs/phase8_5_matrix_campaigns"))
    return root_dir / campaign_id


def build_phase8_5_campaign_plan(
    manifest: dict[str, object],
    *,
    registry: dict[str, dict[str, object]],
    campaign_id: str,
    campaign_dir: Path,
    selected_groups: list[str],
    smoke: bool,
    provider_filter: str | None,
    model_filter: str | None,
    resume: bool,
) -> dict[str, object]:
    ordered_groups = _resolve_stage_order(manifest, selected_groups)

    stages: list[dict[str, object]] = []
    for index, group in enumerate(ordered_groups, start=1):
        stage_run_id = build_run_id(
            manifest,
            selected_groups=[group],
            provider_filter=provider_filter,
            model_filter=model_filter,
            smoke=smoke,
        )
        stage_run_dir = campaign_dir / "group_runs" / f"{index:02d}_{group}_{stage_run_id}"
        stage_preflight = build_preflight_payload(
            manifest,
            registry=registry,
            run_id=stage_run_id,
            output_dir=stage_run_dir,
            selected_groups=[group],
            smoke=smoke,
            provider_filter=provider_filter,
            model_filter=model_filter,
            resume=resume,
        )
        stages.append(
            {
                "stage_index": index,
                "group": group,
                "run_id": stage_run_id,
                "run_dir": str(stage_run_dir),
                "preflight": stage_preflight,
            }
        )

    combined_preflight = build_preflight_payload(
        manifest,
        registry=registry,
        run_id=campaign_id,
        output_dir=campaign_dir,
        selected_groups=ordered_groups,
        smoke=smoke,
        provider_filter=provider_filter,
        model_filter=model_filter,
        resume=resume,
    )
    combined_preflight.update(
        {
            "campaign_mode": "staged_full_matrix",
            "campaign_id": campaign_id,
            "stage_order": ordered_groups,
            "stages": [
                {
                    "stage_index": item.get("stage_index"),
                    "group": item.get("group"),
                    "run_id": item.get("run_id"),
                    "run_dir": item.get("run_dir"),
                    "planned_case_count": ((item.get("preflight") or {}).get("planned_case_count")),
                }
                for item in stages
            ],
        }
    )
    return {
        "campaign_id": campaign_id,
        "campaign_dir": str(campaign_dir),
        "selected_groups": ordered_groups,
        "smoke": bool(smoke),
        "provider_filter": provider_filter,
        "model_filter": model_filter,
        "resume": bool(resume),
        "stages": stages,
        "preflight": combined_preflight,
    }


def _resolved_case_artifacts(events: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "case_id": event.get("case_id"),
            "group": event.get("group"),
            "provider_requested": event.get("provider_requested"),
            "provider_effective": event.get("provider_effective"),
            "model_requested": event.get("model_requested"),
            "model_effective": event.get("model_effective"),
            "requested_runtime_family": event.get("requested_runtime_family"),
            "resolved_runtime_family": event.get("resolved_runtime_family"),
            "runtime_family_resolution_status": event.get("runtime_family_resolution_status"),
            "runtime_family_resolution_note": event.get("runtime_family_resolution_note"),
            "model_resolution_status": event.get("model_resolution_status"),
            "model_resolution_source": event.get("model_resolution_source"),
            "requested_model_candidates": event.get("requested_model_candidates") or [],
            "runtime_artifact": event.get("runtime_artifact"),
            "runtime_bucket": event.get("runtime_bucket"),
            "quantization_family": event.get("quantization_family"),
            "runtime_path": event.get("runtime_path"),
            "backend_equivalence_key": event.get("backend_equivalence_key"),
            "equivalent_direct_runtime_key": event.get("equivalent_direct_runtime_key"),
            "path_overhead_expected": event.get("path_overhead_expected"),
            "status": event.get("status"),
        }
        for event in events
        if isinstance(event, dict)
    ]


def run_phase8_5_staged_campaign(
    manifest: dict[str, object],
    *,
    registry: dict[str, dict[str, object]],
    campaign_id: str,
    campaign_dir: Path,
    selected_groups: list[str],
    smoke: bool,
    provider_filter: str | None,
    model_filter: str | None,
    resume: bool,
) -> dict[str, object]:
    plan = build_phase8_5_campaign_plan(
        manifest,
        registry=registry,
        campaign_id=campaign_id,
        campaign_dir=campaign_dir,
        selected_groups=selected_groups,
        smoke=smoke,
        provider_filter=provider_filter,
        model_filter=model_filter,
        resume=resume,
    )
    campaign_dir.mkdir(parents=True, exist_ok=True)
    (campaign_dir / "campaign_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    stage_results: list[dict[str, object]] = []
    merged_events: list[dict[str, object]] = []

    for stage in plan.get("stages") or []:
        if not isinstance(stage, dict):
            continue
        group = str(stage.get("group") or "").strip()
        stage_run_id = str(stage.get("run_id") or "").strip()
        stage_run_dir = Path(str(stage.get("run_dir") or "")).resolve()
        summary_path = stage_run_dir / "aggregated" / "summary.json"
        stage_raw_events_path = stage_run_dir / "raw" / "events.jsonl"

        if stage_raw_events_path.exists() and not resume and not summary_path.exists():
            raise RuntimeError(
                f"Stage run directory already contains raw benchmark events. Re-run with --resume or choose a different --output-dir: {stage_run_dir}"
            )

        if resume and summary_path.exists():
            result = load_phase8_5_benchmark_artifacts(stage_run_dir)
            aggregated = result.get("summary") if isinstance(result.get("summary"), dict) else {}
            events = [item for item in (result.get("events") or []) if isinstance(item, dict)]
            stage_status = "reused_existing_stage_run"
        else:
            result = run_phase8_5_benchmark(
                manifest=manifest,
                registry=registry,
                run_id=stage_run_id,
                run_dir=stage_run_dir,
                selected_groups=[group],
                smoke=smoke,
                provider_filter=provider_filter,
                model_filter=model_filter,
                resume=resume,
            )
            aggregated = result.get("aggregated") if isinstance(result.get("aggregated"), dict) else {}
            events = [item for item in (result.get("events") or []) if isinstance(item, dict)]
            stage_status = "executed"

        merged_events.extend(events)
        stage_results.append(
            {
                "group": group,
                "run_id": stage_run_id,
                "run_dir": str(stage_run_dir),
                "status": stage_status,
                "total_cases": aggregated.get("total_cases"),
                "successful_cases": aggregated.get("successful_cases"),
                "failed_cases": aggregated.get("failed_cases"),
            }
        )

    combined_preflight = dict(plan.get("preflight") or {})
    combined_preflight["stages"] = stage_results
    combined_preflight["campaign_mode"] = "staged_full_matrix"
    combined_preflight["campaign_id"] = campaign_id

    environment_snapshot = build_benchmark_environment_snapshot(
        project_root=BASE_DIR,
        registry=registry,
        manifest=manifest,
        selected_groups=list(plan.get("selected_groups") or []),
        fairness_config=manifest.get("fairness") if isinstance(manifest.get("fairness"), dict) else {},
        environment_overrides={
            **collect_relevant_environment_values(),
            "timeout_policy": manifest.get("timeout_policy"),
            "resume_policy": manifest.get("resume_policy"),
            "campaign_mode": "staged_full_matrix",
            "campaign_id": campaign_id,
        },
        resolved_case_artifacts=_resolved_case_artifacts(merged_events),
    )
    environment_snapshot["campaign_stages"] = stage_results

    raw_events_path = campaign_dir / "raw" / "events.jsonl"
    summary_path = campaign_dir / "aggregated" / "summary.json"
    if raw_events_path.exists() and not resume and not summary_path.exists():
        raise RuntimeError(
            f"Campaign directory already contains raw benchmark events. Re-run with --resume or choose a different --output-dir: {campaign_dir}"
        )
    if raw_events_path.exists() and not resume:
        raw_events_path.unlink()
    append_jsonl_record(
        raw_events_path,
        {
            "event_type": "campaign_started",
            "run_id": campaign_id,
            "started_at": time.time(),
            "selected_groups": plan.get("selected_groups") or [],
            "smoke": bool(smoke),
        },
    )
    for event in merged_events:
        append_jsonl_record(raw_events_path, event)

    aggregated = write_benchmark_outputs(
        run_dir=campaign_dir,
        manifest=manifest,
        environment_snapshot=environment_snapshot,
        preflight=combined_preflight,
        events=merged_events,
    )
    append_jsonl_record(
        raw_events_path,
        {
            "event_type": "campaign_completed",
            "run_id": campaign_id,
            "finished_at": time.time(),
            "aggregated": {
                "total_cases": aggregated.get("total_cases"),
                "successful_cases": aggregated.get("successful_cases"),
                "failed_cases": aggregated.get("failed_cases"),
            },
            "stages": stage_results,
        },
    )
    (campaign_dir / "campaign_stages.json").write_text(
        json.dumps(stage_results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "campaign_id": campaign_id,
        "campaign_dir": str(campaign_dir),
        "preflight": combined_preflight,
        "environment_snapshot": environment_snapshot,
        "aggregated": aggregated,
        "events": merged_events,
        "stages": stage_results,
    }