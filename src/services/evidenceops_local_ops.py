from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.config import EvidenceOpsExternalSettings, get_evidenceops_external_settings
from .evidenceops_external_targets import (
    build_nextcloud_repository_snapshot,
    get_nextcloud_repository_document,
    list_nextcloud_repository_documents,
)
from .evidenceops_repository import (
    build_evidenceops_repository_snapshot,
    diff_evidenceops_repository_snapshots,
    list_evidenceops_repository_documents,
    search_evidenceops_repository_documents,
    summarize_evidenceops_repository_documents,
)
from ..storage.phase95_evidenceops_action_store import (
    append_evidenceops_actions_from_worklog_entry,
    load_evidenceops_actions,
    summarize_evidenceops_actions,
    update_evidenceops_action,
)
from ..storage.phase95_evidenceops_repository_snapshot import (
    load_evidenceops_repository_snapshot,
    save_evidenceops_repository_snapshot,
)
from ..storage.phase95_evidenceops_worklog import load_evidenceops_worklog, summarize_evidenceops_worklog
from ..storage.phase95_evidenceops_worklog import append_evidenceops_worklog_entry


def _resolve_repository_backend(
    repository_backend: str | None = None,
    *,
    external_settings: EvidenceOpsExternalSettings | None = None,
) -> str:
    if repository_backend is not None:
        normalized = str(repository_backend).strip().lower()
        return normalized or "local"
    if external_settings is not None:
        normalized = str(external_settings.repository_backend or "").strip().lower()
        return normalized or "local"
    normalized = str(os.getenv("EVIDENCEOPS_REPOSITORY_BACKEND", "")).strip().lower()
    return normalized or "local"


def list_evidenceops_repository_entries(
    repository_root: Path,
    *,
    query: str | None = None,
    category: str | None = None,
    suffix: str | None = None,
    document_id: str | None = None,
    limit: int | None = None,
    repository_backend: str | None = None,
    external_settings: EvidenceOpsExternalSettings | None = None,
) -> list[dict[str, Any]]:
    resolved_settings = external_settings or get_evidenceops_external_settings()
    resolved_backend = _resolve_repository_backend(repository_backend, external_settings=resolved_settings)
    if resolved_backend == "nextcloud_webdav":
        return list_nextcloud_repository_documents(
            settings=resolved_settings,
            query=query,
            category=category,
            suffix=suffix,
            document_id=document_id,
            limit=limit,
        )
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
    repository_backend: str | None = None,
    external_settings: EvidenceOpsExternalSettings | None = None,
) -> list[dict[str, Any]]:
    return list_evidenceops_repository_entries(
        repository_root,
        query=query,
        category=category,
        suffix=suffix,
        document_id=document_id,
        limit=limit,
        repository_backend=repository_backend,
        external_settings=external_settings,
    )


def get_evidenceops_repository_document(
    repository_root: Path,
    *,
    relative_path: str | None = None,
    document_id: str | None = None,
    repository_backend: str | None = None,
    external_settings: EvidenceOpsExternalSettings | None = None,
) -> dict[str, Any] | None:
    resolved_settings = external_settings or get_evidenceops_external_settings()
    resolved_backend = _resolve_repository_backend(repository_backend, external_settings=resolved_settings)
    if resolved_backend == "nextcloud_webdav":
        return get_nextcloud_repository_document(
            settings=resolved_settings,
            relative_path=relative_path,
            document_id=document_id,
        )
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
    repository_backend: str | None = None,
    external_settings: EvidenceOpsExternalSettings | None = None,
) -> dict[str, Any]:
    resolved_settings = external_settings or get_evidenceops_external_settings()
    resolved_backend = _resolve_repository_backend(repository_backend, external_settings=resolved_settings)
    documents = list_evidenceops_repository_entries(
        repository_root,
        category=category,
        suffix=suffix,
        document_id=document_id,
        repository_backend=resolved_backend,
        external_settings=resolved_settings,
    )
    return {
        **summarize_evidenceops_repository_documents(documents),
        "repository_backend": resolved_backend,
    }


def compare_evidenceops_repository_state(
    repository_root: Path,
    *,
    snapshot_path: Path | None = None,
    repository_backend: str | None = None,
    external_settings: EvidenceOpsExternalSettings | None = None,
) -> dict[str, Any]:
    resolved_settings = external_settings or get_evidenceops_external_settings()
    resolved_backend = _resolve_repository_backend(repository_backend, external_settings=resolved_settings)
    resolved_snapshot_path = snapshot_path or (repository_root / ".phase95_evidenceops_repository_snapshot.json")
    previous_snapshot = load_evidenceops_repository_snapshot(resolved_snapshot_path)
    current_snapshot = (
        build_nextcloud_repository_snapshot(settings=resolved_settings)
        if resolved_backend == "nextcloud_webdav"
        else build_evidenceops_repository_snapshot(repository_root)
    )
    diff = diff_evidenceops_repository_snapshots(previous_snapshot, current_snapshot)
    save_evidenceops_repository_snapshot(resolved_snapshot_path, current_snapshot)
    return {
        **diff,
        "snapshot_path": str(resolved_snapshot_path),
        "repository_root": str(repository_root) if resolved_backend == "local" else resolved_settings.nextcloud.root_path,
        "repository_backend": resolved_backend,
    }


def summarize_evidenceops_worklog_entries(log_path: Path) -> dict[str, Any]:
    entries = load_evidenceops_worklog(log_path)
    return summarize_evidenceops_worklog(entries)


def register_evidenceops_entry(
    worklog_path: Path,
    store_path: Path,
    *,
    entry: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError("'entry' must be a dictionary.")

    worklog_entries = append_evidenceops_worklog_entry(worklog_path, entry)
    inserted_actions = append_evidenceops_actions_from_worklog_entry(store_path, entry)
    action_entries = load_evidenceops_actions(store_path)
    return {
        "registered_entry": entry,
        "worklog_total_runs": len(worklog_entries),
        "actions_inserted": int(inserted_actions),
        "worklog_summary": summarize_evidenceops_worklog(worklog_entries),
        "action_summary": summarize_evidenceops_actions(action_entries),
    }


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