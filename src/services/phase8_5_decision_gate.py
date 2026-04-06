from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..evals.phase8_thresholds import DIAGNOSIS_THRESHOLDS, PHASE8_5_DECISION_THRESHOLDS


DEFAULT_PHASE8_5_RUN_ROOT_CANDIDATES = (
    "benchmark_runs/phase8_5_matrix",
    "benchmark_runs/phase8_5_matrix_campaigns",
    "benchmark_runs/phase8_5_round1",
)

BENCHMARK_USE_CASE_TO_TASK_TYPE = {
    "executive_summary": "summary",
    "risk_review": "checklist",
    "structured_extraction": "extraction",
    "technical_review": "code_analysis",
    "cv_analysis": "cv_analysis",
}

RETRIEVAL_SENSITIVE_TASKS = {
    "summary",
    "checklist",
    "extraction",
    "cv_analysis",
    "cv_contacts",
    "code_analysis",
    "reranking",
}

TASK_PRIMARY_METRICS = {
    "summary": "pass_rate",
    "checklist": "grounded_item_rate",
    "extraction": "schema_adherence",
    "cv_analysis": "avg_f1",
    "cv_contacts": "avg_f1",
    "classification": "pass_rate",
    "intent_classification": "pass_rate",
    "reranking": "mrr",
    "code_analysis": "avg_score_ratio",
}


def _safe_float(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _average(values: list[float]) -> float:
    return round(sum(values) / max(len(values), 1), 4) if values else 0.0


def _candidate_key(payload: dict[str, object]) -> str:
    explicit_candidate = str(payload.get("candidate_id") or payload.get("candidate") or "").strip()
    if explicit_candidate:
        return explicit_candidate
    provider = str(payload.get("provider") or payload.get("provider_requested") or "").strip()
    model = str(payload.get("model") or payload.get("model_requested") or "").strip()
    return f"{provider}::{model}" if provider or model else "candidate"


def _is_local_candidate(payload: dict[str, object]) -> bool:
    runtime_bucket = str(payload.get("runtime_bucket") or "").strip().lower()
    runtime_path = str(payload.get("runtime_path") or "").strip().lower()
    provider = str(payload.get("provider") or payload.get("provider_requested") or "").strip().lower()
    if runtime_bucket and runtime_bucket != "cloud":
        return True
    if runtime_path and runtime_path in {"direct_runtime", "hub_wrapped_runtime", "local_native_runtime"}:
        return True
    return provider not in {"openai", "huggingface_inference"}


def _load_json_file(path: Path) -> dict[str, object] | list[object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, (dict, list)) else None


def _extract_run_group_coverage(run_dir: Path) -> tuple[int, int, int]:
    preflight = _load_json_file(run_dir / "preflight.json")
    events = _load_json_file(run_dir / "aggregated" / "latest_case_results.json")
    manifest = _load_json_file(run_dir / "manifest.resolved.json")

    executed_groups = {
        str(item.get("group") or "").strip()
        for item in (events or [])
        if isinstance(item, dict) and str(item.get("group") or "").strip()
    }
    selected_groups = {
        str(item).strip()
        for item in ((preflight or {}).get("selected_groups") or [])
        if str(item).strip()
    } if isinstance(preflight, dict) else set()
    manifest_groups = {
        str(key).strip()
        for key in (((manifest or {}).get("groups") or {}) if isinstance(manifest, dict) else {}).keys()
        if str(key).strip()
    }
    return len(executed_groups), len(selected_groups), len(manifest_groups)


def find_latest_phase8_5_run_dir(project_root: str | Path) -> Path | None:
    resolved_root = Path(project_root)
    candidates: list[Path] = []
    for relative_root in DEFAULT_PHASE8_5_RUN_ROOT_CANDIDATES:
        run_root = resolved_root / relative_root
        if not run_root.exists() or not run_root.is_dir():
            continue
        for child in run_root.iterdir():
            if child.is_dir() and (child / "aggregated" / "summary.json").exists():
                candidates.append(child)
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            *_extract_run_group_coverage(item),
            item.stat().st_mtime,
        ),
        reverse=True,
    )
    return candidates[0]


