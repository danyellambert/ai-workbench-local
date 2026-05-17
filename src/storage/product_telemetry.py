from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _sanitize_json_like(value: object):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_sanitize_json_like(item) for item in value]
    if isinstance(value, dict):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            if isinstance(key, str):
                sanitized[key] = _sanitize_json_like(item)
        return sanitized
    return str(value)


def load_product_telemetry_runs(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def save_product_telemetry_runs(path: Path, runs: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([_sanitize_json_like(item) for item in runs], ensure_ascii=False, indent=2), encoding="utf-8")


def append_product_telemetry_run(path: Path, run: dict[str, Any]) -> list[dict[str, Any]]:
    runs = load_product_telemetry_runs(path)
    runs.insert(0, _sanitize_json_like(run))
    save_product_telemetry_runs(path, runs)
    return runs


def get_product_telemetry_run(path: Path, run_id: str) -> dict[str, Any] | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    for run in load_product_telemetry_runs(path):
        if str(run.get("run_id") or "").strip() == normalized_run_id:
            return run
    return None


def update_product_telemetry_run(path: Path, run_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    runs = load_product_telemetry_runs(path)
    updated: dict[str, Any] | None = None
    for index, run in enumerate(runs):
        if str(run.get("run_id") or "").strip() != normalized_run_id:
            continue
        updated = {**run, **_sanitize_json_like(patch)}
        runs[index] = updated
        break
    if updated is None:
        return None
    save_product_telemetry_runs(path, runs)
    return updated


def summarize_product_telemetry_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if not runs:
        return {
            "total_runs": 0,
            "completed_runs": 0,
            "warning_runs": 0,
            "error_runs": 0,
            "success_rate": 0.0,
            "error_rate": 0.0,
            "needs_review_rate": 0.0,
            "avg_latency_s": 0.0,
            "avg_retrieval_latency_s": 0.0,
            "avg_generation_latency_s": 0.0,
            "avg_prompt_build_latency_s": 0.0,
            "avg_total_tokens": 0.0,
            "avg_prompt_tokens": 0.0,
            "avg_completion_tokens": 0.0,
            "avg_retrieved_chunks_count": 0.0,
            "avg_context_pressure_ratio": 0.0,
            "max_context_pressure_ratio": 0.0,
            "truncated_prompt_rate": 0.0,
            "total_tokens": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_cost_usd": 0.0,
            "costed_runs": 0,
            "provider_switch_runs": 0,
            "provider_counts": {},
            "workflow_counts": {},
            "surface_counts": {},
            "status_counts": {},
            "latest_timestamp": None,
            "latest_started_at": None,
            "latest_completed_at": None,
        }

    status_counter: Counter[str] = Counter()
    workflow_counter: Counter[str] = Counter()
    provider_counter: Counter[str] = Counter()
    surface_counter: Counter[str] = Counter()
    latencies: list[float] = []
    retrieval_latencies: list[float] = []
    generation_latencies: list[float] = []
    prompt_build_latencies: list[float] = []
    prompt_tokens: list[int] = []
    completion_tokens: list[int] = []
    total_tokens: list[int] = []
    costs: list[float] = []
    retrieved_chunks: list[int] = []
    context_pressure_ratios: list[float] = []
    needs_review_count = 0
    truncated_prompt_runs = 0
    costed_runs = 0
    provider_switch_runs = 0

    for run in runs:
        status = str(run.get("status") or "unknown").strip().lower() or "unknown"
        status_counter[status] += 1
        workflow_id = str(run.get("workflow_id") or "unknown").strip() or "unknown"
        workflow_counter[workflow_id] += 1
        runtime = run.get("runtime") if isinstance(run.get("runtime"), dict) else {}
        provider = str(runtime.get("provider") or "unknown").strip() or "unknown"
        provider_counter[provider] += 1
        surface = str(run.get("surface") or "product_api").strip() or "product_api"
        surface_counter[surface] += 1
        if bool(run.get('needs_review')):
            needs_review_count += 1
        if runtime.get('provider_effective') and runtime.get('provider_requested') and runtime.get('provider_effective') != runtime.get('provider_requested'):
            provider_switch_runs += 1
        if bool(runtime.get('context_window_mode')) and str(runtime.get('context_window_mode')) == 'truncated':
            truncated_prompt_runs += 1
        latency_value = runtime.get('latency_s')
        if isinstance(latency_value, (int, float)):
            latencies.append(float(latency_value))
        retrieval_value = runtime.get('retrieval_latency_s')
        if isinstance(retrieval_value, (int, float)):
            retrieval_latencies.append(float(retrieval_value))
        generation_value = runtime.get('generation_latency_s')
        if isinstance(generation_value, (int, float)):
            generation_latencies.append(float(generation_value))
        prompt_build_value = runtime.get('prompt_build_latency_s')
        if isinstance(prompt_build_value, (int, float)):
            prompt_build_latencies.append(float(prompt_build_value))
        prompt_token_value = runtime.get('prompt_tokens')
        if isinstance(prompt_token_value, (int, float)):
            prompt_tokens.append(int(prompt_token_value))
        completion_token_value = runtime.get('completion_tokens')
        if isinstance(completion_token_value, (int, float)):
            completion_tokens.append(int(completion_token_value))
        total_token_value = runtime.get('total_tokens')
        if isinstance(total_token_value, (int, float)):
            total_tokens.append(int(total_token_value))
        retrieved_value = runtime.get('retrieved_chunks_count')
        if isinstance(retrieved_value, (int, float)):
            retrieved_chunks.append(int(retrieved_value))
        context_pressure_value = runtime.get('context_pressure_ratio')
        if isinstance(context_pressure_value, (int, float)):
            context_pressure_ratios.append(float(context_pressure_value))
        cost_value = runtime.get('cost_usd')
        if isinstance(cost_value, (int, float)):
            costs.append(float(cost_value))
            costed_runs += 1

    total_run_count = len(runs)
    completed_runs = int(status_counter.get("completed", 0))
    warning_runs = int(status_counter.get("warning", 0))
    error_runs = int(status_counter.get("error", 0))
    success_runs = completed_runs + warning_runs
    return {
        "total_runs": total_run_count,
        "completed_runs": completed_runs,
        "warning_runs": warning_runs,
        "error_runs": error_runs,
        "success_rate": round(success_runs / max(total_run_count, 1), 4),
        "error_rate": round(error_runs / max(total_run_count, 1), 4),
        "needs_review_rate": round(needs_review_count / max(total_run_count, 1), 4),
        "avg_latency_s": round(sum(latencies) / max(len(latencies), 1), 4) if latencies else 0.0,
        "avg_retrieval_latency_s": round(sum(retrieval_latencies) / max(len(retrieval_latencies), 1), 4) if retrieval_latencies else 0.0,
        "avg_generation_latency_s": round(sum(generation_latencies) / max(len(generation_latencies), 1), 4) if generation_latencies else 0.0,
        "avg_prompt_build_latency_s": round(sum(prompt_build_latencies) / max(len(prompt_build_latencies), 1), 4) if prompt_build_latencies else 0.0,
        "avg_total_tokens": round(sum(total_tokens) / max(len(total_tokens), 1), 2) if total_tokens else 0.0,
        "avg_prompt_tokens": round(sum(prompt_tokens) / max(len(prompt_tokens), 1), 2) if prompt_tokens else 0.0,
        "avg_completion_tokens": round(sum(completion_tokens) / max(len(completion_tokens), 1), 2) if completion_tokens else 0.0,
        "avg_retrieved_chunks_count": round(sum(retrieved_chunks) / max(len(retrieved_chunks), 1), 2) if retrieved_chunks else 0.0,
        "avg_context_pressure_ratio": round(sum(context_pressure_ratios) / max(len(context_pressure_ratios), 1), 4) if context_pressure_ratios else 0.0,
        "max_context_pressure_ratio": round(max(context_pressure_ratios), 4) if context_pressure_ratios else 0.0,
        "truncated_prompt_rate": round(truncated_prompt_runs / max(total_run_count, 1), 4),
        "total_tokens": int(sum(total_tokens)) if total_tokens else 0,
        "total_prompt_tokens": int(sum(prompt_tokens)) if prompt_tokens else 0,
        "total_completion_tokens": int(sum(completion_tokens)) if completion_tokens else 0,
        "total_cost_usd": round(sum(costs), 6) if costs else 0.0,
        "avg_cost_usd": round(sum(costs) / max(costed_runs, 1), 6) if costs else 0.0,
        "costed_runs": costed_runs,
        "provider_switch_runs": provider_switch_runs,
        "provider_counts": dict(provider_counter),
        "workflow_counts": dict(workflow_counter),
        "surface_counts": dict(surface_counter),
        "status_counts": dict(status_counter),
        "latest_timestamp": runs[0].get("completed_at") or runs[0].get("started_at"),
        "latest_started_at": runs[0].get("started_at"),
        "latest_completed_at": runs[0].get("completed_at"),
    }

def build_telemetry_provider_breakdown(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        runtime = run.get("runtime") if isinstance(run.get("runtime"), dict) else {}
        provider = str(runtime.get("provider") or "unknown")
        model = str(runtime.get("model") or "unknown")
        grouped[(provider, model)].append(run)
    rows: list[dict[str, Any]] = []
    for (provider, model), items in grouped.items():
        total = len(items)
        errors = sum(1 for item in items if str(item.get("status") or "").lower() == "error")
        reviews = sum(1 for item in items if bool(item.get("needs_review")))
        latencies = [float((item.get("runtime") or {}).get("latency_s")) for item in items if isinstance((item.get("runtime") or {}).get("latency_s"), (int, float))]
        tokens = [float((item.get("runtime") or {}).get("total_tokens")) for item in items if isinstance((item.get("runtime") or {}).get("total_tokens"), (int, float))]
        rows.append({
            "key": f"{provider}:{model}",
            "provider": provider,
            "model": model,
            "runs": total,
            "errorRate": round(errors / max(total, 1), 3),
            "needsReviewRate": round(reviews / max(total, 1), 3),
            "avgLatencyS": round(sum(latencies) / max(len(latencies), 1), 3) if latencies else 0.0,
            "avgTotalTokens": round(sum(tokens) / max(len(tokens), 1), 1) if tokens else 0.0,
        })
    rows.sort(key=lambda item: (-int(item.get("runs") or 0), str(item.get("provider") or ""), str(item.get("model") or "")))
    return rows
