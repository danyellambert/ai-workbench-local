from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.product.models import ProductWorkflowRequest, ProductWorkflowResult
from src.product.service import list_product_documents
from src.storage.product_workflow_history import load_product_workflow_history, summarize_product_workflow_history
from src.storage.runtime_execution_log import load_runtime_execution_log
from src.storage.runtime_paths import get_artifact_root, get_product_workflow_history_path, get_runtime_execution_log_path

if TYPE_CHECKING:
    from src.app.product_bootstrap import ProductBootstrap


EXPORT_KIND_TO_WORKFLOW_LABEL = {
    "document_review_deck": "Document Review",
    "policy_contract_comparison_deck": "Policy Comparison",
    "action_plan_deck": "Action Plan",
    "candidate_review_deck": "Candidate Review",
    "benchmark_eval_executive_deck": "Benchmark / Eval",
    "evidence_pack_deck": "Evidence Pack",
}


def _format_duration_label(duration_s: float | int | None) -> str:
    if not isinstance(duration_s, (int, float)):
        return "—"
    total_seconds = max(float(duration_s), 0.0)
    if total_seconds < 60:
        return f"{total_seconds:.1f}s"
    minutes = int(total_seconds // 60)
    seconds = int(round(total_seconds % 60))
    return f"{minutes}m {seconds:02d}s"


def _format_size_label(size_bytes: int | None) -> str:
    if not isinstance(size_bytes, int) or size_bytes <= 0:
        return "—"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{round(size_bytes / 1024, 1)} KB"
    return f"{round(size_bytes / (1024 * 1024), 1)} MB"


def _normalize_status_for_artifact(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized == "completed":
        return "ready"
    if normalized in {"failed", "artifact_download_failed"}:
        return "error"
    return normalized or "pending"


def _normalize_timestamp(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _parse_export_created_at(export_id: str | None, metadata_path: Path) -> str:
    normalized = str(export_id or "").strip()
    match = re.match(r"deckexp_(\d{8})_(\d{6})_", normalized)
    if match:
        raw = f"{match.group(1)}{match.group(2)}"
        try:
            return datetime.strptime(raw, "%Y%m%d%H%M%S").isoformat()
        except ValueError:
            pass
    return datetime.fromtimestamp(metadata_path.stat().st_mtime).isoformat()


def _workflow_label_from_runtime_entry(entry: dict[str, object]) -> tuple[str, str] | None:
    task_type = str(entry.get("task_type") or "").strip().lower()
    tool_name = str(entry.get("agent_tool") or "").strip().lower()
    if task_type == "cv_analysis":
        return "candidate_review", "Candidate Review"
    if task_type != "document_agent":
        return None
    if tool_name == "compare_documents":
        return "policy_contract_comparison", "Policy Comparison"
    if tool_name == "extract_operational_tasks":
        return "action_plan_evidence_review", "Action Plan"
    return "document_review", "Document Review"


def _build_document_lookup(bootstrap: ProductBootstrap) -> dict[str, str]:
    return {item.document_id: item.name for item in list_product_documents(bootstrap.rag_settings)}


def build_product_workflow_history_entry(
    *,
    request: ProductWorkflowRequest,
    document_lookup: dict[str, str],
    result: ProductWorkflowResult | None,
    duration_s: float,
    error_message: str | None = None,
) -> dict[str, object]:
    workflow_label = result.workflow_label if result is not None else request.workflow_id.replace("_", " ").title()
    status = result.status if result is not None else "error"
    artifacts = result.artifacts if result is not None else []
    return {
        "id": f"{request.workflow_id}-{int(datetime.now().timestamp() * 1000)}",
        "timestamp": datetime.now().isoformat(),
        "workflow_id": request.workflow_id,
        "workflow_label": workflow_label,
        "status": status,
        "provider": request.provider,
        "model": request.model,
        "duration_s": round(float(duration_s), 4),
        "duration_label": _format_duration_label(duration_s),
        "document_ids": list(request.document_ids),
        "documents": [document_lookup.get(document_id, document_id) for document_id in request.document_ids],
        "document_count": len(request.document_ids),
        "findings_count": len(result.highlights or []) if result is not None else 0,
        "warning_count": len(result.warnings or []) if result is not None else 0,
        "recommendation": result.recommendation if result is not None else None,
        "artifacts": [artifact.download_name or artifact.label for artifact in artifacts if artifact.available],
        "error_message": error_message,
    }


def _build_run_entries_from_runtime_log(
    entries: list[dict[str, object]],
    *,
    document_lookup: dict[str, str],
) -> list[dict[str, object]]:
    runs: list[dict[str, object]] = []
    for index, entry in enumerate(entries):
        workflow = _workflow_label_from_runtime_entry(entry)
        if workflow is None:
            continue
        workflow_id, workflow_label = workflow
        success = bool(entry.get("success"))
        error_message = str(entry.get("error_message") or "").strip() or None
        needs_review = bool(entry.get("needs_review"))
        status = "error" if error_message or not success else ("warning" if needs_review else "completed")
        source_document_ids = [str(item) for item in (entry.get("source_document_ids") or []) if str(item).strip()]
        runs.append(
            {
                "id": f"runtime-{index}",
                "timestamp": _normalize_timestamp(entry.get("timestamp")),
                "workflow_id": workflow_id,
                "workflow_label": workflow_label,
                "status": status,
                "provider": entry.get("provider"),
                "model": entry.get("model"),
                "duration_s": entry.get("latency_s"),
                "duration_label": _format_duration_label(entry.get("latency_s") if isinstance(entry.get("latency_s"), (int, float)) else None),
                "document_ids": source_document_ids,
                "documents": [document_lookup.get(document_id, document_id[:12]) for document_id in source_document_ids],
                "document_count": int(entry.get("selected_documents") or len(source_document_ids) or 0),
                "findings_count": None,
                "warning_count": 1 if status == "warning" else 0,
                "recommendation": None,
                "artifacts": [],
                "error_message": error_message,
            }
        )
    return runs


def build_product_run_history_payload(bootstrap: ProductBootstrap, *, recent_limit: int = 25) -> dict[str, object]:
    history_path = get_product_workflow_history_path(bootstrap.workspace_root)
    document_lookup = _build_document_lookup(bootstrap)
    history_entries = load_product_workflow_history(history_path)
    source = "product_workflow_history"
    if history_entries:
        entries = history_entries
    else:
        runtime_entries = load_runtime_execution_log(get_runtime_execution_log_path(bootstrap.workspace_root))
        entries = _build_run_entries_from_runtime_log(runtime_entries, document_lookup=document_lookup)
        source = "runtime_execution_fallback"
    summary = summarize_product_workflow_history(entries)
    return {
        "ok": True,
        "source": source,
        "history_path": str(history_path),
        "summary": summary,
        "runs": list(reversed(entries[-recent_limit:])),
    }


def build_product_artifact_payload(bootstrap: ProductBootstrap, *, recent_limit: int = 25) -> dict[str, object]:
    artifact_root = get_artifact_root(bootstrap.workspace_root) / "presentation_exports"
    entries: list[dict[str, object]] = []
    if artifact_root.exists() and artifact_root.is_dir():
        metadata_paths = sorted(artifact_root.glob("**/metadata.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        for metadata_path in metadata_paths:
            try:
                payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            export_id = str(payload.get("export_id") or metadata_path.parent.name)
            pptx_path_raw = str(payload.get("local_pptx_path") or "").strip()
            pptx_path = Path(pptx_path_raw) if pptx_path_raw else None
            size_bytes = None
            if pptx_path is not None and pptx_path.exists() and pptx_path.is_file():
                size_bytes = pptx_path.stat().st_size
            export_kind = str(payload.get("export_kind") or payload.get("requested_export_kind") or "").strip()
            export_kind_label = str(payload.get("export_kind_label") or export_kind or export_id).strip()
            entries.append(
                {
                    "id": export_id,
                    "name": export_kind_label,
                    "type": "pptx",
                    "workflow_label": EXPORT_KIND_TO_WORKFLOW_LABEL.get(export_kind, export_kind_label.replace(" Deck", "")),
                    "created_at": _parse_export_created_at(export_id, metadata_path),
                    "size": _format_size_label(size_bytes),
                    "status": _normalize_status_for_artifact(str(payload.get("status") or "")),
                    "export_kind": export_kind,
                    "local_artifact_dir": str(payload.get("local_artifact_dir") or metadata_path.parent),
                    "local_pptx_path": str(pptx_path) if pptx_path is not None else None,
                }
            )

    completed_count = sum(1 for entry in entries if str(entry.get("status") or "") == "ready")
    error_count = sum(1 for entry in entries if str(entry.get("status") or "") == "error")
    return {
        "ok": True,
        "artifact_root": str(artifact_root),
        "summary": {
            "total_artifacts": len(entries),
            "completed_artifacts": completed_count,
            "error_artifacts": error_count,
        },
        "artifacts": entries[:recent_limit],
    }


def build_product_command_center_payload(bootstrap: ProductBootstrap, *, recent_limit: int = 5) -> dict[str, object]:
    documents = list_product_documents(bootstrap.rag_settings)
    run_history = build_product_run_history_payload(bootstrap, recent_limit=recent_limit)
    artifact_payload = build_product_artifact_payload(bootstrap, recent_limit=recent_limit)
    return {
        "ok": True,
        "summary": {
            "indexed_documents": len(documents),
            "total_chunks": sum(int(item.chunk_count or 0) for item in documents),
            "completed_runs": int((run_history.get("summary") or {}).get("completed_runs") or 0),
            "artifacts_generated": int((artifact_payload.get("summary") or {}).get("completed_artifacts") or 0),
            "total_chars": sum(int(item.char_count or 0) for item in documents),
            "workflow_count": len(bootstrap.workflow_catalog),
        },
        "recent_runs": run_history.get("runs") or [],
        "recent_artifacts": artifact_payload.get("artifacts") or [],
    }


def build_product_document_library_payload(bootstrap: ProductBootstrap) -> dict[str, object]:
    documents = list_product_documents(bootstrap.rag_settings)
    status_counts: dict[str, int] = {
        "indexed": 0,
        "indexing": 0,
        "warning": 0,
        "error": 0,
        "pending": 0,
    }
    for item in documents:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1

    indexed_documents = sum(1 for item in documents if item.indexed_at)
    return {
        "ok": True,
        "summary": {
            "total_documents": len(documents),
            "indexed_documents": indexed_documents,
            "warning_documents": int(status_counts.get("warning") or 0),
            "error_documents": int(status_counts.get("error") or 0),
            "pending_documents": int(status_counts.get("pending") or 0),
            "indexing_documents": int(status_counts.get("indexing") or 0),
            "total_chunks": sum(int(item.chunk_count or 0) for item in documents),
            "total_chars": sum(int(item.char_count or 0) for item in documents),
        },
        "documents": [item.model_dump(mode="json") for item in documents],
    }