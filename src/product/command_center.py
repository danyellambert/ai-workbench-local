from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.product.models import ProductArtifact, ProductWorkflowRequest, ProductWorkflowResult
from src.product.presenters import build_document_review_view, build_product_result_sections
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


ARTIFACT_ASSET_LABELS: dict[str, tuple[str, str]] = {
    "local_pptx_path": ("pptx", "Presentation deck (.pptx)"),
    "local_contract_path": ("contract_json", "Executive deck contract (.json)"),
    "local_payload_path": ("payload_json", "PPT payload (.json)"),
    "local_review_path": ("review_json", "Layout review (.json)"),
    "local_preview_manifest_path": ("preview_manifest_json", "Preview manifest (.json)"),
    "local_thumbnail_sheet_path": ("thumbnail_sheet", "Thumbnail sheet (.png)"),
    "local_render_request_path": ("render_request_json", "Render request (.json)"),
    "local_render_response_path": ("render_response_json", "Render response (.json)"),
}


def _format_duration_label(duration_s: float | int | None) -> str:
    if not isinstance(duration_s, (int, float)):
        return "-"
    total_seconds = max(float(duration_s), 0.0)
    if total_seconds < 60:
        return f"{total_seconds:.1f}s"
    minutes = int(total_seconds // 60)
    seconds = int(round(total_seconds % 60))
    return f"{minutes}m {seconds:02d}s"


def _format_size_label(size_bytes: int | None) -> str:
    if not isinstance(size_bytes, int) or size_bytes <= 0:
        return "-"
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


def _load_json_file(path: Path | None) -> dict[str, Any] | list[Any] | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, (dict, list)) else None


def _infer_baseline_root_from_metadata_path(metadata_path: Path) -> Path:
    resolved = metadata_path.resolve(strict=False)
    parts = list(resolved.parts)

    for index, part in enumerate(parts):
        if part == "artifacts" and index + 1 < len(parts) and parts[index + 1] == "presentation_exports":
            return Path(*parts[:index]).resolve(strict=False)

    if len(resolved.parents) >= 4:
        return resolved.parents[3].resolve(strict=False)

    return resolved.parent.resolve(strict=False)


def _resolve_baseline_uri_path(raw_uri: str, metadata_path: Path) -> Path | None:
    if not raw_uri.startswith("baseline://"):
        return None

    logical = raw_uri.removeprefix("baseline://").strip("/")
    if not logical:
        return None

    namespace, _, suffix = logical.partition("/")
    baseline_root = _infer_baseline_root_from_metadata_path(metadata_path)

    namespace_roots = {
        "workspace": baseline_root,
        "artifacts": baseline_root / "artifacts",
        "runtime": baseline_root / ".runtime",
        "outputs": baseline_root / "outputs",
        "data": baseline_root / "data",
        "external_files": baseline_root / "external_files",
    }

    root = namespace_roots.get(namespace)
    if root is None:
        return None

    candidate = (root / suffix).resolve(strict=False) if suffix else root.resolve(strict=False)
    return candidate if candidate.exists() else None


def _resolve_artifact_sidecar_path(value: object, metadata_path: Path) -> Path | None:
    raw_value = str(value or "").strip()
    if not raw_value:
        return None

    artifact_dir = metadata_path.parent.resolve(strict=False)

    def sibling_candidate(name: str) -> Path | None:
        clean_name = name.strip().split("/")[-1]
        if not clean_name:
            return None

        candidates = [artifact_dir / clean_name]

        # Legacy Oracle-like baseline exports stored sidecars next to metadata,
        # while metadata may point at baseline://external_files/<hash>_<filename>.
        if "_" in clean_name:
            candidates.append(artifact_dir / clean_name.split("_", 1)[1])

        # Preview manifests historically used both hyphen and underscore names.
        candidates.extend(
            [
                artifact_dir / clean_name.replace("_", "-"),
                artifact_dir / clean_name.replace("-", "_"),
            ]
        )

        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve(strict=False)
        return None

    if raw_value.startswith("baseline://external_files/"):
        resolved = sibling_candidate(raw_value.removeprefix("baseline://external_files/"))
        return resolved if resolved is not None else None

    if raw_value.startswith("baseline://artifacts/"):
        relative = raw_value.removeprefix("baseline://artifacts/").strip("/")
        if relative:
            parts = relative.split("/")
            if parts and parts[-1]:
                resolved = sibling_candidate(parts[-1])
                if resolved is not None:
                    return resolved
        return artifact_dir

    candidate = Path(raw_value)
    if candidate.is_absolute():
        if candidate.exists():
            return candidate.resolve(strict=False)

        # If an old absolute path points at /app/baseline/artifacts or /app/artifacts,
        # keep the current metadata directory as the source of truth.
        resolved = sibling_candidate(candidate.name)
        return resolved if resolved is not None else candidate.resolve(strict=False)

    resolved = (metadata_path.parent / candidate).resolve(strict=False)
    if resolved.exists():
        return resolved

    sibling = sibling_candidate(candidate.name)
    return sibling if sibling is not None else resolved