def load_phase8_5_benchmark_artifacts(run_dir: str | Path) -> dict[str, object]:
    resolved_run_dir = Path(run_dir)
    summary = _load_json_file(resolved_run_dir / "aggregated" / "summary.json")
    events = _load_json_file(resolved_run_dir / "aggregated" / "latest_case_results.json")
    manifest = _load_json_file(resolved_run_dir / "manifest.resolved.json")
    preflight = _load_json_file(resolved_run_dir / "preflight.json")
    return {
        "run_dir": str(resolved_run_dir),
        "summary": summary if isinstance(summary, dict) else {},
        "events": events if isinstance(events, list) else [],
        "manifest": manifest if isinstance(manifest, dict) else {},
        "preflight": preflight if isinstance(preflight, dict) else {},
    }


def _build_generation_role_map(manifest: dict[str, object]) -> dict[str, str]:
    groups = manifest.get("groups") if isinstance(manifest.get("groups"), dict) else {}
    generation = groups.get("generation") if isinstance(groups.get("generation"), dict) else {}
    provider_model_pairs = generation.get("provider_model_pairs") if isinstance(generation.get("provider_model_pairs"), list) else []
    role_map: dict[str, str] = {}
    for item in provider_model_pairs:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider") or "").strip().lower()
        model = str(item.get("model") or "").strip()
        role = str(item.get("role") or "").strip() or "challenger"
        if provider and model:
            role_map[f"{provider}::{model}"] = role
    return role_map


def _map_benchmark_use_case_to_task_type(benchmark_use_case: str, use_case_id: str) -> str | None:
    normalized_use_case = str(benchmark_use_case or "").strip().lower()
    normalized_id = str(use_case_id or "").strip().lower()
    if normalized_use_case in BENCHMARK_USE_CASE_TO_TASK_TYPE:
        return BENCHMARK_USE_CASE_TO_TASK_TYPE[normalized_use_case]
    if "summary" in normalized_id:
        return "summary"
    if "checklist" in normalized_id or "risk" in normalized_id:
        return "checklist"
    if "extract" in normalized_id:
        return "extraction"
    if "cv" in normalized_id:
        return "cv_analysis"
    if "code" in normalized_id or "technical" in normalized_id:
        return "code_analysis"
    return None


def _pick_baseline_candidate(ranking: list[dict[str, object]]) -> dict[str, object] | None:
    if not ranking:
        return None
    for item in ranking:
        role = str(item.get("candidate_role") or "").strip().lower()
        if role.startswith("baseline") or role in {"current_default", "default"}:
            return item
    return None


def _compute_latency_ratio(winner: dict[str, object], baseline: dict[str, object], *, latency_key: str) -> float | None:
    winner_latency = _safe_float(winner.get(latency_key))
    baseline_latency = _safe_float(baseline.get(latency_key))
    if winner_latency is None or baseline_latency is None or baseline_latency <= 0:
        return None
    return round(winner_latency / baseline_latency, 4)


def _decide_change(
    *,
    winner: dict[str, object] | None,
    baseline: dict[str, object] | None,
    primary_metric_key: str,
    min_primary_delta: float,
    latency_key: str,
    max_latency_regression_ratio: float,
    secondary_metric_key: str | None = None,
    min_secondary_delta: float | None = None,
    latency_improvement_ratio: float | None = None,
) -> dict[str, object]:
    if not isinstance(winner, dict):
        return {
            "change_recommended": False,
            "status": "insufficient_evidence",
            "reason": "no_winner_available",
        }
    if not isinstance(baseline, dict):
        return {
            "change_recommended": False,
            "status": "insufficient_evidence",
            "reason": "baseline_candidate_not_identified",
            "winner_candidate": _candidate_key(winner),
        }
    if _candidate_key(winner) == _candidate_key(baseline):
        return {
            "change_recommended": False,
            "status": "current_baseline_sufficient",
            "reason": "baseline_remains_best",
            "winner_candidate": _candidate_key(winner),
            "baseline_candidate": _candidate_key(baseline),
        }

    primary_winner = _safe_float(winner.get(primary_metric_key))
    primary_baseline = _safe_float(baseline.get(primary_metric_key))
    primary_delta = (
        round(primary_winner - primary_baseline, 4)
        if primary_winner is not None and primary_baseline is not None
        else None
    )

    secondary_delta = None
    if secondary_metric_key:
        secondary_winner = _safe_float(winner.get(secondary_metric_key))
        secondary_baseline = _safe_float(baseline.get(secondary_metric_key))
        if secondary_winner is not None and secondary_baseline is not None:
            secondary_delta = round(secondary_winner - secondary_baseline, 4)

    latency_ratio = _compute_latency_ratio(winner, baseline, latency_key=latency_key)
    primary_improvement = primary_delta is not None and primary_delta >= float(min_primary_delta)
    secondary_improvement = (
        secondary_metric_key is not None
        and min_secondary_delta is not None
        and secondary_delta is not None
        and secondary_delta >= float(min_secondary_delta)
    )
    latency_acceptable = latency_ratio is None or latency_ratio <= float(max_latency_regression_ratio)
    latency_improved = (
        latency_ratio is not None
        and latency_improvement_ratio is not None
        and latency_ratio <= (1.0 - float(latency_improvement_ratio))
    )

    if (primary_improvement or secondary_improvement) and latency_acceptable:
        status = "change_recommended"
        reason = "quality_gain_clear_enough"
        change_recommended = True
    elif latency_improved and primary_delta is not None and primary_delta >= 0:
        status = "change_recommended"
        reason = "quality_held_with_latency_gain"
        change_recommended = True
    else:
        status = "current_baseline_sufficient"
        reason = "challenger_gain_not_clear_enough"
        change_recommended = False

    return {
        "change_recommended": change_recommended,
        "status": status,
        "reason": reason,
        "winner_candidate": _candidate_key(winner),
        "baseline_candidate": _candidate_key(baseline),
        "primary_metric_key": primary_metric_key,
        "primary_delta": primary_delta,
        "secondary_metric_key": secondary_metric_key,
        "secondary_delta": secondary_delta,
        "latency_ratio_vs_baseline": latency_ratio,
    }


