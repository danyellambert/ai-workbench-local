from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from uuid import uuid4

from ..config import PresentationExportSettings, get_presentation_export_settings
from ..storage.phase7_model_comparison_log import load_model_comparison_log
from ..storage.phase8_eval_store import load_eval_runs
from ..storage.phase95_evidenceops_action_store import load_evidenceops_actions
from ..storage.phase95_evidenceops_worklog import load_evidenceops_worklog
from ..structured.envelope import StructuredResult
from .presentation_export import (
    DEFAULT_PRESENTATION_EXPORT_CONTRACT_VERSION,
    DEFAULT_PRESENTATION_EXPORT_KIND,
    EXECUTIVE_DECK_EXPORT_KIND_LABELS,
    SUPPORTED_EXECUTIVE_DECK_EXPORT_KINDS,
    build_executive_deck_contract,
    build_ppt_creator_payload_from_executive_deck_contract,
    normalize_executive_deck_export_kind,
)


def _json_dump(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _build_export_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"deckexp_{timestamp}_{uuid4().hex[:8]}"


def _normalize_json_response(payload: object) -> dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        return dict(payload.get("result") or {})
    return dict(payload) if isinstance(payload, dict) else {}


def _http_json_request(
    *,
    method: str,
    url: str,
    timeout_seconds: int,
    json_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if json_payload is not None:
        data = json.dumps(json_payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib_request.Request(url=url, data=data, headers=headers, method=method.upper())
    with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body or "{}")
    return parsed if isinstance(parsed, dict) else {"raw": parsed}


def _download_artifact(*, base_url: str, remote_path: str, timeout_seconds: int) -> bytes:
    query = urllib_parse.urlencode({"path": remote_path})
    artifact_url = f"{base_url.rstrip('/')}/artifact?{query}"
    with urllib_request.urlopen(artifact_url, timeout=timeout_seconds) as response:
        return response.read()


def _resolve_model_comparison_entries(
    *,
    model_comparison_entries: list[dict[str, Any]] | None,
    phase7_log_path: str | Path | None,
) -> list[dict[str, Any]]:
    if model_comparison_entries is not None:
        return [item for item in model_comparison_entries if isinstance(item, dict)]
    if phase7_log_path:
        return load_model_comparison_log(Path(phase7_log_path))
    return []


def _resolve_eval_entries(
    *,
    eval_entries: list[dict[str, Any]] | None,
    phase8_eval_db_path: str | Path | None,
) -> list[dict[str, Any]]:
    if eval_entries is not None:
        return [item for item in eval_entries if isinstance(item, dict)]
    if phase8_eval_db_path:
        return load_eval_runs(Path(phase8_eval_db_path), limit=250)
    return []


def _resolve_structured_result(
    *,
    structured_result: StructuredResult | dict[str, Any] | None,
) -> StructuredResult | None:
    if structured_result is None:
        return None
    return structured_result if isinstance(structured_result, StructuredResult) else StructuredResult.model_validate(structured_result)


def _resolve_evidenceops_worklog_entries(
    *,
    evidenceops_worklog_entries: list[dict[str, Any]] | None,
    phase95_evidenceops_worklog_path: str | Path | None,
) -> list[dict[str, Any]]:
    if evidenceops_worklog_entries is not None:
        return [item for item in evidenceops_worklog_entries if isinstance(item, dict)]
    if phase95_evidenceops_worklog_path:
        return load_evidenceops_worklog(Path(phase95_evidenceops_worklog_path))
    return []


def _resolve_evidenceops_action_entries(
    *,
    evidenceops_action_entries: list[dict[str, Any]] | None,
    phase95_evidenceops_action_store_path: str | Path | None,
) -> list[dict[str, Any]]:
    if evidenceops_action_entries is not None:
        return [item for item in evidenceops_action_entries if isinstance(item, dict)]
    if phase95_evidenceops_action_store_path:
        return load_evidenceops_actions(Path(phase95_evidenceops_action_store_path), limit=250)
    return []


def resolve_enabled_export_kinds(settings: PresentationExportSettings) -> tuple[str, ...]:
    normalized = []
    for value in settings.enabled_export_kinds:
        normalized_value = normalize_executive_deck_export_kind(value)
        if normalized_value not in normalized:
            normalized.append(normalized_value)
    return tuple(normalized)


def is_export_kind_enabled(*, export_kind: str, settings: PresentationExportSettings) -> bool:
    enabled_export_kinds = resolve_enabled_export_kinds(settings)
    if not enabled_export_kinds:
        return True
    return normalize_executive_deck_export_kind(export_kind) in enabled_export_kinds


def generate_executive_deck(
    *,
    export_kind: str,
    model_comparison_entries: list[dict[str, Any]] | None = None,
    eval_entries: list[dict[str, Any]] | None = None,
    structured_result: StructuredResult | dict[str, Any] | None = None,
    evidenceops_worklog_entries: list[dict[str, Any]] | None = None,
    evidenceops_action_entries: list[dict[str, Any]] | None = None,
    phase7_log_path: str | Path | None = None,
    phase8_eval_db_path: str | Path | None = None,
    phase95_evidenceops_worklog_path: str | Path | None = None,
    phase95_evidenceops_action_store_path: str | Path | None = None,
    settings: PresentationExportSettings | None = None,
) -> dict[str, Any]:
    requested_export_kind = export_kind
    export_kind = normalize_executive_deck_export_kind(export_kind)
    if export_kind not in SUPPORTED_EXECUTIVE_DECK_EXPORT_KINDS:
        raise ValueError(f"Unsupported executive deck export kind: {export_kind}")

    resolved_settings = settings or get_presentation_export_settings()
    export_id = _build_export_id()
    artifact_dir = Path(resolved_settings.local_artifact_dir) / export_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "export_id": export_id,
        "status": "created",
        "requested_export_kind": requested_export_kind,
        "export_kind": export_kind,
        "export_kind_label": EXECUTIVE_DECK_EXPORT_KIND_LABELS.get(export_kind, export_kind),
        "contract_version": DEFAULT_PRESENTATION_EXPORT_CONTRACT_VERSION,
        "enabled": bool(resolved_settings.enabled),
        "base_url": resolved_settings.base_url,
        "service_health": None,
        "remote_output_path": None,
        "remote_preview_dir": None,
        "local_artifact_dir": str(artifact_dir),
        "local_contract_path": None,
        "local_payload_path": None,
        "local_render_request_path": None,
        "local_render_response_path": None,
        "local_pptx_path": None,
        "local_review_path": None,
        "local_preview_manifest_path": None,
        "local_thumbnail_sheet_path": None,
        "render_latency_s": None,
        "artifact_download_latency_s": None,
        "pptx_size_bytes": None,
        "model_comparison_entry_count": 0,
        "eval_entry_count": 0,
        "evidenceops_worklog_entry_count": 0,
        "evidenceops_action_entry_count": 0,
        "structured_task_type": None,
        "warnings": [],
        "error_message": None,
    }

    def _persist_metadata() -> None:
        _write_json(artifact_dir / "metadata.json", result)

    try:
        if not is_export_kind_enabled(export_kind=export_kind, settings=resolved_settings):
            enabled_export_kinds = resolve_enabled_export_kinds(resolved_settings)
            result["status"] = "disabled_export_kind"
            result["service_health"] = "disabled_export_kind"
            result["error_message"] = (
                f"Export kind `{export_kind}` is disabled by the current configuration. "
                f"Enabled: {', '.join(enabled_export_kinds) if enabled_export_kinds else 'all'}"
            )
            _persist_metadata()
            return result

        resolved_model_entries = _resolve_model_comparison_entries(
            model_comparison_entries=model_comparison_entries,
            phase7_log_path=phase7_log_path,
        )
        resolved_eval_entries = _resolve_eval_entries(
            eval_entries=eval_entries,
            phase8_eval_db_path=phase8_eval_db_path,
        )
        resolved_structured_result = _resolve_structured_result(structured_result=structured_result)
        resolved_worklog_entries = _resolve_evidenceops_worklog_entries(
            evidenceops_worklog_entries=evidenceops_worklog_entries,
            phase95_evidenceops_worklog_path=phase95_evidenceops_worklog_path,
        )
        resolved_action_entries = _resolve_evidenceops_action_entries(
            evidenceops_action_entries=evidenceops_action_entries,
            phase95_evidenceops_action_store_path=phase95_evidenceops_action_store_path,
        )

        result["model_comparison_entry_count"] = len(resolved_model_entries)
        result["eval_entry_count"] = len(resolved_eval_entries)
        result["evidenceops_worklog_entry_count"] = len(resolved_worklog_entries)
        result["evidenceops_action_entry_count"] = len(resolved_action_entries)
        if resolved_structured_result is not None:
            result["structured_task_type"] = resolved_structured_result.task_type

        if export_kind == DEFAULT_PRESENTATION_EXPORT_KIND and not resolved_model_entries:
            result["status"] = "failed"
            result["error_message"] = "No benchmark/model comparison evidence is available to generate the executive deck."
            _persist_metadata()
            return result
        if export_kind == DEFAULT_PRESENTATION_EXPORT_KIND and not resolved_eval_entries:
            result["warnings"].append("No eval run is available; the deck will be generated mainly from the benchmark signals.")

        contract = build_executive_deck_contract(
            export_kind=export_kind,
            model_comparison_entries=resolved_model_entries,
            eval_entries=resolved_eval_entries,
            structured_result=resolved_structured_result,
            evidenceops_worklog_entries=resolved_worklog_entries,
            evidenceops_action_entries=resolved_action_entries,
        )
        contract_payload = contract.model_dump(exclude_none=True)
        result["contract_version"] = str(contract_payload.get("contract_version") or result["contract_version"])
        contract_path = artifact_dir / "contract.json"
        _write_json(contract_path, contract_payload)
        result["local_contract_path"] = str(contract_path)

        payload = build_ppt_creator_payload_from_executive_deck_contract(contract)
        payload_path = artifact_dir / "payload.json"
        _write_json(payload_path, payload)
        result["local_payload_path"] = str(payload_path)

        if not resolved_settings.enabled:
            result["status"] = "disabled"
            result["service_health"] = "disabled"
            result["warnings"].append(
                "PRESENTATION_EXPORT_ENABLED=false. The contract and payload were persisted locally, but the renderer was not called."
            )
            _persist_metadata()
            return result

        if not str(resolved_settings.base_url or "").strip():
            result["status"] = "disabled"
            result["service_health"] = "missing_base_url"
            result["error_message"] = "PRESENTATION_EXPORT_BASE_URL is not configured."
            _persist_metadata()
            return result

        try:
            health_payload = _http_json_request(
                method="GET",
                url=f"{resolved_settings.base_url.rstrip('/')}/health",
                timeout_seconds=resolved_settings.timeout_seconds,
            )
            result["service_health"] = str(health_payload.get("status") or "ok")
        except Exception as error:
            result["status"] = "service_unavailable"
            result["service_health"] = "unavailable"
            result["error_message"] = f"Failed to validate renderer health: {error}"
            _persist_metadata()
            return result

        remote_output_path = f"{resolved_settings.remote_output_dir.rstrip('/')}/{export_id}/{export_kind}.pptx"
        remote_preview_dir = f"{resolved_settings.remote_preview_dir.rstrip('/')}/{export_id}"
        result["remote_output_path"] = remote_output_path
        result["remote_preview_dir"] = remote_preview_dir

        render_request_payload = {
            "spec": payload,
            "output_path": remote_output_path,
            "include_review": bool(resolved_settings.include_review),
            "preview_output_dir": remote_preview_dir,
            "preview_backend": resolved_settings.preview_backend,
            "preview_require_real": bool(resolved_settings.require_real_previews),
            "preview_fail_on_regression": bool(resolved_settings.fail_on_regression),
        }
        render_request_path = artifact_dir / "render_request.json"
        _write_json(render_request_path, render_request_payload)
        result["local_render_request_path"] = str(render_request_path)

        render_started_at = datetime.now().timestamp()
        raw_render_response = _http_json_request(
            method="POST",
            url=f"{resolved_settings.base_url.rstrip('/')}/render",
            timeout_seconds=resolved_settings.timeout_seconds,
            json_payload=render_request_payload,
        )
        result["render_latency_s"] = round(datetime.now().timestamp() - render_started_at, 4)
        render_response = _normalize_json_response(raw_render_response)
        render_response_path = artifact_dir / "render_response.json"
        _write_json(render_response_path, render_response)
        result["local_render_response_path"] = str(render_response_path)

        review_payload = render_response.get("quality_review")
        if isinstance(review_payload, dict):
            review_path = artifact_dir / "review.json"
            _write_json(review_path, review_payload)
            result["local_review_path"] = str(review_path)

        output_path = str(render_response.get("output_path") or remote_output_path)
        try:
            artifact_download_started_at = datetime.now().timestamp()
            deck_bytes = _download_artifact(
                base_url=resolved_settings.base_url,
                remote_path=output_path,
                timeout_seconds=resolved_settings.timeout_seconds,
            )
            result["artifact_download_latency_s"] = round(datetime.now().timestamp() - artifact_download_started_at, 4)
            local_pptx_path = artifact_dir / Path(output_path).name
            local_pptx_path.write_bytes(deck_bytes)
            result["local_pptx_path"] = str(local_pptx_path)
            result["pptx_size_bytes"] = int(local_pptx_path.stat().st_size)
        except Exception as error:
            result["status"] = "artifact_download_failed"
            result["error_message"] = f"Failed to download the generated deck: {error}"
            _persist_metadata()
            return result

        preview_result = render_response.get("preview_result") if isinstance(render_response.get("preview_result"), dict) else {}
        preview_manifest_remote = str(preview_result.get("preview_manifest") or "").strip()
        if preview_manifest_remote:
            try:
                preview_manifest_bytes = _download_artifact(
                    base_url=resolved_settings.base_url,
                    remote_path=preview_manifest_remote,
                    timeout_seconds=resolved_settings.timeout_seconds,
                )
                local_preview_manifest_path = artifact_dir / Path(preview_manifest_remote).name
                local_preview_manifest_path.write_bytes(preview_manifest_bytes)
                result["local_preview_manifest_path"] = str(local_preview_manifest_path)
            except Exception as error:
                result["warnings"].append(f"Failed to download preview manifest: {error}")

        thumbnail_remote = str(preview_result.get("thumbnail_sheet") or "").strip()
        if thumbnail_remote:
            try:
                thumbnail_bytes = _download_artifact(
                    base_url=resolved_settings.base_url,
                    remote_path=thumbnail_remote,
                    timeout_seconds=resolved_settings.timeout_seconds,
                )
                local_thumbnail_path = artifact_dir / Path(thumbnail_remote).name
                local_thumbnail_path.write_bytes(thumbnail_bytes)
                result["local_thumbnail_sheet_path"] = str(local_thumbnail_path)
            except Exception as error:
                result["warnings"].append(f"Failed to download thumbnail sheet: {error}")

        result["status"] = "completed"
        _persist_metadata()
        return result
    except Exception as error:
        result["status"] = "failed"
        result["error_message"] = str(error)
        _persist_metadata()
        return result


def generate_benchmark_eval_executive_review_deck(
    *,
    model_comparison_entries: list[dict[str, Any]] | None = None,
    eval_entries: list[dict[str, Any]] | None = None,
    phase7_log_path: str | Path | None = None,
    phase8_eval_db_path: str | Path | None = None,
    settings: PresentationExportSettings | None = None,
) -> dict[str, Any]:
    return generate_executive_deck(
        export_kind=DEFAULT_PRESENTATION_EXPORT_KIND,
        model_comparison_entries=model_comparison_entries,
        eval_entries=eval_entries,
        phase7_log_path=phase7_log_path,
        phase8_eval_db_path=phase8_eval_db_path,
        settings=settings,
    )
