from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def load_document_agent_log(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def save_document_agent_log(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_document_agent_log_entry(path: Path, entry: dict[str, object]) -> list[dict[str, object]]:
    entries = load_document_agent_log(path)
    entries.append(entry)
    save_document_agent_log(path, entries)
    return entries


def clear_document_agent_log(path: Path) -> None:
    if path.exists():
        path.unlink()


def summarize_document_agent_log(entries: list[dict[str, object]]) -> dict[str, object]:
    if not entries:
        return {
            "total_runs": 0,
            "success_rate": 0.0,
            "needs_review_rate": 0.0,
            "avg_confidence": 0.0,
            "avg_source_count": 0.0,
            "avg_available_tools": 0.0,
            "runs_with_tool_errors": 0,
            "intent_counts": {},
            "tool_counts": {},
            "answer_mode_counts": {},
            "execution_strategy_counts": {},
            "review_reasons": {},
        }

    total_runs = len(entries)
    success_count = sum(1 for item in entries if bool(item.get("success")))
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
    available_tools_counts = [
        int(item.get("available_tools_count"))
        for item in entries
        if isinstance(item.get("available_tools_count"), (int, float))
    ]

    intent_counter: Counter[str] = Counter()
    tool_counter: Counter[str] = Counter()
    answer_mode_counter: Counter[str] = Counter()
    strategy_counter: Counter[str] = Counter()
    review_reason_counter: Counter[str] = Counter()

    runs_with_tool_errors = 0
    for item in entries:
        intent = str(item.get("user_intent") or "").strip()
        tool = str(item.get("tool_used") or "").strip()
        answer_mode = str(item.get("answer_mode") or "").strip()
        strategy = str(item.get("execution_strategy_used") or "").strip()
        review_reason = str(item.get("needs_review_reason") or "").strip()
        error_tool_runs = int(item.get("error_tool_runs") or 0)
        if error_tool_runs > 0:
            runs_with_tool_errors += 1
        if intent:
            intent_counter[intent] += 1
        if tool:
            tool_counter[tool] += 1
        if answer_mode:
            answer_mode_counter[answer_mode] += 1
        if strategy:
            strategy_counter[strategy] += 1
        if review_reason:
            review_reason_counter[review_reason] += 1

    return {
        "total_runs": total_runs,
        "success_rate": round(success_count / max(total_runs, 1), 3),
        "needs_review_rate": round(needs_review_count / max(total_runs, 1), 3),
        "avg_confidence": round(sum(confidences) / max(len(confidences), 1), 3) if confidences else 0.0,
        "avg_source_count": round(sum(source_counts) / max(len(source_counts), 1), 3) if source_counts else 0.0,
        "avg_available_tools": round(sum(available_tools_counts) / max(len(available_tools_counts), 1), 3) if available_tools_counts else 0.0,
        "runs_with_tool_errors": runs_with_tool_errors,
        "intent_counts": dict(intent_counter),
        "tool_counts": dict(tool_counter),
        "answer_mode_counts": dict(answer_mode_counter),
        "execution_strategy_counts": dict(strategy_counter),
        "review_reasons": dict(review_reason_counter),
    }