def _build_use_case_runtime_matrix(
    benchmark_events: list[dict[str, object]],
    manifest: dict[str, object],
    thresholds: dict[str, object],
) -> list[dict[str, object]]:
    role_map = _build_generation_role_map(manifest)
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for event in benchmark_events:
        if str(event.get("group") or "") != "generation" or str(event.get("status") or "") != "success":
            continue
        use_case_id = str(event.get("use_case_id") or "unknown_use_case")
        grouped[use_case_id].append(event)

    rows: list[dict[str, object]] = []
    for use_case_id, events in grouped.items():
        by_candidate: dict[str, list[dict[str, object]]] = defaultdict(list)
        for event in events:
            by_candidate[_candidate_key(event)].append(event)

        ranking: list[dict[str, object]] = []
        for candidate_key, candidate_events in by_candidate.items():
            provider = str(candidate_events[0].get("provider_requested") or "")
            model = str(candidate_events[0].get("model_requested") or "")
            role = str(candidate_events[0].get("candidate_role") or role_map.get(candidate_key) or "challenger")
            successful = [item for item in candidate_events if item.get("status") == "success"]
            ranking.append(
                {
                    "candidate": candidate_key,
                    "provider": provider,
                    "model": model,
                    "candidate_role": role,
                    "runtime_bucket": candidate_events[0].get("runtime_bucket"),
                    "runtime_path": candidate_events[0].get("runtime_path"),
                    "case_count": len(candidate_events),
                    "success_rate": round(len(successful) / max(len(candidate_events), 1), 4),
                    "avg_use_case_fit_score": _average([
                        float(item.get("use_case_fit_score"))
                        for item in candidate_events
                        if isinstance(item.get("use_case_fit_score"), (int, float))
                    ]),
                    "avg_format_adherence": _average([
                        float(item.get("format_adherence"))
                        for item in candidate_events
                        if isinstance(item.get("format_adherence"), (int, float))
                    ]),
                    "avg_groundedness_score": _average([
                        float(item.get("groundedness_score"))
                        for item in candidate_events
                        if isinstance(item.get("groundedness_score"), (int, float))
                    ]),
                    "avg_latency_s": _average([
                        float(item.get("latency_s"))
                        for item in successful
                        if isinstance(item.get("latency_s"), (int, float))
                    ]),
                }
            )
        ranking.sort(
            key=lambda item: (
                -float(item.get("success_rate") or 0.0),
                -float(item.get("avg_use_case_fit_score") or 0.0),
                -float(item.get("avg_format_adherence") or 0.0),
                float(item.get("avg_latency_s") or 10**9),
            )
        )

        best_local = next((item for item in ranking if _is_local_candidate(item)), ranking[0] if ranking else None)
        baseline = _pick_baseline_candidate(ranking)
        change = _decide_change(
            winner=best_local,
            baseline=baseline,
            primary_metric_key="avg_use_case_fit_score",
            min_primary_delta=float(thresholds.get("runtime_win_min_use_case_fit_delta") or 0.03),
            secondary_metric_key="avg_format_adherence",
            min_secondary_delta=float(thresholds.get("runtime_win_min_format_delta") or 0.05),
            latency_key="avg_latency_s",
            max_latency_regression_ratio=float(thresholds.get("runtime_win_max_latency_regression_ratio") or 1.35),
            latency_improvement_ratio=float(thresholds.get("runtime_win_latency_improvement_ratio") or 0.15),
        )

        benchmark_use_case = str(events[0].get("benchmark_use_case") or "")
        task_type = _map_benchmark_use_case_to_task_type(benchmark_use_case, use_case_id)
        rows.append(
            {
                "use_case_id": use_case_id,
                "use_case_label": events[0].get("use_case_label") or use_case_id,
                "benchmark_use_case": benchmark_use_case,
                "task_type": task_type,
                "best_local_candidate": best_local,
                "baseline_candidate": baseline,
                "candidate_ranking": ranking,
                **change,
            }
        )

    rows.sort(key=lambda item: str(item.get("use_case_id") or ""))
    return rows


