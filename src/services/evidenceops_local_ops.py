from __future__ import annotations

from pathlib import Path
from typing import Any

from .evidenceops_repository import (
    build_evidenceops_repository_snapshot,
    diff_evidenceops_repository_snapshots,
    list_evidenceops_repository_documents,
    search_evidenceops_repository_documents,
    summarize_evidenceops_repository_documents,
)
from ..storage.phase95_evidenceops_action_store import (
    load_evidenceops_actions,
    summarize_evidenceops_actions,
    update_evidenceops_action,
)
from ..storage.phase95_evidenceops_repository_snapshot import (
    load_evidenceops_repository_snapshot,
    save_evidenceops_repository_snapshot,
)
from ..storage.phase95_evidenceops_worklog import load_evidenceops_worklog, summarize_evidenceops_worklog


def list_evidenceops_repository_entries(
    repository_root: Path,
    *,
    query: str | None = None,
    category: str | None = None,
    suffix: str | None = None,
    document_id: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return list_evidenceops_repository_documents(
        repository_root,
        query=query,
        category=category,
        suffix=suffix,
        document_id=document_id,
        limit=limit,
    )


def search_evidenceops_repository_entries(
    repository_root: Path,
    *,
    query: str,
    category: str | None = None,
    suffix: str | None = None,
    document_id: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return search_evidenceops_repository_documents(
        repository_root,
        query=query,
        category=category,
        suffix=suffix,
        document_id=document_id,
        limit=limit,
    )


def get_evidenceops_repository_document(
    repository_root: Path,
    *,
    relative_path: str | None = None,
    document_id: str | None = None,
) -> dict[str, Any] | None:
    documents = list_evidenceops_repository_documents(repository_root)
    normalized_relative_path = str(relative_path or "").strip()
    normalized_document_id = str(document_id or "").strip()
    for document in documents:
        if normalized_relative_path and str(document.get("relative_path") or "") == normalized_relative_path:
            return document
        if normalized_document_id and str(document.get("document_id") or "") == normalized_document_id:
            return document
    return None


def list_evidenceops_action_items(
    store_path: Path,
    *,
    status: str | None = None,
    owner: str | None = None,
    review_type: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    entries = load_evidenceops_actions(store_path, limit=limit)
    normalized_status = str(status or "").strip().lower()
    normalized_owner = str(owner or "").strip().lower()
    normalized_review_type = str(review_type or "").strip().lower()
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        entry_status = str(entry.get("status") or "").strip().lower()
        entry_owner = str(entry.get("owner") or "").strip().lower()
        entry_review_type = str(entry.get("review_type") or "").strip().lower()
        if normalized_status and entry_status != normalized_status:
            continue
        if normalized_owner and entry_owner != normalized_owner:
            continue
        if normalized_review_type and entry_review_type != normalized_review_type:
            continue
        filtered.append(entry)
    return filtered


def summarize_evidenceops_action_items(store_path: Path, *, limit: int | None = None) -> dict[str, Any]:
    entries = load_evidenceops_actions(store_path, limit=limit)
    return summarize_evidenceops_actions(entries)


def summarize_evidenceops_repository_entries(
    repository_root: Path,
    *,
    category: str | None = None,
    suffix: str | None = None,
    document_id: str | None = None,
) -> dict[str, Any]:
    documents = list_evidenceops_repository_documents(
        repository_root,
        category=category,
        suffix=suffix,
        document_id=document_id,
    )
    return summarize_evidenceops_repository_documents(documents)


def compare_evidenceops_repository_state(
    repository_root: Path,
    *,
    snapshot_path: Path | None = None,
) -> dict[str, Any]:
    resolved_snapshot_path = snapshot_path or (repository_root / ".phase95_evidenceops_repository_snapshot.json")
    previous_snapshot = load_evidenceops_repository_snapshot(resolved_snapshot_path)
    current_snapshot = build_evidenceops_repository_snapshot(repository_root)
    diff = diff_evidenceops_repository_snapshots(previous_snapshot, current_snapshot)
    save_evidenceops_repository_snapshot(resolved_snapshot_path, current_snapshot)
    return {
        **diff,
        "snapshot_path": str(resolved_snapshot_path),
        "repository_root": str(repository_root),
    }


def summarize_evidenceops_worklog_entries(log_path: Path) -> dict[str, Any]:
    entries = load_evidenceops_worklog(log_path)
    return summarize_evidenceops_worklog(entries)


def update_evidenceops_action_item(
    store_path: Path,
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
    return update_evidenceops_action(
        store_path,
        action_id=action_id,
        status=status,
        owner=owner,
        due_date=due_date,
        metadata_patch=metadata_patch,
        approval_status=approval_status,
        approval_reason=approval_reason,
        approved_by=approved_by,
    )