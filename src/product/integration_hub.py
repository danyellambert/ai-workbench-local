from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import get_evidenceops_external_settings
from src.product.models import ProductWorkflowResult
from src.services.evidenceops_external_targets import (
    build_external_targets_status,
    build_phase95_corpus_mapping,
    create_notion_page_from_product_result,
    list_nextcloud_repository_documents,
    list_notion_database_entries,
    sync_phase95_corpus_to_nextcloud,
)
from src.storage.product_workflow_history import (
    get_product_workflow_history_entry,
    load_product_workflow_history,
    update_product_workflow_history_entry,
)
from src.storage.runtime_paths import get_product_workflow_history_path

WORKFLOW_DELIVERY_MAP: dict[str, dict[str, str]] = {
    "action_plan_evidence_review": {
        "workflow_label": "Action Plan",
        "source_target": "nextcloud",
        "execution_target": "trello",
        "handoff_target": "notion",
        "narrative": "Ground evidence from Nextcloud, convert findings into Trello execution cards and publish an executive handoff to Notion.",
    },
    "candidate_review": {
        "workflow_label": "Candidate Review",
        "source_target": "nextcloud",
        "execution_target": "trello",
        "handoff_target": "notion",
        "narrative": "Ingest the candidate packet from the corpus, create interview / follow-up actions in Trello and publish the hiring brief to Notion.",
    },
    "policy_contract_comparison": {
        "workflow_label": "Comparison",
        "source_target": "nextcloud",
        "execution_target": "trello",
        "handoff_target": "notion",
        "narrative": "Compare controlled documents, turn deltas into tracked actions and publish the executive comparison register.",
    },
    "document_review": {
        "workflow_label": "Document Review",
        "source_target": "nextcloud",
        "execution_target": "trello",
        "handoff_target": "notion",
        "narrative": "Review grounded evidence, track remediation in Trello and publish the review summary to Notion.",
    },
}

TARGET_LABELS = {
    "nextcloud": "Nextcloud",
    "trello": "Trello",
    "notion": "Notion",
}

TARGET_ROLES = {
    "nextcloud": "Evidence source",
    "trello": "Operational execution",
    "notion": "Executive handoff",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: object) -> datetime | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    try:
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _first_non_empty(*values: object) -> str | None:
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return None


def _normalize_delivery_status(raw_status: object) -> str:
    normalized = str(raw_status or "").strip().lower()
    if normalized in {"success", "ok", "completed", "ready"}:
        return "completed"
    if normalized in {"planned", "warning", "degraded", "partial"}:
        return "warning"
    if normalized in {"error", "failed"}:
        return "error"
    return normalized or "completed"