def _artifact_asset_entries(metadata_payload: dict[str, Any], metadata_path: Path) -> list[dict[str, object]]:
    assets: list[dict[str, object]] = []
    for field_name, (asset_type, label) in ARTIFACT_ASSET_LABELS.items():
        resolved_path = _resolve_artifact_sidecar_path(metadata_payload.get(field_name), metadata_path)
        assets.append(
            {
                "artifact_type": asset_type,
                "label": label,
                "path": str(resolved_path) if resolved_path is not None else None,
                "download_name": resolved_path.name if resolved_path is not None else None,
                "available": bool(resolved_path and resolved_path.exists() and resolved_path.is_file()),
            }
        )
    metadata_asset = metadata_path.resolve(strict=False)
    assets.append(
        {
            "artifact_type": "metadata_json",
            "label": "Metadata (.json)",
            "path": str(metadata_asset),
            "download_name": metadata_asset.name,
            "available": metadata_asset.exists() and metadata_asset.is_file(),
        }
    )
    return assets


def _normalize_artifact_entry_from_metadata(metadata_path: Path) -> dict[str, object] | None:
    metadata_payload = _load_json_file(metadata_path)
    if not isinstance(metadata_payload, dict):
        return None

    export_id = str(metadata_payload.get("export_id") or metadata_path.parent.name)
    export_kind = str(metadata_payload.get("export_kind") or metadata_payload.get("requested_export_kind") or "").strip()
    export_kind_label = str(metadata_payload.get("export_kind_label") or export_kind or export_id).strip()
    created_at = _parse_export_created_at(export_id, metadata_path)

    normalized_dir = metadata_path.parent.resolve(strict=False)
    normalized_pptx = _resolve_artifact_sidecar_path(metadata_payload.get("local_pptx_path"), metadata_path)
    normalized_review = _resolve_artifact_sidecar_path(metadata_payload.get("local_review_path"), metadata_path)
    normalized_preview_manifest = _resolve_artifact_sidecar_path(metadata_payload.get("local_preview_manifest_path"), metadata_path)
    normalized_thumbnail_sheet = _resolve_artifact_sidecar_path(metadata_payload.get("local_thumbnail_sheet_path"), metadata_path)
    normalized_contract = _resolve_artifact_sidecar_path(metadata_payload.get("local_contract_path"), metadata_path)
    normalized_payload = _resolve_artifact_sidecar_path(metadata_payload.get("local_payload_path"), metadata_path)
    normalized_render_request = _resolve_artifact_sidecar_path(metadata_payload.get("local_render_request_path"), metadata_path)
    normalized_render_response = _resolve_artifact_sidecar_path(metadata_payload.get("local_render_response_path"), metadata_path)

    review_payload = _load_json_file(normalized_review)
    preview_manifest_payload = _load_json_file(normalized_preview_manifest)
    contract_payload = _load_json_file(normalized_contract)
    payload_payload = _load_json_file(normalized_payload)

    pptx_size_bytes = int(normalized_pptx.stat().st_size) if normalized_pptx and normalized_pptx.exists() and normalized_pptx.is_file() else None
    warnings = [str(item).strip() for item in (metadata_payload.get("warnings") or []) if str(item).strip()]
    error_message = str(metadata_payload.get("error_message") or "").strip() or None
    review_status = str(review_payload.get("status") or "").strip() if isinstance(review_payload, dict) else None
    issue_count = int(review_payload.get("issue_count") or 0) if isinstance(review_payload, dict) else 0
    warning_count = int(review_payload.get("warning_count") or 0) if isinstance(review_payload, dict) else 0
    slide_count = int(review_payload.get("slide_count") or 0) if isinstance(review_payload, dict) else 0
    average_score = float(review_payload.get("average_score") or 0.0) if isinstance(review_payload, dict) and isinstance(review_payload.get("average_score"), (int, float)) else None
    preview_count = int(preview_manifest_payload.get("preview_count") or 0) if isinstance(preview_manifest_payload, dict) else 0
    presentation_title = None
    if isinstance(contract_payload, dict):
        presentation = contract_payload.get("presentation") if isinstance(contract_payload.get("presentation"), dict) else {}
        presentation_title = str(presentation.get("title") or "").strip() or None
    if presentation_title is None and isinstance(payload_payload, dict):
        presentation = payload_payload.get("presentation") if isinstance(payload_payload.get("presentation"), dict) else {}
        presentation_title = str(presentation.get("title") or "").strip() or None

    assets = _artifact_asset_entries(metadata_payload, metadata_path)
    available_assets = [asset for asset in assets if bool(asset.get("available"))]
    status_reason = error_message or (warnings[0] if warnings else None)

    return {
        "id": export_id,
        "name": export_kind_label,
        "title": presentation_title or export_kind_label,
        "type": "pptx",
        "workflow_label": EXPORT_KIND_TO_WORKFLOW_LABEL.get(export_kind, export_kind_label.replace(" Deck", "")),
        "created_at": created_at,
        "size": _format_size_label(pptx_size_bytes),
        "status": _normalize_status_for_artifact(str(metadata_payload.get("status") or "")),
        "status_reason": status_reason,
        "export_kind": export_kind,
        "local_artifact_dir": str(normalized_dir),
        "local_pptx_path": str(normalized_pptx) if normalized_pptx is not None else None,
        "local_contract_path": str(normalized_contract) if normalized_contract is not None else None,
        "local_payload_path": str(normalized_payload) if normalized_payload is not None else None,
        "local_review_path": str(normalized_review) if normalized_review is not None else None,
        "local_preview_manifest_path": str(normalized_preview_manifest) if normalized_preview_manifest is not None else None,
        "local_thumbnail_sheet_path": str(normalized_thumbnail_sheet) if normalized_thumbnail_sheet is not None else None,
        "local_render_request_path": str(normalized_render_request) if normalized_render_request is not None else None,
        "local_render_response_path": str(normalized_render_response) if normalized_render_response is not None else None,
        "metadata_path": str(metadata_path.resolve(strict=False)),
        "pptx_size_bytes": pptx_size_bytes,
        "slide_count": slide_count or None,
        "preview_count": preview_count or None,
        "review_status": review_status or None,
        "average_score": average_score,
        "issue_count": issue_count,
        "warning_count": warning_count,
        "error_message": error_message,
        "warnings": warnings,
        "available_assets": available_assets,
        "asset_count": len(available_assets),
        "has_preview": bool(preview_count or normalized_thumbnail_sheet),
        "has_review": isinstance(review_payload, dict),
    }


