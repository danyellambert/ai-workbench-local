from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def load_langgraph_shadow_log(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def save_langgraph_shadow_log(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_langgraph_shadow_log_entry(path: Path, entry: dict[str, object]) -> list[dict[str, object]]:
    entries = load_langgraph_shadow_log(path)
    entries.append(entry)
    save_langgraph_shadow_log(path, entries)
    return entries


def clear_langgraph_shadow_log(path: Path) -> None:
    if path.exists():
        path.unlink()


def summarize_langgraph_shadow_log(entries: list[dict[str, object]]) -> dict[str, object]:
    if not entries:
        return {
            "total_runs": 0,
            "same_success_rate": 0.0,
            "avg_latency_delta_s": 0.0,
            "avg_quality_delta": 0.0,
            "alternate_better_quality_count": 0,
            "primary_better_quality_count": 0,
            "alternate_faster_count": 0,
            "primary_faster_count": 0,
            "alternate_avoided_review_count": 0,
            "strategy_pairs": {},
            "alternate_fallbacks": {},
        }

    total_runs = len(entries)
    same_success = sum(1 for item in entries if bool(item.get("same_success")))
    latency_deltas = [
        float(item.get("latency_delta_s"))
        for item in entries
        if isinstance(item.get("latency_delta_s"), (int, float))
    ]
    quality_deltas = [
        float(item.get("quality_delta"))
        for item in entries
        if isinstance(item.get("quality_delta"), (int, float))
    ]

    pair_counter: Counter[str] = Counter()
    fallback_counter: Counter[str] = Counter()
    for item in entries:
        primary = str(item.get("primary_strategy_used") or item.get("primary_strategy_requested") or "unknown")
        alternate = str(item.get("alternate_strategy_used") or item.get("alternate_strategy_requested") or "unknown")
        pair_counter[f"{primary} -> {alternate}"] += 1
        fallback = str(item.get("alternate_fallback_reason") or "").strip()
        if fallback:
            fallback_counter[fallback] += 1

    return {
        "total_runs": total_runs,
        "same_success_rate": round(same_success / max(total_runs, 1), 3),
        "avg_latency_delta_s": round(sum(latency_deltas) / max(len(latency_deltas), 1), 3) if latency_deltas else 0.0,
        "avg_quality_delta": round(sum(quality_deltas) / max(len(quality_deltas), 1), 3) if quality_deltas else 0.0,
        "alternate_better_quality_count": sum(1 for item in entries if bool(item.get("alternate_better_quality"))),
        "primary_better_quality_count": sum(1 for item in entries if bool(item.get("primary_better_quality"))),
        "alternate_faster_count": sum(1 for item in entries if bool(item.get("alternate_faster"))),
        "primary_faster_count": sum(1 for item in entries if bool(item.get("primary_faster"))),
        "alternate_avoided_review_count": sum(1 for item in entries if bool(item.get("alternate_avoided_review"))),
        "strategy_pairs": dict(pair_counter),
        "alternate_fallbacks": dict(fallback_counter),
    }