def _build_embedding_decision(benchmark_summary: dict[str, object], thresholds: dict[str, object]) -> dict[str, object]:
    embeddings = benchmark_summary.get("embeddings") if isinstance(benchmark_summary.get("embeddings"), dict) else {}
    subset_rankings = [item for item in (embeddings.get("subset_rankings") or []) if isinstance(item, dict)]
    preferred_subset = next(
        (item for item in subset_rankings if str(item.get("subset_kind") or "").strip().lower() == "general"),
        None,
    )
    ranking = [item for item in ((preferred_subset or {}).get("candidate_ranking") or embeddings.get("candidate_ranking") or []) if isinstance(item, dict)]
    best = (
        (preferred_subset or {}).get("top_candidate")
        if isinstance((preferred_subset or {}).get("top_candidate"), dict)
        else embeddings.get("top_candidate")
        if isinstance(embeddings.get("top_candidate"), dict)
        else (ranking[0] if ranking else None)
    )
    baseline = _pick_baseline_candidate(ranking)
    decision = _decide_change(
        winner=best,
        baseline=baseline,
        primary_metric_key="avg_mrr",
        min_primary_delta=float(thresholds.get("embedding_win_min_mrr_delta") or 0.05),
        secondary_metric_key="avg_hit_at_1",
        min_secondary_delta=float(thresholds.get("embedding_win_min_hit_at_1_delta") or 0.10),
        latency_key="avg_retrieval_seconds",
        max_latency_regression_ratio=float(thresholds.get("embedding_win_max_latency_regression_ratio") or 1.5),
        latency_improvement_ratio=None,
    )
    return {
        "supported": bool(ranking),
        "preferred_subset": preferred_subset,
        "best_embedding_strategy": best,
        "candidate_ranking": ranking,
        **decision,
    }


def _build_reranker_decision(benchmark_summary: dict[str, object], thresholds: dict[str, object]) -> dict[str, object]:
    rerankers = benchmark_summary.get("rerankers") if isinstance(benchmark_summary.get("rerankers"), dict) else {}
    ranking = [item for item in (rerankers.get("candidate_ranking") or []) if isinstance(item, dict)]
    best = rerankers.get("best_tradeoff") if isinstance(rerankers.get("best_tradeoff"), dict) else (ranking[0] if ranking else None)
    baseline = _pick_baseline_candidate(ranking)
    decision = _decide_change(
        winner=best,
        baseline=baseline,
        primary_metric_key="avg_mrr",
        min_primary_delta=float(thresholds.get("reranker_win_min_mrr_delta") or 0.05),
        secondary_metric_key="avg_groundedness_proxy",
        min_secondary_delta=float(thresholds.get("reranker_win_min_groundedness_delta") or 0.05),
        latency_key="avg_retrieval_seconds",
        max_latency_regression_ratio=float(thresholds.get("reranker_win_max_latency_regression_ratio") or 1.75),
        latency_improvement_ratio=None,
    )
    return {
        "supported": bool(ranking),
        "best_reranker_tradeoff": rerankers.get("best_tradeoff") if isinstance(rerankers.get("best_tradeoff"), dict) else best,
        "candidate_ranking": ranking,
        **decision,
    }