def _build_artifact_entries(
    bootstrap: ProductBootstrap,
    *,
    additional_artifact_roots: list[Path] | None = None,
) -> list[dict[str, object]]:
    global_artifact_root = get_artifact_root(bootstrap.workspace_root) / "presentation_exports"
    artifact_roots: list[Path] = [global_artifact_root]
    for root in additional_artifact_roots or []:
        if root is None:
            continue
        artifact_roots.append(Path(root))

    metadata_paths: list[Path] = []
    seen_paths: set[str] = set()
    for artifact_root in artifact_roots:
        if artifact_root.exists() and artifact_root.is_dir():
            for metadata_path in artifact_root.glob("**/metadata.json"):
                key = str(metadata_path.resolve(strict=False))
                if key not in seen_paths:
                    seen_paths.add(key)
                    metadata_paths.append(metadata_path)

    entries: list[dict[str, object]] = []
    for metadata_path in sorted(metadata_paths, key=lambda item: item.stat().st_mtime, reverse=True):
        entry = _normalize_artifact_entry_from_metadata(metadata_path)
        if entry is not None:
            entries.append(entry)
    return entries


def _coerce_request_payload(entry: dict[str, object]) -> dict[str, object] | None:
    request_payload = entry.get("request_payload")
    if isinstance(request_payload, dict):
        return dict(request_payload)

    workflow_id = str(entry.get("workflow_id") or "").strip()
    document_ids = [str(item).strip() for item in (entry.get("document_ids") or []) if str(item).strip()]
    input_text = str(entry.get("input_text") or "").strip()
    if not workflow_id:
        return None
    payload: dict[str, object] = {
        "workflow_id": workflow_id,
        "document_ids": document_ids,
        "input_text": input_text,
    }
    if entry.get("provider"):
        payload["provider"] = entry.get("provider")
    if entry.get("model"):
        payload["model"] = entry.get("model")
    if entry.get("temperature") is not None:
        payload["temperature"] = entry.get("temperature")
    if entry.get("context_window_mode"):
        payload["context_window_mode"] = entry.get("context_window_mode")
    if entry.get("context_window") is not None:
        payload["context_window"] = entry.get("context_window")
    if entry.get("use_document_context") is not None:
        payload["use_document_context"] = entry.get("use_document_context")
    if entry.get("context_strategy"):
        payload["context_strategy"] = entry.get("context_strategy")
    if entry.get("prompt_profile"):
        payload["prompt_profile"] = entry.get("prompt_profile")
    return payload


