from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4


_STEP_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("extraction", "Extraction"),
    ("chunking", "Chunking"),
    ("embeddings", "Embeddings"),
    ("index_sync", "Index Sync"),
)

_JOB_STORE: dict[str, dict[str, Any]] = {}
_JOB_LOCK = Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_steps() -> list[dict[str, Any]]:
    now = _now_iso()
    return [
        {
            "key": key,
            "label": label,
            "status": "pending",
            "detail": None,
            "updated_at": now,
            "metadata": {},
        }
        for key, label in _STEP_DEFINITIONS
    ]


def _coerce_progress_pct(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return max(0.0, min(100.0, float(value)))
    return None


def _format_stage_detail(detail: str | None, metadata: dict[str, Any] | None = None) -> str | None:
    normalized_detail = str(detail or "").strip() or None
    progress_pct = _coerce_progress_pct((metadata or {}).get("progress_pct") if isinstance(metadata, dict) else None)
    if progress_pct is None:
        return normalized_detail

    progress_label = f"{int(round(progress_pct))}%"
    if not normalized_detail:
        return progress_label
    if normalized_detail.startswith(progress_label):
        return normalized_detail
    return f"{progress_label} · {normalized_detail}"


def create_product_upload_job(*, uploaded_count: int, ignored_count: int = 0) -> dict[str, Any]:
    job_id = uuid4().hex[:12]
    payload = {
        "ok": True,
        "job_id": job_id,
        "status": "queued",
        "message": "Upload accepted. Preparing ingestion pipeline.",
        "uploaded_count": int(uploaded_count),
        "ignored_count": int(ignored_count),
        "current_stage": None,
        "steps": _build_steps(),
        "indexed_documents": [],
        "document_library": None,
        "index_status": None,
        "error": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    with _JOB_LOCK:
        _JOB_STORE[job_id] = payload
    return deepcopy(payload)


def get_product_upload_job(job_id: str) -> dict[str, Any] | None:
    with _JOB_LOCK:
        payload = _JOB_STORE.get(str(job_id or "").strip())
        return deepcopy(payload) if payload is not None else None


def mark_product_upload_job_running(job_id: str, *, message: str | None = None) -> dict[str, Any] | None:
    with _JOB_LOCK:
        payload = _JOB_STORE.get(job_id)
        if payload is None:
            return None
        payload["status"] = "running"
        payload["message"] = message or payload.get("message") or "Ingestion pipeline running."
        payload["updated_at"] = _now_iso()
        return deepcopy(payload)


def reset_product_upload_job_steps(
    job_id: str,
    *,
    message: str | None = None,
    document_name: str | None = None,
    current_document: int | None = None,
    total_documents: int | None = None,
) -> dict[str, Any] | None:
    """Reset the visible pipeline cards before a new document starts."""
    metadata: dict[str, Any] = {}
    if document_name:
        metadata["document_name"] = document_name
    if current_document is not None:
        metadata["current_document"] = int(current_document)
    if total_documents is not None:
        metadata["total_documents"] = int(total_documents)

    with _JOB_LOCK:
        payload = _JOB_STORE.get(job_id)
        if payload is None:
            return None
        payload["status"] = "running"
        payload["message"] = message or payload.get("message") or "Running ingestion pipeline."
        payload["current_stage"] = None
        payload["updated_at"] = _now_iso()
        for step in payload.get("steps", []):
            step["status"] = "pending"
            step["detail"] = None
            step["updated_at"] = payload["updated_at"]
            step["metadata"] = dict(metadata)
        return deepcopy(payload)


def update_product_upload_job_stage(
    job_id: str,
    stage_key: str,
    *,
    status: str,
    detail: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    with _JOB_LOCK:
        payload = _JOB_STORE.get(job_id)
        if payload is None:
            return None
        payload["status"] = "running" if status not in {"error", "completed"} else payload.get("status", "running")
        payload["current_stage"] = stage_key
        payload["updated_at"] = _now_iso()
        for step in payload.get("steps", []):
            if step.get("key") != stage_key:
                continue
            step["status"] = status
            step["detail"] = _format_stage_detail(detail, metadata)
            step["updated_at"] = payload["updated_at"]
            step["metadata"] = dict(metadata or {})
            break
        return deepcopy(payload)


def complete_product_upload_job(
    job_id: str,
    *,
    message: str,
    indexed_documents: list[dict[str, Any]],
    document_library: dict[str, Any],
    index_status: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    with _JOB_LOCK:
        payload = _JOB_STORE.get(job_id)
        if payload is None:
            return None
        payload["status"] = "completed"
        payload["message"] = message
        payload["indexed_documents"] = list(indexed_documents)
        payload["document_library"] = dict(document_library)
        payload["index_status"] = dict(index_status or {})
        payload["updated_at"] = _now_iso()
        for step in payload.get("steps", []):
            if step.get("status") == "pending":
                step["status"] = "completed"
                step["updated_at"] = payload["updated_at"]
        return deepcopy(payload)


def fail_product_upload_job(job_id: str, *, error_message: str, stage_key: str | None = None) -> dict[str, Any] | None:
    with _JOB_LOCK:
        payload = _JOB_STORE.get(job_id)
        if payload is None:
            return None
        payload["status"] = "error"
        payload["error"] = error_message
        payload["message"] = error_message
        payload["updated_at"] = _now_iso()
        target_stage = stage_key or payload.get("current_stage")
        if target_stage:
            for step in payload.get("steps", []):
                if step.get("key") != target_stage:
                    continue
                step["status"] = "error"
                step["detail"] = error_message
                step["updated_at"] = payload["updated_at"]
                break
        return deepcopy(payload)