def _build_ocr_vlm_observations(benchmark_summary: dict[str, object]) -> dict[str, object]:
    ocr_vlm = benchmark_summary.get("ocr_vlm") if isinstance(benchmark_summary.get("ocr_vlm"), dict) else {}
    return {
        "supported": bool(ocr_vlm),
        "best_ocr_tradeoff": ocr_vlm.get("best_ocr_tradeoff") if isinstance(ocr_vlm.get("best_ocr_tradeoff"), dict) else None,
        "best_vlm_tradeoff": ocr_vlm.get("best_vlm_tradeoff") if isinstance(ocr_vlm.get("best_vlm_tradeoff"), dict) else None,
        "variant_ranking": [item for item in (ocr_vlm.get("variant_ranking") or []) if isinstance(item, dict)],
        "support_level": ocr_vlm.get("support_level"),
    }


def _build_minimal_experiment_outline(task_row: dict[str, object]) -> dict[str, object]:
    task_type = str(task_row.get("task_type") or "unknown")
    baseline_ratio = _safe_float(task_row.get("avg_score_ratio")) or 0.0
    target_ratio = max(
        float(DIAGNOSIS_THRESHOLDS.get("healthy_avg_score_ratio") or 0.80),
        round(baseline_ratio + 0.10, 3),
    )
    return {
        "experiment_type": "future_lora_peft_scaffold_only",
        "task_scope": task_type,
        "primary_success_metric": TASK_PRIMARY_METRICS.get(task_type, "avg_score_ratio"),
        "baseline_quality": {
            "pass_rate": task_row.get("pass_rate"),
            "fail_rate": task_row.get("fail_rate"),
            "avg_score_ratio": task_row.get("avg_score_ratio"),
        },
        "target_quality": {
            "target_avg_score_ratio": target_ratio,
            "target_fail_rate_max": round(float(task_row.get("fail_rate") or 0.0) * 0.5, 3),
        },
        "scope_constraints": [
            "single narrow task only",
            "offline/local labeled set only",
            "no long-running training job in this phase",
            "compare against prompt + RAG + retrieval baselines before promotion",
        ],
    }


def _build_adaptation_decision(
    eval_diagnosis: dict[str, object],
    use_case_matrix: list[dict[str, object]],
    embedding_decision: dict[str, object],
    reranker_decision: dict[str, object],
) -> dict[str, object]:
    diagnosis_rows = [item for item in (eval_diagnosis.get("task_diagnosis") or []) if isinstance(item, dict)]
    healthy_rows = [item for item in (eval_diagnosis.get("healthy_tasks") or []) if isinstance(item, dict)]
    candidate_rows = [item for item in (eval_diagnosis.get("adaptation_candidates") or []) if isinstance(item, dict)]

    runtime_win_tasks = {
        str(item.get("task_type"))
        for item in use_case_matrix
        if isinstance(item, dict)
        and bool(item.get("change_recommended"))
        and str(item.get("task_type") or "").strip()
    }

    adaptation_not_needed_yet: list[dict[str, object]] = [
        {
            "task_type": item.get("task_type"),
            "reason": "prompt_rag_schema_sufficient",
            "pass_rate": item.get("pass_rate"),
            "avg_score_ratio": item.get("avg_score_ratio"),
        }
        for item in healthy_rows
    ]

    adaptation_candidates: list[dict[str, object]] = []
    deferred_candidates: list[dict[str, object]] = []
    by_task_type = {str(item.get("task_type") or ""): item for item in diagnosis_rows}
    for item in candidate_rows:
        task_type = str(item.get("task_type") or "")
        alternatives_remaining: list[str] = []
        if task_type in runtime_win_tasks:
            alternatives_remaining.append("runtime_or_model_swap")
        if task_type in RETRIEVAL_SENSITIVE_TASKS and bool(embedding_decision.get("change_recommended")):
            alternatives_remaining.append("embedding_strategy_change")
        if task_type in RETRIEVAL_SENSITIVE_TASKS and bool(reranker_decision.get("change_recommended")):
            alternatives_remaining.append("reranker_change")

        enriched = {
            "task_type": task_type,
            "failure_pattern": [reason.get("reason") for reason in (item.get("top_reasons") or []) if isinstance(reason, dict)],
            "current_baseline_quality": {
                "pass_rate": item.get("pass_rate"),
                "fail_rate": item.get("fail_rate"),
                "avg_score_ratio": item.get("avg_score_ratio"),
            },
            "adaptation_priority": item.get("adaptation_priority"),
            "expected_adaptation_target": _build_minimal_experiment_outline(item).get("target_quality"),
            "non_training_alternatives_remaining": alternatives_remaining,
            "why_prompt_rag_retrieval_changes_were_not_enough": (
                "Persistent eval failures remain after prompt/RAG/schema iteration, and benchmark evidence does not show a clearer non-training alternative closing the gap."
                if not alternatives_remaining
                else f"There are still non-training alternatives to exhaust before adaptation: {', '.join(alternatives_remaining)}."
            ),
            "minimal_lora_peft_experiment": _build_minimal_experiment_outline(item),
            "recommended_action": item.get("recommended_action"),
        }
        if alternatives_remaining:
            deferred_candidates.append(enriched)
        else:
            adaptation_candidates.append(enriched)

    adaptation_not_needed_yet.extend(
        {
            "task_type": item.get("task_type"),
            "reason": "non_training_alternatives_remaining",
            "alternatives_remaining": item.get("non_training_alternatives_remaining"),
            "avg_score_ratio": (item.get("current_baseline_quality") or {}).get("avg_score_ratio")
            if isinstance(item.get("current_baseline_quality"), dict)
            else None,
        }
        for item in deferred_candidates
    )

    adaptation_justified = bool(adaptation_candidates)
    if adaptation_justified:
        global_recommendation = "targeted_lightweight_adaptation_justified_for_narrow_tasks"
    elif deferred_candidates:
        global_recommendation = "defer_adaptation_until_runtime_and_retrieval_changes_are_exhausted"
    else:
        global_recommendation = "adaptation_not_needed_yet"

    best_candidate = adaptation_candidates[0] if adaptation_candidates else None
    return {
        "global_recommendation": global_recommendation,
        "adaptation_justified": adaptation_justified,
        "adaptation_not_needed_yet": adaptation_not_needed_yet,
        "adaptation_candidates": adaptation_candidates,
        "deferred_candidates": deferred_candidates,
        "best_candidate": best_candidate,
        "diagnosis_task_count": len(by_task_type),
    }