def _count_product_workflow_findings(*args, **kwargs) -> int:
    """Count the most useful visible outcome for each product workflow.

    The Run History column is named findings for historical UI reasons, but not every
    workflow emits literal `findings`. Action Plan emits actions/deadlines/risks,
    Candidate Review emits strengths/signals, and Policy Comparison emits comparison
    findings or highlights. This function counts real structured outputs only; it
    does not invent synthetic findings.
    """

    def _as_dict(value):
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            try:
                dumped = value.model_dump(mode="json")
                return dumped if isinstance(dumped, dict) else {}
            except Exception:
                return {}
        return {}

    def _clean_len(value) -> int:
        if isinstance(value, list):
            return len([item for item in value if str(item or "").strip()])
        if isinstance(value, dict):
            return len([key for key, item in value.items() if str(item or "").strip()])
        return 1 if str(value or "").strip() else 0

    def _walk(value, depth: int = 0):
        if depth > 5:
            return
        if isinstance(value, dict):
            yield value
            for nested in value.values():
                yield from _walk(nested, depth + 1)
        elif isinstance(value, list):
            for item in value:
                yield from _walk(item, depth + 1)
        else:
            dumped = _as_dict(value)
            if dumped:
                yield from _walk(dumped, depth + 1)

    result = kwargs.get("result")
    if result is None:
        for arg in args:
            if hasattr(arg, "workflow_id") or hasattr(arg, "structured_result") or isinstance(arg, dict):
                result = arg
                break

    if result is None:
        return 0

    result_dict = _as_dict(result)
    workflow_id = str(
        result_dict.get("workflow_id")
        or getattr(result, "workflow_id", "")
        or kwargs.get("workflow_id", "")
        or ""
    ).lower()

    containers = [result_dict]

    structured_result = result_dict.get("structured_result") or getattr(result, "structured_result", None)
    if structured_result is not None:
        containers.append(_as_dict(structured_result))
        validated_output = getattr(structured_result, "validated_output", None)
        if validated_output is not None:
            containers.append(_as_dict(validated_output))
        parsed_json = getattr(structured_result, "parsed_json", None)
        if parsed_json is not None:
            containers.append(_as_dict(parsed_json))

    for attr in ("validated_output", "parsed_json", "result_view", "response_payload"):
        value = result_dict.get(attr) if isinstance(result_dict, dict) else None
        if value:
            containers.append(_as_dict(value))

    # Include top-level ProductWorkflowResult lists.
    for attr in ("highlights", "warnings", "artifacts"):
        value = result_dict.get(attr)
        if value:
            containers.append({attr: value})

    key_sets = {
        "action_plan_evidence_review": [
            "actions",
            "action_items",
            "recommended_actions",
            "checklist_preview",
            "deadlines",
            "important_dates",
            "risks",
            "blockers",
            "evidence_gaps",
            "missing_information",
        ],
        "policy_contract_comparison": [
            "comparison_findings",
            "findings",
            "differences",
            "key_differences",
            "recommendations",
            "key_points",
            "highlights",
            "risks",
            "gaps",
        ],
        "candidate_review": [
            "strengths",
            "seniority_signals",
            "skills",
            "concerns",
            "risks",
            "key_points",
            "highlights",
            "recommendations",
        ],
        "document_review": [
            "findings",
            "risks",
            "gaps",
            "missing_information",
            "actions",
            "action_items",
            "key_points",
            "highlights",
        ],
    }

    selected_keys = key_sets.get(workflow_id)
    if not selected_keys:
        selected_keys = [
            "findings",
            "actions",
            "action_items",
            "recommendations",
            "key_points",
            "highlights",
            "risks",
            "gaps",
        ]

    counts: list[int] = []

    for container in containers:
        for obj in _walk(container):
            for key in selected_keys:
                if key in obj:
                    counts.append(_clean_len(obj.get(key)))

            structured_response = obj.get("structured_response")
            if isinstance(structured_response, dict):
                for key in selected_keys:
                    if key in structured_response:
                        counts.append(_clean_len(structured_response.get(key)))

    # Prefer the strongest workflow-specific signal, not a sum that double-counts
    # the same item repeated in payload, structured_response and highlights.
    return max(counts or [0])


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
    response_payload = result.model_dump(mode="json") if result is not None else None
    result_sections = build_product_result_sections(result) if result is not None else None
    artifact_items = [artifact.model_dump(mode="json") for artifact in artifacts if artifact.available]
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
        "findings_count": _count_product_workflow_findings(result),
        "warning_count": len(result.warnings or []) if result is not None else 0,
        "recommendation": result.recommendation if result is not None else None,
        "artifacts": [artifact.download_name or artifact.label for artifact in artifacts if artifact.available],
        "artifact_items": artifact_items,
        "request_payload": request.model_dump(mode="json"),
        "response_payload": response_payload,
        "result_sections": result_sections,
        "deck_export_kind": result.deck_export_kind if result is not None else None,
        "error_message": error_message,
    }


