from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def load_shadow_log(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def save_shadow_log(path: Path, entries: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_shadow_log_entry(path: Path, entry: dict[str, object]) -> list[dict[str, object]]:
    entries = load_shadow_log(path)
    entries.append(entry)
    save_shadow_log(path, entries)
    return entries


def clear_shadow_log(path: Path) -> None:
    if path.exists():
        path.unlink()


def summarize_shadow_log(entries: list[dict[str, object]]) -> dict[str, object]:
    if not entries:
        return {
            "total_runs": 0,
            "avg_overlap_ratio": 0.0,
            "same_top_1_rate": 0.0,
            "same_top_3_rate": 0.0,
            "strategy_pairs": {},
        }

    total_runs = len(entries)
    overlap_values = [float(item.get("overlap_ratio") or 0.0) for item in entries]
    same_top_1 = sum(1 for item in entries if bool(item.get("same_top_1")))
    same_top_3 = sum(1 for item in entries if bool(item.get("same_top_3_order")))
    pair_counter: Counter[str] = Counter()
    fallback_counter: Counter[str] = Counter()

    for item in entries:
        primary = str(item.get("primary_strategy") or "unknown")
        alternate = str(item.get("alternate_strategy") or "unknown")
        pair_counter[f"{primary} -> {alternate}"] += 1
        fallback = str(item.get("alternate_fallback_reason") or "").strip()
        if fallback:
            fallback_counter[fallback] += 1

    return {
        "total_runs": total_runs,
        "avg_overlap_ratio": round(sum(overlap_values) / max(total_runs, 1), 3),
        "same_top_1_rate": round(same_top_1 / max(total_runs, 1), 3),
        "same_top_3_rate": round(same_top_3 / max(total_runs, 1), 3),
        "strategy_pairs": dict(pair_counter),
        "alternate_fallbacks": dict(fallback_counter),
    }