def _build_decision_matrix(
    use_case_matrix: list[dict[str, object]],
    eval_diagnosis: dict[str, object],
    adaptation_decision: dict[str, object],
) -> list[dict[str, object]]:
    diagnosis_by_task = {
        str(item.get("task_type") or ""): item
        for item in (eval_diagnosis.get("task_diagnosis") or [])
        if isinstance(item, dict)
    }
    adaptation_candidate_tasks = {
        str(item.get("task_type") or "")
        for item in (adaptation_decision.get("adaptation_candidates") or [])
        if isinstance(item, dict)
    }
    rows: list[dict[str, object]] = []
    for item in use_case_matrix:
        task_type = str(item.get("task_type") or "")
        diagnosis = diagnosis_by_task.get(task_type, {})
        best_local = item.get("best_local_candidate") if isinstance(item.get("best_local_candidate"), dict) else {}
        rows.append(
            {
                "use_case_id": item.get("use_case_id"),
                "benchmark_use_case": item.get("benchmark_use_case"),
                "task_type": task_type or None,
                "best_local_candidate": best_local.get("candidate"),
                "best_local_provider": best_local.get("provider"),
                "best_local_model": best_local.get("model"),
                "runtime_model_change_enough": item.get("change_recommended"),
                "runtime_model_reason": item.get("reason"),
                "prompt_rag_schema_status": diagnosis.get("health_label"),
                "prompt_rag_recommendation": diagnosis.get("recommended_action"),
                "adaptation_status": (
                    "adaptation_candidate"
                    if task_type in adaptation_candidate_tasks
                    else "adaptation_not_needed_yet"
                    if diagnosis.get("health_label") == "healthy"
                    else "iterate_before_adaptation"
                ),
            }
        )
    return rows