def _normalize_delivery_output(target: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized_target = str(target or "").strip().lower() or "delivery"
    message = _first_non_empty(payload.get("message"), payload.get("detail"), payload.get("summary"))
    url = _first_non_empty(
        payload.get("page_url"),
        payload.get("board_url"),
        payload.get("card_url"),
        (payload.get("created_card_urls") or [None])[0] if isinstance(payload.get("created_card_urls"), list) else None,
    )
    metrics: dict[str, Any] = {}
    for key in [
        "created_card_count",
        "planned_card_count",
        "entry_count",
        "upload_count",
        "uploaded_file_count",
        "children_count",
        "remote_directory_count",
        "remote_document_count",
    ]:
        if key in payload:
            metrics[key] = payload.get(key)
    for key in ["board_name", "target_board_id", "database_id", "page_title", "remote_root_path"]:
        value = _first_non_empty(payload.get(key))
        if value:
            metrics[key] = value
    return {
        "target": normalized_target,
        "label": TARGET_LABELS.get(normalized_target, normalized_target.replace("_", " ").title()),
        "status": _normalize_delivery_status(payload.get("status")),
        "dry_run": bool(payload.get("dry_run")),
        "timestamp": _first_non_empty(payload.get("timestamp"), _now_iso()),
        "message": message,
        "summary": message,
        "url": url,
        "metrics": metrics,
    }


def record_product_delivery_output(
    workspace_root: str | Path,
    *,
    run_id: str | None,
    target: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    history_path = get_product_workflow_history_path(Path(workspace_root))
    current_entry = get_product_workflow_history_entry(history_path, normalized_run_id)
    if current_entry is None:
        return None
    delivery_outputs = dict(current_entry.get("delivery_outputs") or {}) if isinstance(current_entry.get("delivery_outputs"), dict) else {}
    delivery_outputs[str(target or "delivery").strip().lower() or "delivery"] = _normalize_delivery_output(target, payload)
    return update_product_workflow_history_entry(
        history_path,
        normalized_run_id,
        {
            "delivery_outputs": delivery_outputs,
            "last_delivery_at": delivery_outputs[str(target or "delivery").strip().lower() or "delivery"].get("timestamp"),
        },
    )


def _build_recent_delivery_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        outputs = entry.get("delivery_outputs") if isinstance(entry.get("delivery_outputs"), dict) else {}
        for raw_target, raw_payload in outputs.items():
            if not isinstance(raw_payload, dict):
                continue
            payload = _normalize_delivery_output(str(raw_target), raw_payload)
            rows.append(
                {
                    "run_id": str(entry.get("id") or "").strip() or None,
                    "workflow_id": str(entry.get("workflow_id") or "").strip() or None,
                    "workflow_label": str(entry.get("workflow_label") or entry.get("workflow_id") or "").strip() or None,
                    "target": str(payload.get("target") or raw_target),
                    "target_label": str(payload.get("label") or TARGET_LABELS.get(str(raw_target), raw_target)),
                    "status": str(payload.get("status") or "completed"),
                    "summary": str(payload.get("summary") or payload.get("message") or "").strip() or None,
                    "timestamp": payload.get("timestamp"),
                    "url": payload.get("url"),
                    "dry_run": bool(payload.get("dry_run")),
                    "delivery": payload,
                }
            )
    rows.sort(key=lambda item: _parse_timestamp(item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return rows


def build_product_integration_hub_payload(workspace_root: str | Path) -> dict[str, Any]:
    settings = get_evidenceops_external_settings()
    mapping = build_phase95_corpus_mapping(settings=settings)
    external_status = build_external_targets_status(settings)
    history_entries = load_product_workflow_history(get_product_workflow_history_path(Path(workspace_root)))
    recent_deliveries = _build_recent_delivery_rows(history_entries)

    recent_by_target: dict[str, dict[str, Any]] = {}
    for row in recent_deliveries:
        target = str(row.get("target") or "").strip().lower()
        if target and target not in recent_by_target:
            recent_by_target[target] = row

    nextcloud_files = sum(int(item.get("file_count") or 0) for item in mapping.nextcloud_directories)
    trello_storylines = len(mapping.trello_storylines)
    notion_registers = len(mapping.notion_registers)

    targets = []
    nextcloud_status = external_status.get("nextcloud") if isinstance(external_status.get("nextcloud"), dict) else {}
    trello_status = external_status.get("trello") if isinstance(external_status.get("trello"), dict) else {}
    notion_status = external_status.get("notion") if isinstance(external_status.get("notion"), dict) else {}

    for key, status_payload, metrics, detail in [
        (
            "nextcloud",
            nextcloud_status,
            [
                {"label": "Directories", "value": len(mapping.nextcloud_directories)},
                {"label": "Files", "value": nextcloud_files},
                {"label": "Remote root", "value": str(nextcloud_status.get("root_path") or settings.nextcloud.root_path)},
            ],
            str(nextcloud_status.get("root_path") or settings.nextcloud.root_path),
        ),
        (
            "trello",
            trello_status,
            [
                {"label": "Storylines", "value": trello_storylines},
                {"label": "Board", "value": str(trello_status.get("board_id") or "Not configured")},
                {"label": "Lists mapped", "value": 4},
            ],
            str(trello_status.get("board_id") or "Board id missing"),
        ),
        (
            "notion",
            notion_status,
            [
                {"label": "Registers", "value": notion_registers},
                {"label": "Database", "value": str(notion_status.get("database_id") or "Not configured")},
                {"label": "Workflow handoffs", "value": len(WORKFLOW_DELIVERY_MAP)},
            ],
            str(notion_status.get("database_id") or "Database id missing"),
        ),
    ]:
        configured = bool(status_payload.get("configured"))
        last_delivery = recent_by_target.get(key)
        targets.append(
            {
                "key": key,
                "label": TARGET_LABELS[key],
                "role": TARGET_ROLES[key],
                "configured": configured,
                "status": "ready" if configured else "degraded",
                "detail": detail,
                "metrics": metrics,
                "last_delivery_at": last_delivery.get("timestamp") if last_delivery else None,
                "last_delivery_summary": last_delivery.get("summary") if last_delivery else None,
            }
        )

    workflow_targets = []
    for workflow_id, config in WORKFLOW_DELIVERY_MAP.items():
        latest_delivery = next((row.get("delivery") for row in recent_deliveries if row.get("workflow_id") == workflow_id), None)
        workflow_targets.append(
            {
                "workflow_id": workflow_id,
                "workflow_label": config["workflow_label"],
                "narrative": config["narrative"],
                "source_target": config["source_target"],
                "execution_target": config["execution_target"],
                "handoff_target": config["handoff_target"],
                "latest_delivery": latest_delivery,
            }
        )

    ready_targets = sum(1 for item in targets if str(item.get("status") or "") == "ready")
    updated_at = recent_deliveries[0].get("timestamp") if recent_deliveries else _now_iso()
    return {
        "ok": True,
        "status": "live" if ready_targets else "degraded",
        "updated_at": updated_at,
        "summary": {
            "ready_targets": ready_targets,
            "total_targets": len(targets),
            "recent_deliveries": len(recent_deliveries),
            "corpus_files": nextcloud_files,
        },
        "cycle": [
            {"step": "1", "target": "Nextcloud", "description": "Ground the workflow in synced evidence, policies, contracts and candidate packets."},
            {"step": "2", "target": "Trello", "description": "Turn findings into operational execution cards with owners, due dates and review lists."},
            {"step": "3", "target": "Notion", "description": "Publish the executive handoff, register or hiring brief for review and sharing."},
        ],
        "targets": targets,
        "workflow_targets": workflow_targets,
        "recent_deliveries": recent_deliveries[:12],
    }


def build_product_notion_entries_payload(*, limit: int = 10) -> dict[str, Any]:
    result = list_notion_database_entries(limit=max(1, min(int(limit), 25)))
    result.setdefault("ok", True)
    result.setdefault("timestamp", _now_iso())
    return result


def build_product_nextcloud_documents_payload(*, limit: int = 10) -> dict[str, Any]:
    documents = list_nextcloud_repository_documents(limit=max(1, min(int(limit), 25)))
    normalized_documents = [
        {
            "document_id": item.get("document_id"),
            "title": item.get("title"),
            "relative_path": item.get("relative_path"),
            "category": item.get("category"),
            "size_bytes": item.get("size_bytes"),
            "modified_at": item.get("modified_at"),
            "webdav_url": item.get("webdav_url") or item.get("path"),
        }
        for item in documents
        if isinstance(item, dict)
    ]
    return {
        "ok": True,
        "status": "success",
        "timestamp": _now_iso(),
        "entry_count": len(normalized_documents),
        "remote_root_path": get_evidenceops_external_settings().nextcloud.root_path,
        "documents": normalized_documents,
    }


def build_product_nextcloud_sync_payload(*, dry_run: bool = False) -> dict[str, Any]:
    result = sync_phase95_corpus_to_nextcloud(dry_run=bool(dry_run))
    result.setdefault("ok", True)
    result.setdefault("timestamp", _now_iso())
    return result


def publish_product_workflow_to_notion(
    result: ProductWorkflowResult,
    *,
    dry_run: bool = False,
    template_id: str | None = None,
    preview_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = create_notion_page_from_product_result(
        result,
        dry_run=bool(dry_run),
        template_id=template_id,
        preview_payload=preview_payload,
    )
    payload.setdefault("ok", True)
    payload.setdefault("timestamp", _now_iso())
    return payload
