from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_evidenceops_action_store(path: Path) -> None:
    with _connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS evidenceops_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                run_timestamp TEXT,
                task_type TEXT,
                review_type TEXT,
                tool_used TEXT,
                query TEXT,
                action_type TEXT NOT NULL,
                description TEXT NOT NULL,
                owner TEXT,
                due_date TEXT,
                status TEXT,
                evidence TEXT,
                confidence REAL,
                needs_review INTEGER NOT NULL DEFAULT 0,
                workflow_id TEXT,
                execution_strategy_used TEXT,
                source_count INTEGER NOT NULL DEFAULT 0,
                document_ids_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                action_key TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_evidenceops_actions_action_key ON evidenceops_actions(action_key)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_evidenceops_actions_review_type ON evidenceops_actions(review_type, created_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_evidenceops_actions_status ON evidenceops_actions(status, created_at DESC)"
        )


def _build_action_key(payload: dict[str, Any]) -> str:
    canonical = {
        "run_timestamp": payload.get("run_timestamp"),
        "task_type": payload.get("task_type"),
        "review_type": payload.get("review_type"),
        "tool_used": payload.get("tool_used"),
        "query": payload.get("query"),
        "action_type": payload.get("action_type"),
        "description": payload.get("description"),
        "owner": payload.get("owner"),
        "due_date": payload.get("due_date"),
        "status": payload.get("status"),
        "evidence": payload.get("evidence"),
        "document_ids_json": payload.get("document_ids_json"),
        "workflow_id": payload.get("workflow_id"),
    }
    serialized = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _normalized_document_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_status(value: object) -> str:
    return str(value or "").strip().lower()


def _normalize_owner(value: object) -> str:
    return str(value or "").strip()