def build_phase8_5_decision_summary(
    *,
    benchmark_summary: dict[str, object],
    benchmark_events: list[dict[str, object]],
    manifest: dict[str, object] | None = None,
    preflight: dict[str, object] | None = None,
    eval_summary: dict[str, object] | None = None,
    eval_diagnosis: dict[str, object] | None = None,
    benchmark_run_dir: str | None = None,
    decision_thresholds: dict[str, object] | None = None,
) -> dict[str, object]:
    thresholds = {**PHASE8_5_DECISION_THRESHOLDS, **(decision_thresholds or {})}
    manifest_payload = manifest if isinstance(manifest, dict) else {}
    preflight_payload = preflight if isinstance(preflight, dict) else {}
    eval_summary_payload = eval_summary if isinstance(eval_summary, dict) else {}
    eval_diagnosis_payload = eval_diagnosis if isinstance(eval_diagnosis, dict) else {}
    executed_groups = sorted({str(item.get("group") or "") for item in benchmark_events if str(item.get("group") or "").strip()})
    preflight_selected_groups = [str(item) for item in (preflight_payload.get("selected_groups") or []) if str(item).strip()]
    effective_groups = sorted(set(preflight_selected_groups) | set(executed_groups))

    use_case_matrix = _build_use_case_runtime_matrix(benchmark_events, manifest_payload, thresholds)
    runtime_model_decisions = {
        "best_local_runtime_by_use_case": use_case_matrix,
        "runtime_change_recommended_for_any_use_case": any(bool(item.get("change_recommended")) for item in use_case_matrix),
    }
    embedding_decision = _build_embedding_decision(benchmark_summary, thresholds)
    reranker_decision = _build_reranker_decision(benchmark_summary, thresholds)
    ocr_vlm_observations = _build_ocr_vlm_observations(benchmark_summary)
    adaptation_decision = _build_adaptation_decision(
        eval_diagnosis_payload,
        use_case_matrix,
        embedding_decision,
        reranker_decision,
    )
    decision_matrix = _build_decision_matrix(use_case_matrix, eval_diagnosis_payload, adaptation_decision)

    return {
        "phase": "8.5",
        "round": "round3_decision_gate",
        "benchmark_run_dir": benchmark_run_dir,
        "benchmark_run_id": preflight_payload.get("run_id") or (benchmark_events[0].get("run_id") if benchmark_events else None),
        "decision_thresholds": thresholds,
        "benchmark_overview": {
            "total_cases": benchmark_summary.get("total_cases"),
            "successful_cases": benchmark_summary.get("successful_cases"),
            "failed_cases": benchmark_summary.get("failed_cases"),
            "selected_groups": effective_groups,
            "preflight_selected_groups": preflight_selected_groups,
            "executed_groups": executed_groups,
        },
        "runtime_model_decisions": runtime_model_decisions,
        "embedding_decisions": embedding_decision,
        "reranker_decisions": reranker_decision,
        "ocr_vlm_observations": ocr_vlm_observations,
        "eval_summary": {
            "total_runs": eval_summary_payload.get("total_runs"),
            "pass_rate": eval_summary_payload.get("pass_rate"),
            "fail_rate": eval_summary_payload.get("fail_rate"),
            "avg_score_ratio": eval_summary_payload.get("avg_score_ratio"),
            "needs_review_rate": eval_summary_payload.get("needs_review_rate"),
        },
        "eval_diagnosis_summary": {
            "global_recommendation": (eval_diagnosis_payload.get("decision_summary") or {}).get("global_recommendation")
            if isinstance(eval_diagnosis_payload.get("decision_summary"), dict)
            else None,
            "healthy_tasks": [
                item.get("task_type")
                for item in (eval_diagnosis_payload.get("healthy_tasks") or [])
                if isinstance(item, dict)
            ],
            "persistent_failure_tasks": [
                item.get("task_type")
                for item in (eval_diagnosis_payload.get("persistent_failure_tasks") or [])
                if isinstance(item, dict)
            ],
        },
        "adaptation_decision": adaptation_decision,
        "decision_matrix": decision_matrix,
    }