def _normalize_artifact_items(raw_value: object) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    if isinstance(raw_value, list):
        for item in raw_value:
            if isinstance(item, ProductArtifact):
                items.append(item.model_dump(mode="json"))
            elif isinstance(item, dict):
                items.append(dict(item))
    return items


def _normalize_history_entry(
    entry: dict[str, object],
    *,
    document_lookup: dict[str, str],
    source: str,
) -> dict[str, object]:
    request_payload = _coerce_request_payload(entry)
    response_payload = entry.get("response_payload") if isinstance(entry.get("response_payload"), dict) else None
    result_sections = entry.get("result_sections") if isinstance(entry.get("result_sections"), dict) else None
    if result_sections is None and isinstance(response_payload, dict):
        try:
            result_sections = build_product_result_sections(ProductWorkflowResult.model_validate(response_payload))
        except Exception:
            result_sections = None

    artifact_items = _normalize_artifact_items(entry.get("artifact_items"))
    if not artifact_items and isinstance(response_payload, dict):
        artifact_items = _normalize_artifact_items(response_payload.get("artifacts"))

    document_ids = [str(item).strip() for item in (entry.get("document_ids") or []) if str(item).strip()]
    if not document_ids and isinstance(request_payload, dict):
        document_ids = [str(item).strip() for item in (request_payload.get("document_ids") or []) if str(item).strip()]
    documents = [str(item).strip() for item in (entry.get("documents") or []) if str(item).strip()]
    if not documents and document_ids:
        documents = [document_lookup.get(document_id, document_id) for document_id in document_ids]

    artifact_labels = [str(item).strip() for item in (entry.get("artifacts") or []) if str(item).strip()]
    if not artifact_labels and artifact_items:
        artifact_labels = [
            str(item.get("download_name") or item.get("label") or item.get("artifact_type") or "artifact").strip()
            for item in artifact_items
            if str(item.get("download_name") or item.get("label") or item.get("artifact_type") or "").strip()
        ]

    notes: list[str] = []
    if response_payload is None:
        notes.append("Structured response payload was not captured for this historical run.")
    if not artifact_items and artifact_labels:
        notes.append("Artifact labels were recorded, but direct artifact paths are unavailable for this run.")

    input_text = str(entry.get("input_text") or "").strip() if entry.get("input_text") is not None else None
    if (not input_text) and isinstance(request_payload, dict):
        input_text = str(request_payload.get("input_text") or "").strip() or None

    can_rerun = bool(
        str(entry.get("workflow_id") or (request_payload or {}).get("workflow_id") or "").strip()
        and (document_ids or input_text)
    )
    delivery_outputs = entry.get("delivery_outputs") if isinstance(entry.get("delivery_outputs"), dict) else None

    return {
        "id": str(entry.get("id") or "").strip(),
        "timestamp": _normalize_timestamp(entry.get("timestamp")),
        "workflow_id": str(entry.get("workflow_id") or (request_payload or {}).get("workflow_id") or "").strip() or None,
        "workflow_label": str(entry.get("workflow_label") or "").strip() or str(entry.get("workflow_id") or "").replace("_", " ").title(),
        "status": str(entry.get("status") or "pending").strip() or "pending",
        "provider": entry.get("provider") or (request_payload or {}).get("provider"),
        "model": entry.get("model") or (request_payload or {}).get("model"),
        "duration_s": entry.get("duration_s"),
        "duration_label": str(entry.get("duration_label") or _format_duration_label(entry.get("duration_s") if isinstance(entry.get("duration_s"), (int, float)) else None)),
        "document_ids": document_ids,
        "documents": documents,
        "document_count": int(entry.get("document_count") or len(document_ids) or len(documents) or 0),
        "findings_count": (
            _count_product_workflow_findings(ProductWorkflowResult.model_validate(response_payload))
            if isinstance(response_payload, dict)
            else entry.get("findings_count")
        ),
        "warning_count": entry.get("warning_count"),
        "recommendation": entry.get("recommendation"),
        "artifacts": artifact_labels,
        "artifact_items": artifact_items,
        "error_message": entry.get("error_message"),
        "request_payload": request_payload,
        "response_payload": response_payload,
        "result_sections": result_sections,
        "delivery_outputs": delivery_outputs,
        "can_rerun": can_rerun,
        "notes": notes,
        "source": source,
    }



