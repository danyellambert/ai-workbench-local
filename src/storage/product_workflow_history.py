from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def load_product_workflow_history(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def save_product_workflow_history(path: Path, entries: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def append_product_workflow_history_entry(path: Path, entry: dict[str, object]) -> list[dict[str, object]]:
    entries = load_product_workflow_history(path)
    entries.append(entry)
    save_product_workflow_history(path, entries)
    return entries


def get_product_workflow_history_entry(path: Path, run_id: str) -> dict[str, object] | None:
    normalized_id = str(run_id or "").strip()
    if not normalized_id:
        return None
    entries = load_product_workflow_history(path)
    for entry in entries:
        if str(entry.get("id") or "").strip() == normalized_id:
            return entry
    return None


def update_product_workflow_history_entry(path: Path, run_id: str, patch: dict[str, object]) -> dict[str, object] | None:
    normalized_id = str(run_id or "").strip()
    if not normalized_id:
        return None
    entries = load_product_workflow_history(path)
    updated_entry: dict[str, object] | None = None
    for index, entry in enumerate(entries):
        if str(entry.get("id") or "").strip() != normalized_id:
            continue
        updated_entry = {**entry, **patch}
        entries[index] = updated_entry
        break
    if updated_entry is None:
        return None
    save_product_workflow_history(path, entries)
    return updated_entry


def summarize_product_workflow_history(entries: list[dict[str, object]]) -> dict[str, object]:
    if not entries:
        return {
            "total_runs": 0,
            "completed_runs": 0,
            "warning_runs": 0,
            "error_runs": 0,
            "workflow_counts": {},
            "latest_timestamp": None,
        }

    status_counter: Counter[str] = Counter()
    workflow_counter: Counter[str] = Counter()
    for entry in entries:
        status = str(entry.get("status") or "").strip().lower()
        workflow_label = str(entry.get("workflow_label") or entry.get("workflow_id") or "").strip()
        if status:
            status_counter[status] += 1
        if workflow_label:
            workflow_counter[workflow_label] += 1

    return {
        "total_runs": len(entries),
        "completed_runs": int(status_counter.get("completed", 0) + status_counter.get("warning", 0)),
        "warning_runs": int(status_counter.get("warning", 0)),
        "error_runs": int(status_counter.get("error", 0)),
        "workflow_counts": dict(workflow_counter),
        "latest_timestamp": entries[-1].get("timestamp"),
    }