def render_phase8_5_decision_markdown(summary: dict[str, object]) -> str:
    runtime_model = summary.get("runtime_model_decisions") if isinstance(summary.get("runtime_model_decisions"), dict) else {}
    embedding = summary.get("embedding_decisions") if isinstance(summary.get("embedding_decisions"), dict) else {}
    reranker = summary.get("reranker_decisions") if isinstance(summary.get("reranker_decisions"), dict) else {}
    adaptation = summary.get("adaptation_decision") if isinstance(summary.get("adaptation_decision"), dict) else {}
    decision_matrix = [item for item in (summary.get("decision_matrix") or []) if isinstance(item, dict)]
    ocr_vlm = summary.get("ocr_vlm_observations") if isinstance(summary.get("ocr_vlm_observations"), dict) else {}

    lines = [
        "# Phase 8.5 Decision Gate Report",
        "",
        f"- Benchmark run: `{summary.get('benchmark_run_id') or 'n/a'}`",
        f"- Benchmark directory: `{summary.get('benchmark_run_dir') or 'n/a'}`",
        f"- Global adaptation recommendation: `{adaptation.get('global_recommendation') or 'n/a'}`",
        "",
        "## Decision matrix by use case",
        "",
        "| Use case | Task type | Best local candidate | Runtime/model change enough? | Prompt+RAG+schema status | Adaptation status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in decision_matrix:
        lines.append(
            f"| `{item.get('use_case_id')}` | `{item.get('task_type') or '-'}` | `{item.get('best_local_candidate') or '-'}` | `{item.get('runtime_model_change_enough')}` | `{item.get('prompt_rag_schema_status') or '-'}` | `{item.get('adaptation_status') or '-'}` |"
        )

    lines.extend(
        [
            "",
            "## Runtime / model conclusions",
            "",
            f"- Runtime/model change recommended for any use case: `{runtime_model.get('runtime_change_recommended_for_any_use_case')}`",
        ]
    )
    for item in runtime_model.get("best_local_runtime_by_use_case") or []:
        if not isinstance(item, dict):
            continue
        best_local = item.get("best_local_candidate") if isinstance(item.get("best_local_candidate"), dict) else {}
        lines.append(
            f"- `{item.get('use_case_id')}` → best local candidate `{best_local.get('candidate') or 'n/a'}`; change decision: `{item.get('status') or 'n/a'}` ({item.get('reason') or 'n/a'})."
        )

    lines.extend(
        [
            "",
            "## Retrieval conclusions",
            "",
            f"- Best embedding strategy: `{((embedding.get('best_embedding_strategy') or {}).get('candidate')) or 'n/a'}`",
            f"- Embedding change recommended: `{embedding.get('change_recommended')}` ({embedding.get('reason') or 'n/a'})",
            f"- Best reranker tradeoff: `{((reranker.get('best_reranker_tradeoff') or {}).get('candidate_id')) or 'n/a'}`",
            f"- Reranker change recommended: `{reranker.get('change_recommended')}` ({reranker.get('reason') or 'n/a'})",
        ]
    )

    if ocr_vlm.get("supported"):
        lines.extend(
            [
                "",
                "## Supporting OCR / VLM observations",
                "",
                f"- Best OCR fallback tradeoff: `{((ocr_vlm.get('best_ocr_tradeoff') or {}).get('variant')) or 'n/a'}`",
                f"- Best VLM fallback tradeoff: `{((ocr_vlm.get('best_vlm_tradeoff') or {}).get('variant')) or 'n/a'}`",
            ]
        )

    lines.extend(
        [
            "",
            "## Adaptation not needed yet",
            "",
        ]
    )
    not_needed = [item for item in (adaptation.get("adaptation_not_needed_yet") or []) if isinstance(item, dict)]
    if not not_needed:
        lines.append("- No tasks were classified as adaptation-not-needed-yet from the current evidence bundle.")
    else:
        for item in not_needed:
            lines.append(
                f"- `{item.get('task_type')}` → `{item.get('reason')}`"
            )

    lines.extend(
        [
            "",
            "## Adaptation candidates",
            "",
        ]
    )
    candidates = [item for item in (adaptation.get("adaptation_candidates") or []) if isinstance(item, dict)]
    if not candidates:
        lines.append("- No lightweight adaptation candidate is justified yet from the current benchmark + eval evidence.")
    else:
        for item in candidates:
            experiment = item.get("minimal_lora_peft_experiment") if isinstance(item.get("minimal_lora_peft_experiment"), dict) else {}
            target_quality = experiment.get("target_quality") if isinstance(experiment.get("target_quality"), dict) else {}
            lines.append(
                f"- `{item.get('task_type')}` → priority `{item.get('adaptation_priority')}`; failure pattern: {', '.join(item.get('failure_pattern') or []) or 'n/a'}; target avg score ratio: `{target_quality.get('target_avg_score_ratio')}`"
            )

    lines.extend(
        [
            "",
            "## Conservative conclusion",
            "",
            "- This round does not implement full fine-tuning or training jobs.",
            "- Runtime/model swaps are considered first for use-case-level wins.",
            "- Embedding and reranker changes are considered before any adaptation recommendation for retrieval-sensitive tasks.",
            "- Lightweight adaptation is only justified when eval failures persist and benchmark evidence does not show a clearer non-training path.",
            "",
        ]
    )
    return "\n".join(lines)