def _compact_run_history_entry(entry: dict[str, object]) -> dict[str, object]:
    """Return the fields needed for the run-history list without heavy payload blobs.

    Full request/response/result/artifact payloads remain available from
    /api/product/run-history/<run_id>.
    """

    keep_keys = [
        "id",
        "timestamp",
        "workflow_id",
        "workflow_label",
        "status",
        "provider",
        "model",
        "duration_s",
        "duration_label",
        "document_ids",
        "documents",
        "document_count",
        "findings_count",
        "warning_count",
        "recommendation",
        "artifacts",
        "error_message",
        "can_rerun",
        "notes",
        "source",
    ]
    return {key: entry.get(key) for key in keep_keys if key in entry}

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
        source_document_ids = [str(item).strip() for item in (entry.get("source_document_ids") or []) if str(item).strip()]
        raw_entry = {
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
            "request_payload": {
                "workflow_id": workflow_id,
                "document_ids": source_document_ids,
                "provider": entry.get("provider"),
                "model": entry.get("model"),
            },
            "error_message": error_message,
        }
        runs.append(_normalize_history_entry(raw_entry, document_lookup=document_lookup, source="runtime_execution_fallback"))
    return runs


def build_product_rerun_request_payload(entry: dict[str, object]) -> dict[str, object] | None:
    request_payload = _coerce_request_payload(entry)
    if request_payload is None:
        return None
    normalized: dict[str, object] = {
        "workflow_id": str(request_payload.get("workflow_id") or "").strip(),
        "document_ids": [str(item).strip() for item in (request_payload.get("document_ids") or []) if str(item).strip()],
        "input_text": str(request_payload.get("input_text") or "").strip(),
    }
    for key in [
        "provider",
        "model",
        "prompt_profile",
        "temperature",
        "top_p",
        "max_tokens",
        "context_window_mode",
        "context_window",
        "use_document_context",
        "context_strategy",
    ]:
        value = request_payload.get(key)
        if value is not None:
            normalized[key] = value
    if not str(normalized.get("workflow_id") or "").strip():
        return None
    return normalized


def build_product_run_history_payload(bootstrap: ProductBootstrap, *, recent_limit: int = 25, additional_history_paths: list[Path] | None = None, compact: bool = False) -> dict[str, object]:
    history_path = get_product_workflow_history_path(bootstrap.workspace_root)
    document_lookup = _build_document_lookup(bootstrap)
    history_entries = load_product_workflow_history(history_path)
    source = "product_workflow_history"
    if history_entries:
        entries = [
            _normalize_history_entry(entry, document_lookup=document_lookup, source=source)
            for entry in history_entries
        ]
    else:
        runtime_entries = load_runtime_execution_log(get_runtime_execution_log_path(bootstrap.workspace_root))
        entries = _build_run_entries_from_runtime_log(runtime_entries, document_lookup=document_lookup)
        source = "runtime_execution_fallback"
    additional_sources: list[str] = []
    for additional_path in additional_history_paths or []:
        additional_entries = [
            _normalize_history_entry(entry, document_lookup=document_lookup, source="session_overlay_workflow_history")
            for entry in load_product_workflow_history(additional_path)
        ]
        if additional_entries:
            additional_sources.append(str(additional_path))
            entries.extend(additional_entries)

    if additional_sources:
        source = f"{source}+session_overlay"
        entries = sorted(entries, key=lambda entry: str(entry.get("timestamp") or entry.get("created_at") or ""))

    summary = summarize_product_workflow_history(entries)
    recent_runs = list(reversed(entries[-recent_limit:]))
    if compact:
        recent_runs = [_compact_run_history_entry(entry) for entry in recent_runs]

    return {
        "ok": True,
        "source": source,
        "history_path": str(history_path),
        "additional_history_paths": additional_sources,
        "summary": summary,
        "runs": recent_runs,
        "pagination": {
            "limit": recent_limit,
            "returned": len(recent_runs),
            "total": int(summary.get("total_runs") or len(entries)),
            "has_more": len(entries) > recent_limit,
        },
        "compact": compact,
    }


