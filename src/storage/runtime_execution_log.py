from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


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


def load_runtime_execution_log(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def save_runtime_execution_log(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_runtime_execution_log_entry(path: Path, entry: dict[str, object]) -> list[dict[str, object]]:
    entries = load_runtime_execution_log(path)
    entries.append(_sanitize_json_like(entry))
    save_runtime_execution_log(path, entries)
    return entries


def clear_runtime_execution_log(path: Path) -> None:
    if path.exists():
        path.unlink()


def summarize_runtime_execution_log(entries: list[dict[str, object]]) -> dict[str, object]:
    if not entries:
        return {
            "total_runs": 0,
            "success_rate": 0.0,
            "error_rate": 0.0,
            "needs_review_rate": 0.0,
            "avg_latency_s": 0.0,
            "avg_retrieval_latency_s": 0.0,
            "avg_generation_latency_s": 0.0,
            "avg_prompt_chars": 0.0,
            "avg_output_chars": 0.0,
            "avg_context_chars": 0.0,
            "total_prompt_tokens": 0,
            "avg_prompt_tokens": 0.0,
            "total_completion_tokens": 0,
            "avg_completion_tokens": 0.0,
            "total_tokens": 0,
            "avg_total_tokens": 0.0,
            "total_cost_usd": 0.0,
            "avg_cost_usd": 0.0,
            "costed_runs": 0,
            "usage_source_counts": {},
            "flow_counts": {},
            "task_counts": {},
            "provider_counts": {},
            "model_counts": {},
            "latest_timestamp": None,
        }

    total_runs = len(entries)
    success_count = sum(1 for item in entries if bool(item.get("success")))
    needs_review_count = sum(1 for item in entries if bool(item.get("needs_review")))
    error_count = sum(1 for item in entries if str(item.get("error_message") or "").strip())

    latencies = [
        float(item.get("latency_s"))
        for item in entries
        if isinstance(item.get("latency_s"), (int, float))
    ]
    retrieval_latencies = [
        float(item.get("retrieval_latency_s"))
        for item in entries
        if isinstance(item.get("retrieval_latency_s"), (int, float))
    ]
    generation_latencies = [
        float(item.get("generation_latency_s"))
        for item in entries
        if isinstance(item.get("generation_latency_s"), (int, float))
    ]
    prompt_chars = [
        int(item.get("prompt_chars"))
        for item in entries
        if isinstance(item.get("prompt_chars"), (int, float))
    ]
    output_chars = [
        int(item.get("output_chars"))
        for item in entries
        if isinstance(item.get("output_chars"), (int, float))
    ]
    context_chars = [
        int(item.get("context_chars"))
        for item in entries
        if isinstance(item.get("context_chars"), (int, float))
    ]
    prompt_tokens = [
        int(item.get("prompt_tokens"))
        for item in entries
        if isinstance(item.get("prompt_tokens"), (int, float))
    ]
    completion_tokens = [
        int(item.get("completion_tokens"))
        for item in entries
        if isinstance(item.get("completion_tokens"), (int, float))
    ]
    total_tokens = [
        int(item.get("total_tokens"))
        for item in entries
        if isinstance(item.get("total_tokens"), (int, float))
    ]
    cost_values = [
        float(item.get("cost_usd"))
        for item in entries
        if isinstance(item.get("cost_usd"), (int, float))
    ]

    flow_counter: Counter[str] = Counter()
    task_counter: Counter[str] = Counter()
    provider_counter: Counter[str] = Counter()
    model_counter: Counter[str] = Counter()
    usage_source_counter: Counter[str] = Counter()

    for item in entries:
        flow_type = str(item.get("flow_type") or "").strip()
        task_type = str(item.get("task_type") or "").strip()
        provider = str(item.get("provider") or "").strip()
        model = str(item.get("model") or "").strip()
        usage_source = str(item.get("usage_source") or "").strip()
        if flow_type:
            flow_counter[flow_type] += 1
        if task_type:
            task_counter[task_type] += 1
        if provider:
            provider_counter[provider] += 1
        if model:
            model_counter[model] += 1
        if usage_source:
            usage_source_counter[usage_source] += 1

    return {
        "total_runs": total_runs,
        "success_rate": round(success_count / max(total_runs, 1), 3),
        "error_rate": round(error_count / max(total_runs, 1), 3),
        "needs_review_rate": round(needs_review_count / max(total_runs, 1), 3),
        "avg_latency_s": round(sum(latencies) / max(len(latencies), 1), 3) if latencies else 0.0,
        "avg_retrieval_latency_s": round(sum(retrieval_latencies) / max(len(retrieval_latencies), 1), 3) if retrieval_latencies else 0.0,
        "avg_generation_latency_s": round(sum(generation_latencies) / max(len(generation_latencies), 1), 3) if generation_latencies else 0.0,
        "avg_prompt_chars": round(sum(prompt_chars) / max(len(prompt_chars), 1), 3) if prompt_chars else 0.0,
        "avg_output_chars": round(sum(output_chars) / max(len(output_chars), 1), 3) if output_chars else 0.0,
        "avg_context_chars": round(sum(context_chars) / max(len(context_chars), 1), 3) if context_chars else 0.0,
        "total_prompt_tokens": sum(prompt_tokens),
        "avg_prompt_tokens": round(sum(prompt_tokens) / max(len(prompt_tokens), 1), 3) if prompt_tokens else 0.0,
        "total_completion_tokens": sum(completion_tokens),
        "avg_completion_tokens": round(sum(completion_tokens) / max(len(completion_tokens), 1), 3) if completion_tokens else 0.0,
        "total_tokens": sum(total_tokens),
        "avg_total_tokens": round(sum(total_tokens) / max(len(total_tokens), 1), 3) if total_tokens else 0.0,
        "total_cost_usd": round(sum(cost_values), 6) if cost_values else 0.0,
        "avg_cost_usd": round(sum(cost_values) / max(len(cost_values), 1), 6) if cost_values else 0.0,
        "costed_runs": len(cost_values),
        "usage_source_counts": dict(usage_source_counter),
        "flow_counts": dict(flow_counter),
        "task_counts": dict(task_counter),
        "provider_counts": dict(provider_counter),
        "model_counts": dict(model_counter),
        "latest_timestamp": entries[-1].get("timestamp"),
    }