def _normalize_due_date(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _is_open_status(value: object) -> bool:
    return _normalize_status(value) in {"open", "in_progress", "pending", "recommended", "suggested"}


def _classify_action_update(
    *,
    current_status: object,
    next_status: object,
    current_owner: object,
    next_owner: object,
    current_due_date: object,
    next_due_date: object,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    normalized_current_status = _normalize_status(current_status)
    normalized_next_status = _normalize_status(next_status)
    normalized_current_owner = _normalize_owner(current_owner)
    normalized_next_owner = _normalize_owner(next_owner)
    normalized_current_due_date = _normalize_due_date(current_due_date)
    normalized_next_due_date = _normalize_due_date(next_due_date)

    if normalized_next_status and normalized_next_status != normalized_current_status and normalized_next_status in {
        "closed",
        "done",
        "completed",
        "resolved",
    }:
        reasons.append("close_action")
    if (
        normalized_current_owner
        and normalized_next_owner
        and normalized_next_owner != normalized_current_owner
    ):
        reasons.append("reassign_owner")
    if (
        normalized_current_due_date
        and normalized_next_due_date
        and normalized_next_due_date != normalized_current_due_date
    ):
        reasons.append("change_due_date")

    sensitivity = "review_required" if reasons else "safe"
    return sensitivity, reasons


def _parse_due_date(value: object) -> date | None:
    normalized = _normalize_due_date(value)
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def _build_action_rows_from_worklog_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(entry, dict):
        return []

    base_payload = {
        "created_at": str(entry.get("timestamp") or ""),
        "run_timestamp": str(entry.get("timestamp") or ""),
        "task_type": str(entry.get("task_type") or "document_agent"),
        "review_type": str(entry.get("review_type") or ""),
        "tool_used": str(entry.get("tool_used") or ""),
        "query": str(entry.get("query") or ""),
        "confidence": float(entry.get("confidence")) if isinstance(entry.get("confidence"), (int, float)) else None,
        "needs_review": 1 if bool(entry.get("needs_review")) else 0,
        "workflow_id": str(entry.get("workflow_id") or "") or None,
        "execution_strategy_used": str(entry.get("execution_strategy_used") or "") or None,
        "source_count": int(entry.get("source_count") or 0),
        "document_ids_json": json.dumps(_normalized_document_ids(entry.get("document_ids")), ensure_ascii=False),
        "metadata_json": json.dumps({"needs_review_reason": entry.get("needs_review_reason")}, ensure_ascii=False),
    }

    rows: list[dict[str, Any]] = []
    for item in entry.get("action_items") or []:
        if not isinstance(item, dict):
            continue
        description = str(item.get("description") or "").strip()
        if not description:
            continue
        payload = {
            **base_payload,
            "action_type": "action_item",
            "description": description,
            "owner": str(item.get("owner") or "").strip() or None,
            "due_date": str(item.get("due_date") or "").strip() or None,
            "status": str(item.get("status") or "suggested").strip() or "suggested",
            "evidence": str(item.get("evidence") or "").strip() or None,
        }
        payload["action_key"] = _build_action_key(payload)
        rows.append(payload)

    for item in entry.get("recommended_actions") or []:
        description = str(item or "").strip()
        if not description:
            continue
        payload = {
            **base_payload,
            "action_type": "recommended_action",
            "description": description,
            "owner": None,
            "due_date": None,
            "status": "recommended",
            "evidence": None,
        }
        payload["action_key"] = _build_action_key(payload)
        rows.append(payload)

    return rows


def append_evidenceops_actions_from_worklog_entry(path: Path, entry: dict[str, Any]) -> int:
    ensure_evidenceops_action_store(path)
    rows = _build_action_rows_from_worklog_entry(entry)
    inserted = 0
    with _connect(path) as connection:
        for row in rows:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO evidenceops_actions (
                    created_at,
                    run_timestamp,
                    task_type,
                    review_type,
                    tool_used,
                    query,
                    action_type,
                    description,
                    owner,
                    due_date,
                    status,
                    evidence,
                    confidence,
                    needs_review,
                    workflow_id,
                    execution_strategy_used,
                    source_count,
                    document_ids_json,
                    metadata_json,
                    action_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("created_at"),
                    row.get("run_timestamp"),
                    row.get("task_type"),
                    row.get("review_type"),
                    row.get("tool_used"),
                    row.get("query"),
                    row.get("action_type"),
                    row.get("description"),
                    row.get("owner"),
                    row.get("due_date"),
                    row.get("status"),
                    row.get("evidence"),
                    row.get("confidence"),
                    row.get("needs_review"),
                    row.get("workflow_id"),
                    row.get("execution_strategy_used"),
                    row.get("source_count"),
                    row.get("document_ids_json"),
                    row.get("metadata_json"),
                    row.get("action_key"),
                ),
            )
            inserted += 1 if int(cursor.rowcount or 0) > 0 else 0
    return inserted


def load_evidenceops_actions(path: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    ensure_evidenceops_action_store(path)
    limit_clause = "LIMIT ?" if isinstance(limit, int) and limit > 0 else ""
    params: list[Any] = [limit] if limit_clause else []
    query = f"""
        SELECT *
        FROM evidenceops_actions
        ORDER BY datetime(created_at) DESC, id DESC
        {limit_clause}
    """
    with _connect(path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [
        {
            "id": int(row["id"]),
            "created_at": row["created_at"],
            "run_timestamp": row["run_timestamp"],
            "task_type": row["task_type"],
            "review_type": row["review_type"],
            "tool_used": row["tool_used"],
            "query": row["query"],
            "action_type": row["action_type"],
            "description": row["description"],
            "owner": row["owner"],
            "due_date": row["due_date"],
            "status": row["status"],
            "evidence": row["evidence"],
            "confidence": row["confidence"],
            "needs_review": bool(row["needs_review"]),
            "workflow_id": row["workflow_id"],
            "execution_strategy_used": row["execution_strategy_used"],
            "source_count": int(row["source_count"] or 0),
            "document_ids": json.loads(row["document_ids_json"] or "[]"),
            "metadata": json.loads(row["metadata_json"] or "{}"),
            "action_key": row["action_key"],
        }
        for row in rows
    ]


def update_evidenceops_action(
    path: Path,
    *,
    action_id: int,
    status: str | None = None,
    owner: str | None = None,
    due_date: str | None = None,
    metadata_patch: dict[str, Any] | None = None,
    approval_status: str | None = None,
    approval_reason: str | None = None,
    approved_by: str | None = None,
) -> dict[str, Any] | None:
    ensure_evidenceops_action_store(path)
    with _connect(path) as connection:
        row = connection.execute(
            "SELECT * FROM evidenceops_actions WHERE id = ?",
            (int(action_id),),
        ).fetchone()
        if row is None:
            return None

        current_metadata = json.loads(row["metadata_json"] or "{}")
        next_metadata = (
            {**current_metadata, **metadata_patch}
            if isinstance(current_metadata, dict) and isinstance(metadata_patch, dict)
            else current_metadata if isinstance(current_metadata, dict)
            else metadata_patch if isinstance(metadata_patch, dict)
            else {}
        )
        next_status = str(status).strip() if isinstance(status, str) and status.strip() else row["status"]
        next_owner = str(owner).strip() if isinstance(owner, str) and owner.strip() else row["owner"]
        next_due_date = str(due_date).strip() if isinstance(due_date, str) and due_date.strip() else row["due_date"]
        sensitivity, sensitivity_reasons = _classify_action_update(
            current_status=row["status"],
            next_status=next_status,
            current_owner=row["owner"],
            next_owner=next_owner,
            current_due_date=row["due_date"],
            next_due_date=next_due_date,
        )
        normalized_approval_status = _normalize_status(approval_status)
        normalized_approval_reason = str(approval_reason or "").strip()
        normalized_approved_by = str(approved_by or "").strip()
        if sensitivity == "review_required" and (
            normalized_approval_status != "approved"
            or not normalized_approval_reason
            or not normalized_approved_by
        ):
            raise PermissionError(
                "Sensitive EvidenceOps action updates require approval_status='approved', approval_reason and approved_by."
            )

        changes: dict[str, dict[str, Any]] = {}
        if next_status != row["status"]:
            changes["status"] = {"from": row["status"], "to": next_status}
        if next_owner != row["owner"]:
            changes["owner"] = {"from": row["owner"], "to": next_owner}
        if next_due_date != row["due_date"]:
            changes["due_date"] = {"from": row["due_date"], "to": next_due_date}

        update_history = current_metadata.get("update_history") if isinstance(current_metadata, dict) else []
        if not isinstance(update_history, list):
            update_history = []
        update_history.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action_id": int(action_id),
                "changes": changes,
                "sensitivity": sensitivity,
                "sensitivity_reasons": sensitivity_reasons,
                "approval_status": normalized_approval_status or ("approved" if sensitivity == "review_required" else "not_required"),
                "approval_reason": normalized_approval_reason or None,
                "approved_by": normalized_approved_by or None,
            }
        )
        if not isinstance(next_metadata, dict):
            next_metadata = {}
        next_metadata["last_update_sensitivity"] = sensitivity
        next_metadata["last_update_reasons"] = sensitivity_reasons
        next_metadata["approval_required"] = sensitivity == "review_required"
        next_metadata["approval_status"] = normalized_approval_status or (
            "approved" if sensitivity == "review_required" else "not_required"
        )
        if normalized_approval_reason:
            next_metadata["approval_reason"] = normalized_approval_reason
        if normalized_approved_by:
            next_metadata["approved_by"] = normalized_approved_by
        next_metadata["update_history"] = update_history

        connection.execute(
            """
            UPDATE evidenceops_actions
            SET status = ?, owner = ?, due_date = ?, metadata_json = ?
            WHERE id = ?
            """,
            (
                next_status,
                next_owner,
                next_due_date,
                json.dumps(next_metadata, ensure_ascii=False),
                int(action_id),
            ),
        )

    entries = load_evidenceops_actions(path)
    return next((entry for entry in entries if int(entry.get("id") or 0) == int(action_id)), None)


def clear_evidenceops_action_store(path: Path) -> None:
    if path.exists():
        path.unlink()


def summarize_evidenceops_actions(entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not entries:
        return {
            "total_actions": 0,
            "open_actions": 0,
            "recommended_actions": 0,
            "actions_with_due_date": 0,
            "actions_without_owner": 0,
            "review_required_actions": 0,
            "approved_actions": 0,
            "pending_approval_actions": 0,
            "overdue_actions": 0,
            "unassigned_open_actions": 0,
            "sensitive_update_count": 0,
            "needs_review_rate": 0.0,
            "unique_document_count": 0,
            "action_type_counts": {},
            "status_counts": {},
            "owner_counts": {},
            "review_type_counts": {},
            "tool_counts": {},
            "latest_created_at": None,
        }

    action_type_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    owner_counter: Counter[str] = Counter()
    review_type_counter: Counter[str] = Counter()
    tool_counter: Counter[str] = Counter()
    unique_documents: set[str] = set()
    needs_review_count = 0
    open_actions = 0
    recommended_actions = 0
    actions_with_due_date = 0
    actions_without_owner = 0
    review_required_actions = 0
    approved_actions = 0
    pending_approval_actions = 0
    overdue_actions = 0
    unassigned_open_actions = 0
    sensitive_update_count = 0
    today = date.today()

    for entry in entries:
        action_type = str(entry.get("action_type") or "").strip()
        status = str(entry.get("status") or "").strip()
        owner = str(entry.get("owner") or "").strip()
        review_type = str(entry.get("review_type") or "").strip()
        tool_used = str(entry.get("tool_used") or "").strip()
        due_date = str(entry.get("due_date") or "").strip()
        metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        approval_required = bool(metadata.get("approval_required"))
        approval_status = _normalize_status(metadata.get("approval_status"))
        last_update_sensitivity = _normalize_status(metadata.get("last_update_sensitivity"))
        update_history = metadata.get("update_history") if isinstance(metadata, dict) else []
        if action_type:
            action_type_counter[action_type] += 1
        if status:
            status_counter[status] += 1
        if owner:
            owner_counter[owner] += 1
        else:
            actions_without_owner += 1
        if review_type:
            review_type_counter[review_type] += 1
        if tool_used:
            tool_counter[tool_used] += 1
        if due_date:
            actions_with_due_date += 1
        if bool(entry.get("needs_review")):
            needs_review_count += 1
        if _is_open_status(status):
            open_actions += 1
            if not owner:
                unassigned_open_actions += 1
        if action_type == "recommended_action":
            recommended_actions += 1
        parsed_due_date = _parse_due_date(due_date)
        if parsed_due_date and _is_open_status(status) and parsed_due_date < today:
            overdue_actions += 1
        if last_update_sensitivity == "review_required" or approval_required:
            review_required_actions += 1
        if approval_status == "approved":
            approved_actions += 1
        elif approval_required:
            pending_approval_actions += 1
        if isinstance(update_history, list):
            sensitive_update_count += sum(
                1
                for item in update_history
                if isinstance(item, dict) and _normalize_status(item.get("sensitivity")) == "review_required"
            )
        for document_id in entry.get("document_ids") or []:
            normalized_document_id = str(document_id or "").strip()
            if normalized_document_id:
                unique_documents.add(normalized_document_id)

    total_actions = len(entries)
    return {
        "total_actions": total_actions,
        "open_actions": open_actions,
        "recommended_actions": recommended_actions,
        "actions_with_due_date": actions_with_due_date,
        "actions_without_owner": actions_without_owner,
        "review_required_actions": review_required_actions,
        "approved_actions": approved_actions,
        "pending_approval_actions": pending_approval_actions,
        "overdue_actions": overdue_actions,
        "unassigned_open_actions": unassigned_open_actions,
        "sensitive_update_count": sensitive_update_count,
        "needs_review_rate": round(needs_review_count / max(total_actions, 1), 3),
        "unique_document_count": len(unique_documents),
        "action_type_counts": dict(action_type_counter),
        "status_counts": dict(status_counter),
        "owner_counts": dict(owner_counter),
        "review_type_counts": dict(review_type_counter),
        "tool_counts": dict(tool_counter),
        "latest_created_at": entries[0].get("created_at"),
    }