def build_product_run_detail_payload(bootstrap: ProductBootstrap, *, run_id: str, additional_history_paths: list[Path] | None = None) -> dict[str, object] | None:
    history_path = get_product_workflow_history_path(bootstrap.workspace_root)
    document_lookup = _build_document_lookup(bootstrap)
    history_entries = load_product_workflow_history(history_path)
    for entry in history_entries:
        if str(entry.get("id") or "").strip() == str(run_id or "").strip():
            return {
                "ok": True,
                "source": "product_workflow_history",
                "history_path": str(history_path),
                "run": _normalize_history_entry(entry, document_lookup=document_lookup, source="product_workflow_history"),
            }

    for additional_path in additional_history_paths or []:
        for entry in load_product_workflow_history(additional_path):
            if str(entry.get("id") or "").strip() == str(run_id or "").strip():
                return {
                    "ok": True,
                    "source": "session_overlay_workflow_history",
                    "history_path": str(additional_path),
                    "run": _normalize_history_entry(entry, document_lookup=document_lookup, source="session_overlay_workflow_history"),
                }

    runtime_entries = _build_run_entries_from_runtime_log(
        load_runtime_execution_log(get_runtime_execution_log_path(bootstrap.workspace_root)),
        document_lookup=document_lookup,
    )
    for entry in runtime_entries:
        if str(entry.get("id") or "").strip() == str(run_id or "").strip():
            return {
                "ok": True,
                "source": "runtime_execution_fallback",
                "history_path": str(history_path),
                "run": entry,
            }
    return None


def build_product_artifact_payload(
    bootstrap: ProductBootstrap,
    *,
    recent_limit: int = 25,
    additional_artifact_roots: list[Path] | None = None,
) -> dict[str, object]:
    artifact_root = get_artifact_root(bootstrap.workspace_root) / "presentation_exports"
    entries = _build_artifact_entries(bootstrap, additional_artifact_roots=additional_artifact_roots)
    entries = sorted(
        entries,
        key=lambda entry: (
            str(entry.get("status") or "").strip().lower() == "ready",
            str(entry.get("created_at") or ""),
            int(entry.get("asset_count") or 0),
            int(entry.get("preview_count") or 0),
        ),
        reverse=True,
    )
    completed_count = sum(1 for entry in entries if str(entry.get("status") or "") == "ready")
    error_count = sum(1 for entry in entries if str(entry.get("status") or "") == "error")
    artifact_roots = [str(artifact_root)]
    artifact_roots.extend(str(Path(root)) for root in additional_artifact_roots or [])
    return {
        "ok": True,
        "artifact_root": str(artifact_root),
        "artifact_roots": artifact_roots,
        "summary": {
            "total_artifacts": len(entries),
            "completed_artifacts": completed_count,
            "error_artifacts": error_count,
        },
        "artifacts": entries[:recent_limit],
    }


