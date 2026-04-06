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


def load_evidenceops_worklog(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def save_evidenceops_worklog(path: Path, entries: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def append_evidenceops_worklog_entry(path: Path, entry: dict[str, object]) -> list[dict[str, object]]:
    entries = load_evidenceops_worklog(path)
    entries.append(_sanitize_json_like(entry))
    save_evidenceops_worklog(path, entries)
    return entries


def clear_evidenceops_worklog(path: Path) -> None:
    if path.exists():
        path.unlink()


def summarize_evidenceops_worklog(entries: list[dict[str, object]]) -> dict[str, object]:
    if not entries:
        return {
            "total_runs": 0,
            "needs_review_rate": 0.0,
            "avg_confidence": 0.0,
            "avg_source_count": 0.0,
            "total_findings": 0,
            "total_action_items": 0,
            "total_recommended_actions": 0,
            "unique_document_count": 0,
            "review_type_counts": {},
            "tool_counts": {},
            "finding_type_counts": {},
            "owner_counts": {},
            "status_counts": {},
            "due_date_counts": {},
            "latest_timestamp": None,
        }

    total_runs = len(entries)
    needs_review_count = sum(1 for item in entries if bool(item.get("needs_review")))
    confidences = [
        float(item.get("confidence"))
        for item in entries
        if isinstance(item.get("confidence"), (int, float))
    ]
    source_counts = [
        int(item.get("source_count"))
        for item in entries
        if isinstance(item.get("source_count"), (int, float))
    ]

    review_type_counter: Counter[str] = Counter()
    tool_counter: Counter[str] = Counter()
    finding_type_counter: Counter[str] = Counter()
    owner_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    due_date_counter: Counter[str] = Counter()
    total_findings = 0
    total_action_items = 0
    total_recommended_actions = 0
    unique_documents: set[str] = set()

    for item in entries:
        review_type = str(item.get("review_type") or "").strip()
        tool_used = str(item.get("tool_used") or "").strip()
        findings = item.get("findings") if isinstance(item.get("findings"), list) else []
        action_items = item.get("action_items") if isinstance(item.get("action_items"), list) else []
        recommended_actions = item.get("recommended_actions") if isinstance(item.get("recommended_actions"), list) else []
        document_ids = item.get("document_ids") if isinstance(item.get("document_ids"), list) else []
        total_findings += len(findings)
        total_action_items += len(action_items)
        total_recommended_actions += len(recommended_actions)
        if review_type:
            review_type_counter[review_type] += 1
        if tool_used:
            tool_counter[tool_used] += 1
        for document_id in document_ids:
            normalized_document_id = str(document_id or "").strip()
            if normalized_document_id:
                unique_documents.add(normalized_document_id)
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            finding_type = str(finding.get("finding_type") or "").strip()
            if finding_type:
                finding_type_counter[finding_type] += 1
        for action in action_items:
            if not isinstance(action, dict):
                continue
            owner = str(action.get("owner") or "").strip()
            status = str(action.get("status") or "").strip()
            due_date = str(action.get("due_date") or "").strip()
            if owner:
                owner_counter[owner] += 1
            if status:
                status_counter[status] += 1
            if due_date:
                due_date_counter[due_date] += 1

    return {
        "total_runs": total_runs,
        "needs_review_rate": round(needs_review_count / max(total_runs, 1), 3),
        "avg_confidence": round(sum(confidences) / max(len(confidences), 1), 3) if confidences else 0.0,
        "avg_source_count": round(sum(source_counts) / max(len(source_counts), 1), 3) if source_counts else 0.0,
        "total_findings": total_findings,
        "total_action_items": total_action_items,
        "total_recommended_actions": total_recommended_actions,
        "unique_document_count": len(unique_documents),
        "review_type_counts": dict(review_type_counter),
        "tool_counts": dict(tool_counter),
        "finding_type_counts": dict(finding_type_counter),
        "owner_counts": dict(owner_counter),
        "status_counts": dict(status_counter),
        "due_date_counts": dict(due_date_counter),
        "latest_timestamp": entries[-1].get("timestamp"),
    }