def build_product_artifact_detail_payload(
    bootstrap: ProductBootstrap,
    *,
    artifact_id: str,
    additional_artifact_roots: list[Path] | None = None,
) -> dict[str, object] | None:
    normalized_id = str(artifact_id or "").strip()
    if not normalized_id:
        return None

    global_artifact_root = get_artifact_root(bootstrap.workspace_root) / "presentation_exports"
    candidate_roots: list[Path] = []
    for root in additional_artifact_roots or []:
        candidate_roots.append(Path(root))
    candidate_roots.append(global_artifact_root)

    artifact_root = global_artifact_root
    metadata_path: Path | None = None
    for candidate_root in candidate_roots:
        candidate_metadata_path = candidate_root / normalized_id / "metadata.json"
        if candidate_metadata_path.exists():
            artifact_root = candidate_root
            metadata_path = candidate_metadata_path
            break

    if metadata_path is None:
        return None

    artifact_entry = _normalize_artifact_entry_from_metadata(metadata_path)
    if artifact_entry is None:
        return None

    metadata_payload = _load_json_file(metadata_path)
    if not isinstance(metadata_payload, dict):
        metadata_payload = {}

    review_payload = _load_json_file(Path(str(artifact_entry.get("local_review_path") or "")))
    preview_manifest_payload = _load_json_file(Path(str(artifact_entry.get("local_preview_manifest_path") or "")))
    contract_payload = _load_json_file(Path(str(artifact_entry.get("local_contract_path") or "")))
    payload_payload = _load_json_file(Path(str(artifact_entry.get("local_payload_path") or "")))

    preview_slides: list[dict[str, object]] = []
    if isinstance(preview_manifest_payload, dict):
        for slide in preview_manifest_payload.get("slides") or []:
            if not isinstance(slide, dict):
                continue
            resolved_path = _resolve_artifact_sidecar_path(slide.get("path"), metadata_path)
            preview_slides.append(
                {
                    "slide_number": slide.get("slide_number"),
                    "filename": slide.get("filename"),
                    "path": str(resolved_path) if resolved_path is not None else None,
                    "available": bool(resolved_path and resolved_path.exists() and resolved_path.is_file()),
                }
            )

    thumbnail_sheet_path = Path(str(artifact_entry.get("local_thumbnail_sheet_path") or "")) if artifact_entry.get("local_thumbnail_sheet_path") else None
    notes: list[str] = []
    if preview_slides and not any(bool(slide.get("available")) for slide in preview_slides):
        notes.append("Preview manifest exists, but the individual slide preview PNGs are not available in this workspace.")
    if thumbnail_sheet_path is not None and thumbnail_sheet_path.exists() and thumbnail_sheet_path.is_file():
        notes.append("Thumbnail sheet is available for quick visual review.")
    if artifact_entry.get("status_reason"):
        notes.append(str(artifact_entry.get("status_reason")))

    return {
        "ok": True,
        "artifact_root": str(artifact_root),
        "artifact": artifact_entry,
        "detail": {
            "metadata": metadata_payload,
            "review": review_payload if isinstance(review_payload, dict) else None,
            "preview_manifest": preview_manifest_payload if isinstance(preview_manifest_payload, dict) else None,
            "preview_slides": preview_slides,
            "contract": contract_payload if isinstance(contract_payload, dict) else None,
            "payload": payload_payload if isinstance(payload_payload, dict) else None,
            "assets": _artifact_asset_entries(metadata_payload, metadata_path),
            "notes": notes,
        },
    }


def build_product_command_center_payload(bootstrap: ProductBootstrap, *, recent_limit: int = 5) -> dict[str, object]:
    documents = list_product_documents(bootstrap.rag_settings)
    run_history = build_product_run_history_payload(bootstrap, recent_limit=recent_limit)
    artifact_payload = build_product_artifact_payload(bootstrap, recent_limit=max(recent_limit * 4, recent_limit))
    ready_recent_artifacts = [
        item
        for item in (artifact_payload.get("artifacts") or [])
        if str(item.get("status") or "").strip().lower() == "ready"
    ][:recent_limit]
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
        "recent_artifacts": ready_recent_artifacts,
    }


def build_product_document_library_payload(
    bootstrap: ProductBootstrap,
    *,
    additional_documents: list[object] | None = None,
) -> dict[str, object]:
    documents = list_product_documents(bootstrap.rag_settings)

    if additional_documents:
        merged_by_id: dict[str, object] = {}
        anonymous_index = 0
        for item in [*documents, *additional_documents]:
            document_id = str(getattr(item, "document_id", "") or "").strip()
            if not document_id:
                anonymous_index += 1
                document_id = f"__anonymous_document_{anonymous_index}"
            merged_by_id[document_id] = item
        documents = list(merged_by_id.values())

    direct_upload_enabled = bool(getattr(bootstrap.product_settings, "allow_direct_uploads", True))
    status_counts: dict[str, int] = {
        "indexed": 0,
        "indexing": 0,
        "warning": 0,
        "error": 0,
        "pending": 0,
    }
    for item in documents:
        status_counts[getattr(item, "status", "pending")] = status_counts.get(getattr(item, "status", "pending"), 0) + 1

    indexed_documents = sum(1 for item in documents if getattr(item, "indexed_at", None))
    return {
        "ok": True,
        "summary": {
            "total_documents": len(documents),
            "indexed_documents": indexed_documents,
            "warning_documents": int(status_counts.get("warning") or 0),
            "error_documents": int(status_counts.get("error") or 0),
            "pending_documents": int(status_counts.get("pending") or 0),
            "indexing_documents": int(status_counts.get("indexing") or 0),
            "total_chunks": sum(int(getattr(item, "chunk_count", 0) or 0) for item in documents),
            "total_chars": sum(int(getattr(item, "char_count", 0) or 0) for item in documents),
        },
        "capabilities": {
            "direct_upload_enabled": direct_upload_enabled,
            "nextcloud_import_enabled": True,
            "public_demo_mode": not direct_upload_enabled,
        },
        "documents": [item.model_dump(mode="json") for item in documents if hasattr(item, "model_dump")],
    }
