from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.app.product_bootstrap import ProductBootstrap
from src.product.action_plan_presenter import build_action_plan_view
from src.product.command_center import build_product_workflow_history_entry
from src.product.models import ProductWorkflowRequest, ProductWorkflowResult
from src.product.service import run_product_workflow
from src.storage.lab_state import append_lab_workflow_run
from src.storage.product_telemetry import append_product_telemetry_run, get_product_telemetry_run, update_product_telemetry_run
from src.storage.product_workflow_history import append_product_workflow_history_entry
from src.storage.runtime_execution_log import append_runtime_execution_log_entry
from src.storage.runtime_paths import (
    get_lab_workflow_runs_path,
    get_product_telemetry_path,
    get_product_workflow_history_path,
    get_runtime_execution_log_path,
)
from src.product.runtime_eval import persist_product_runtime_evals


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_trace_id(workflow_id: str) -> str:
    return f"trace_{workflow_id}_{uuid4().hex[:12]}"


def build_run_id(workflow_id: str) -> str:
    return f"run_{workflow_id}_{uuid4().hex[:12]}"


def _safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _extract_execution_metadata(result: ProductWorkflowResult | None) -> dict[str, Any]:
    if result is None or result.structured_result is None:
        return {}
    metadata = result.structured_result.execution_metadata
    return dict(metadata) if isinstance(metadata, dict) else {}


def _extract_telemetry(result: ProductWorkflowResult | None) -> dict[str, Any]:
    metadata = _extract_execution_metadata(result)
    telemetry = metadata.get("telemetry")
    return dict(telemetry) if isinstance(telemetry, dict) else {}


def _extract_timings(result: ProductWorkflowResult | None) -> dict[str, float]:
    telemetry = _extract_telemetry(result)
    timings = telemetry.get("timings_s")
    if not isinstance(timings, dict):
        return {}
    return {str(key): _safe_float(value) for key, value in timings.items() if isinstance(key, str)}


def _extract_provider_usage(result: ProductWorkflowResult | None) -> dict[str, Any]:
    telemetry = _extract_telemetry(result)
    provider_calls = telemetry.get("provider_calls") if isinstance(telemetry.get("provider_calls"), list) else []
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    prompt_chars = 0
    generation_latency_s = 0.0
    usage_source = None
    cost_source = None
    cost_usd = None
    for call in provider_calls:
        if not isinstance(call, dict):
            continue
        generation_latency_s += _safe_float(call.get("duration_s"))
        prompt_chars += _safe_int(call.get("prompt_chars"))
        native_usage = call.get("native_usage") if isinstance(call.get("native_usage"), dict) else {}
        prompt_tokens += _safe_int(native_usage.get("prompt_tokens"))
        completion_tokens += _safe_int(native_usage.get("completion_tokens"))
        total_tokens += _safe_int(native_usage.get("total_tokens"))
        usage_source = usage_source or native_usage.get("usage_source")
        cost_source = cost_source or native_usage.get("cost_source")
        if isinstance(native_usage.get("cost_usd"), (int, float)):
            cost_usd = (cost_usd or 0.0) + float(native_usage.get("cost_usd") or 0.0)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "prompt_chars": prompt_chars,
        "generation_latency_s": round(generation_latency_s, 4) if generation_latency_s else None,
        "usage_source": usage_source,
        "cost_source": cost_source,
        "cost_usd": round(cost_usd, 6) if isinstance(cost_usd, (int, float)) else None,
        "provider_calls": provider_calls,
    }


def _extract_spans(result: ProductWorkflowResult | None, *, request: ProductWorkflowRequest, duration_s: float) -> list[dict[str, Any]]:
    metadata = _extract_execution_metadata(result)
    workflow_trace = metadata.get("workflow_trace") if isinstance(metadata.get("workflow_trace"), list) else []
    timings = _extract_timings(result)
    provider_usage = _extract_provider_usage(result)

    spans: list[dict[str, Any]] = []
    if request.document_ids:
        spans.append({
            "span_id": f"span_select_{uuid4().hex[:8]}",
            "name": "select_documents",
            "stage": "select_documents",
            "status": "completed",
            "detail": f"{len(request.document_ids)} document(s) selected",
            "duration_ms": 0,
        })
    context_duration_s = timings.get("context_build_s") or 0.0
    spans.append({
        "span_id": f"span_context_{uuid4().hex[:8]}",
        "name": "build_context",
        "stage": "build_context",
        "status": "completed",
        "detail": f"Strategy: {request.context_strategy or 'default'}",
        "duration_ms": int(round(context_duration_s * 1000)),
    })
    if provider_usage.get("generation_latency_s") is not None:
        spans.append({
            "span_id": f"span_generate_{uuid4().hex[:8]}",
            "name": "generate_structured_output",
            "stage": "generate",
            "status": "completed" if result is not None and result.status != "error" else "error",
            "detail": str((_extract_execution_metadata(result).get("execution_strategy_used") or "direct") if result is not None else "direct"),
            "duration_ms": int(round(_safe_float(provider_usage.get("generation_latency_s")) * 1000)),
        })
    parsing_duration_s = timings.get("parsing_s") or 0.0
    if parsing_duration_s:
        spans.append({
            "span_id": f"span_parse_{uuid4().hex[:8]}",
            "name": "parse_and_validate",
            "stage": "parse_validate",
            "status": "completed" if result is not None and result.status != "error" else "warning",
            "detail": "Structured payload parsing and validation",
            "duration_ms": int(round(parsing_duration_s * 1000)),
        })
    for index, node in enumerate(workflow_trace):
        if not isinstance(node, dict):
            continue
        spans.append({
            "span_id": f"span_trace_{index}_{uuid4().hex[:6]}",
            "name": str(node.get("node") or f"workflow_node_{index + 1}"),
            "stage": "workflow_trace",
            "status": "completed" if bool(node.get("success", True)) else "error",
            "detail": str(node.get("detail") or "Workflow trace node"),
            "duration_ms": None,
            "attempt": _safe_int(node.get("attempt") or 1, 1),
            "context_strategy": str(node.get("context_strategy") or request.context_strategy or "default"),
        })
    spans.append({
        "span_id": f"span_total_{uuid4().hex[:8]}",
        "name": "complete_run",
        "stage": "total",
        "status": "completed" if result is not None and result.status != "error" else "error",
        "detail": "End-to-end product workflow run",
        "duration_ms": int(round(duration_s * 1000)),
    })
    return spans


def _derive_needs_review(result: ProductWorkflowResult | None) -> bool:
    if result is None:
        return False
    if result.status == "warning":
        return True
    metadata = _extract_execution_metadata(result)
    if bool(metadata.get("needs_review")):
        return True
    return bool(result.warnings)


def _derive_review_reason(result: ProductWorkflowResult | None, error_message: str | None = None) -> str | None:
    if error_message:
        return error_message
    metadata = _extract_execution_metadata(result)
    reason = str(metadata.get("needs_review_reason") or "").strip()
    if reason:
        return reason
    if result is None:
        return None
    return "; ".join(str(item) for item in (result.warnings or [])[:3]) or None


def _extract_action_plan_entries(result: ProductWorkflowResult | None) -> list[dict[str, Any]]:
    if result is None or result.workflow_id != "action_plan_evidence_review":
        return []
    view = build_action_plan_view(result)
    items = view.get("items") if isinstance(view, dict) else []
    entries: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return entries
    for item in items:
        if not isinstance(item, dict):
            continue
        entries.append({
            "title": str(item.get("title") or "Action item"),
            "owner": str(item.get("owner") or "Unassigned"),
            "due_date": str(item.get("due_date") or "").strip() or None,
            "status": str(item.get("status") or "open"),
            "priority": str(item.get("priority") or "medium"),
            "source": str(item.get("source") or "").strip() or None,
        })
    return entries


def _build_runtime_entry(
    *,
    run_id: str,
    trace_id: str,
    request: ProductWorkflowRequest,
    result: ProductWorkflowResult | None,
    duration_s: float,
    error_message: str | None = None,
) -> dict[str, Any]:
    metadata = _extract_execution_metadata(result)
    timings = _extract_timings(result)
    provider_usage = _extract_provider_usage(result)
    grounding = result.grounding_preview if result is not None else None
    full_document_chars = _safe_int(metadata.get("document_chars_estimate") or 0)
    context_chars = _safe_int(getattr(grounding, "context_chars", 0) if grounding is not None else 0)
    context_pressure_ratio = min(context_chars / max(full_document_chars, 1), 1.0) if full_document_chars > 0 else 0.0
    source_count = _safe_int(getattr(grounding, "source_block_count", 0) if grounding is not None else 0)
    return {
        "timestamp": _now_iso(),
        "trace_id": trace_id,
        "run_id": run_id,
        "workflow_id": request.workflow_id,
        "flow_type": "product_workflow",
        "task_type": str((result.debug_metadata if result is not None else {}).get("task_type") or request.workflow_id),
        "provider": str(metadata.get("provider_effective") or metadata.get("provider") or request.provider),
        "provider_requested": request.provider,
        "provider_effective": str(metadata.get("provider_effective") or metadata.get("provider") or request.provider),
        "model": str(metadata.get("model") or request.model or "unknown"),
        "latency_s": round(duration_s, 4),
        "retrieval_latency_s": round(_safe_float(timings.get("document_load_s") or 0.0), 4) if timings.get("document_load_s") is not None else None,
        "generation_latency_s": provider_usage.get("generation_latency_s") or round(_safe_float(timings.get("provider_total_s") or 0.0), 4) or None,
        "prompt_build_latency_s": round(_safe_float(timings.get("context_build_s") or 0.0), 4) if timings.get("context_build_s") is not None else None,
        "parsing_latency_s": round(_safe_float(timings.get("parsing_s") or 0.0), 4) if timings.get("parsing_s") is not None else None,
        "success": bool(result is not None and result.status != "error" and not error_message),
        "error_message": error_message,
        "needs_review": _derive_needs_review(result),
        "needs_review_reason": _derive_review_reason(result, error_message),
        "source_document_ids": list(request.document_ids),
        "selected_documents": len(request.document_ids),
        "retrieved_chunks_count": source_count,
        "context_chars": context_chars,
        "context_budget_chars": full_document_chars or None,
        "context_pressure_ratio": round(context_pressure_ratio, 4),
        "prompt_chars": provider_usage.get("prompt_chars"),
        "output_chars": len(result.summary or "") if result is not None else 0,
        "prompt_tokens": provider_usage.get("prompt_tokens"),
        "completion_tokens": provider_usage.get("completion_tokens"),
        "total_tokens": provider_usage.get("total_tokens"),
        "cost_usd": provider_usage.get("cost_usd"),
        "usage_source": provider_usage.get("usage_source"),
        "cost_source": provider_usage.get("cost_source"),
        "context_window_mode": request.context_window_mode,
        "context_window": request.context_window,
        "resolved_context_window": metadata.get("resolved_context_window") or request.context_window,
        "context_window_cap": metadata.get("context_window_cap") or request.context_window,
        "temperature": request.temperature,
        "top_p": request.top_p,
        "max_tokens": request.max_tokens,
        "prompt_profile": request.prompt_profile,
        "execution_strategy_requested": metadata.get("execution_strategy_requested"),
        "execution_strategy_used": metadata.get("execution_strategy_used"),
        "workflow_route_decision": metadata.get("workflow_route_decision"),
        "workflow_guardrail_decision": metadata.get("workflow_guardrail_decision"),
        "workflow_attempts": metadata.get("workflow_attempts"),
        "workflow_context_strategies": metadata.get("workflow_context_strategies"),
        "agent_intent": metadata.get("agent_intent"),
        "agent_tool": metadata.get("agent_tool"),
        "agent_answer_mode": metadata.get("agent_answer_mode"),
        "retrieval_backend_used": metadata.get("retrieval_backend_used"),
        "retrieval_strategy_requested": metadata.get("retrieval_strategy_requested"),
        "retrieval_strategy_used": metadata.get("retrieval_strategy_used"),
        "top_k_effective": source_count or None,
        "provider_calls": provider_usage.get("provider_calls"),
        "surface": "product_api",
    }


def _build_lab_run_record(
    *,
    run_id: str,
    trace_id: str,
    request: ProductWorkflowRequest,
    result: ProductWorkflowResult | None,
    runtime_entry: dict[str, Any],
    surface: str,
    reran_from_run_id: str | None = None,
) -> dict[str, Any]:
    document_names = list((result.debug_metadata if result is not None else {}).get("source_documents") or [])
    artifact_item = next((item for item in (result.artifacts if result is not None else []) if getattr(item, "available", False)), None)
    artifact_path = str(getattr(artifact_item, "path", "") or "").strip() or None
    artifact_label = str(getattr(artifact_item, "label", "") or getattr(artifact_item, "download_name", "") or "").strip() or None
    trace = {
        "trace_id": trace_id,
        "spans": _extract_spans(result, request=request, duration_s=_safe_float(runtime_entry.get("latency_s") or 0.0)),
        "warnings": [str(item) for item in ((result.warnings if result is not None else []) or []) if str(item or "").strip()],
    }
    return {
        "run_id": run_id,
        "trace_id": trace_id,
        "task_id": request.workflow_id,
        "workflow_id": request.workflow_id,
        "status": result.status if result is not None else "error",
        "input_text": request.input_text,
        "document_ids": list(request.document_ids),
        "document_names": document_names,
        "confidence": _safe_float(getattr(result.structured_result, "overall_confidence", 0.0) if result is not None and result.structured_result is not None else 0.0),
        "needs_review": _derive_needs_review(result),
        "review_reason": _derive_review_reason(result),
        "provider": runtime_entry.get("provider"),
        "model": runtime_entry.get("model"),
        "summary": result.summary if result is not None else "Workflow execution failed.",
        "artifact_path": artifact_path,
        "artifact_label": artifact_label,
        "execution_mode": surface,
        "result_title": f"{result.workflow_label if result is not None else request.workflow_id} result",
        "source_count": runtime_entry.get("retrieved_chunks_count") or 0,
        "latency_s": runtime_entry.get("latency_s") or 0.0,
        "total_tokens": runtime_entry.get("total_tokens") or 0,
        "context_chars": runtime_entry.get("context_chars") or 0,
        "trace": trace,
        "result": result.model_dump(mode="json") if result is not None else {},
        "request_payload": request.model_dump(mode="json"),
        "response_payload": result.model_dump(mode="json") if result is not None else {},
        "reran_from_run_id": reran_from_run_id,
    }


def _build_telemetry_run(
    *,
    run_id: str,
    trace_id: str,
    request: ProductWorkflowRequest,
    result: ProductWorkflowResult | None,
    runtime_entry: dict[str, Any],
    history_entry: dict[str, Any] | None,
    surface: str,
    started_at: str,
    completed_at: str,
    error_message: str | None = None,
    reran_from_run_id: str | None = None,
) -> dict[str, Any]:
    exec_metadata = _extract_execution_metadata(result)
    action_entries = _extract_action_plan_entries(result)
    lineage = {
        "history_entry_id": history_entry.get("id") if isinstance(history_entry, dict) else run_id,
        "artifacts": history_entry.get("artifact_items") if isinstance(history_entry, dict) and isinstance(history_entry.get("artifact_items"), list) else [],
        "deliveries": list((((history_entry or {}).get("delivery_outputs") or {}).values())) if isinstance((history_entry or {}).get("delivery_outputs"), dict) else [],
        "evidenceops_actions": action_entries,
    }
    telemetry_run = {
        "trace_id": trace_id,
        "run_id": run_id,
        "workflow_id": request.workflow_id,
        "workflow_label": result.workflow_label if result is not None else request.workflow_id.replace("_", " ").title(),
        "surface": surface,
        "status": result.status if result is not None else "error",
        "started_at": started_at,
        "completed_at": completed_at,
        "needs_review": _derive_needs_review(result),
        "review_reason": _derive_review_reason(result, error_message),
        "request": request.model_dump(mode="json"),
        "summary": {
            "title": result.workflow_label if result is not None else request.workflow_id.replace("_", " ").title(),
            "status": result.status if result is not None else "error",
            "summary": result.summary if result is not None else "Workflow execution failed.",
            "highlights": list((result.highlights if result is not None else []) or []),
            "recommendation": result.recommendation if result is not None else None,
            "warnings": list((result.warnings if result is not None else []) or []),
            "grounding_preview": result.grounding_preview.model_dump(mode="json") if result is not None and result.grounding_preview is not None else None,
        },
        "routing": {
            "execution_strategy_requested": exec_metadata.get("execution_strategy_requested"),
            "execution_strategy_used": exec_metadata.get("execution_strategy_used"),
            "workflow_route_decision": exec_metadata.get("workflow_route_decision"),
            "workflow_guardrail_decision": exec_metadata.get("workflow_guardrail_decision"),
            "workflow_context_strategies": exec_metadata.get("workflow_context_strategies"),
            "context_strategy": request.context_strategy,
        },
        "runtime": runtime_entry,
        "spans": _extract_spans(result, request=request, duration_s=_safe_float(runtime_entry.get("latency_s") or 0.0)),
        "lineage": lineage,
        "reran_from_run_id": reran_from_run_id,
        "error_message": error_message,
    }
    digest_source = json.dumps({"request": telemetry_run["request"], "summary": telemetry_run["summary"]}, ensure_ascii=False, sort_keys=True)
    telemetry_run["digest"] = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:16]
    return telemetry_run




def attach_artifact_lineage(
    workspace_root: Path,
    *,
    run_id: str,
    artifacts: list[dict[str, Any]] | None = None,
    export_result: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    path = get_product_telemetry_path(workspace_root)
    current = get_product_telemetry_run(path, run_id)
    if current is None:
        return None
    lineage = dict(current.get("lineage") or {}) if isinstance(current.get("lineage"), dict) else {}
    current_artifacts = list(lineage.get("artifacts") or []) if isinstance(lineage.get("artifacts"), list) else []
    if artifacts:
        current_artifacts.extend([item for item in artifacts if isinstance(item, dict)])
    if export_result:
        current_artifacts.append({
            "artifact_type": "deck_export",
            "status": export_result.get("status"),
            "local_pptx_path": export_result.get("local_pptx_path"),
            "local_contract_path": export_result.get("local_contract_path"),
            "local_payload_path": export_result.get("local_payload_path"),
            "local_review_path": export_result.get("local_review_path"),
        })
    lineage["artifacts"] = current_artifacts
    return update_product_telemetry_run(path, run_id, {"lineage": lineage})


def attach_delivery_lineage(workspace_root: Path, *, run_id: str, target: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    path = get_product_telemetry_path(workspace_root)
    current = get_product_telemetry_run(path, run_id)
    if current is None:
        return None
    lineage = dict(current.get("lineage") or {}) if isinstance(current.get("lineage"), dict) else {}
    deliveries = list(lineage.get("deliveries") or []) if isinstance(lineage.get("deliveries"), list) else []
    deliveries.append({
        "target": target,
        "status": payload.get("status") or ("planned" if payload.get("dry_run") else "completed"),
        "timestamp": payload.get("timestamp") or _now_iso(),
        "dry_run": bool(payload.get("dry_run")),
        "message": payload.get("message") or payload.get("summary"),
        "url": payload.get("url"),
    })
    lineage["deliveries"] = deliveries
    return update_product_telemetry_run(path, run_id, {"lineage": lineage})


def execute_product_workflow_with_telemetry(
    *,
    bootstrap: ProductBootstrap,
    request: ProductWorkflowRequest,
    document_lookup: dict[str, str] | None = None,
    surface: str = "product_api",
    reran_from_run_id: str | None = None,
) -> dict[str, Any]:
    resolved_document_lookup = document_lookup or {}
    started_at = _now_iso()
    trace_id = build_trace_id(request.workflow_id)
    run_id = build_run_id(request.workflow_id)
    started_perf = datetime.now(timezone.utc)
    try:
        result = run_product_workflow(request)
        finished_perf = datetime.now(timezone.utc)
        duration_s = max((finished_perf - started_perf).total_seconds(), 0.0)
        runtime_entry = _build_runtime_entry(run_id=run_id, trace_id=trace_id, request=request, result=result, duration_s=duration_s)
        runtime_entry["surface"] = surface
        result.debug_metadata = {**dict(result.debug_metadata or {}), "run_id": run_id, "trace_id": trace_id, "surface": surface, "latency_s": runtime_entry.get("latency_s"), "total_tokens": runtime_entry.get("total_tokens") or 0, "prompt_tokens": runtime_entry.get("prompt_tokens") or 0, "completion_tokens": runtime_entry.get("completion_tokens") or 0, "cost_usd": runtime_entry.get("cost_usd"), "source_count": runtime_entry.get("retrieved_chunks_count") or 0, "context_chars": runtime_entry.get("context_chars") or 0}
        history_entry = build_product_workflow_history_entry(request=request, document_lookup=resolved_document_lookup, result=result, duration_s=duration_s)
        history_entry["id"] = run_id
        history_entry["trace_id"] = trace_id
        history_entry["surface"] = surface
        history_entry["reran_from_run_id"] = reran_from_run_id
        history_entry["status_classification"] = "live"
        append_product_workflow_history_entry(get_product_workflow_history_path(bootstrap.workspace_root), history_entry)
        append_runtime_execution_log_entry(get_runtime_execution_log_path(bootstrap.workspace_root), runtime_entry)
        run_record = _build_lab_run_record(run_id=run_id, trace_id=trace_id, request=request, result=result, runtime_entry=runtime_entry, surface=surface, reran_from_run_id=reran_from_run_id)
        append_lab_workflow_run(get_lab_workflow_runs_path(bootstrap.workspace_root), run_record)
        telemetry_run = _build_telemetry_run(run_id=run_id, trace_id=trace_id, request=request, result=result, runtime_entry=runtime_entry, history_entry=history_entry, surface=surface, started_at=started_at, completed_at=_now_iso(), reran_from_run_id=reran_from_run_id)
        append_product_telemetry_run(get_product_telemetry_path(bootstrap.workspace_root), telemetry_run)
        persist_product_runtime_evals(bootstrap=bootstrap, telemetry_run=telemetry_run, result=result)
        return {"result": result, "run_id": run_id, "trace_id": trace_id, "history_entry": history_entry, "runtime_entry": runtime_entry, "telemetry_run": telemetry_run, "run_record": run_record}
    except Exception as error:
        finished_perf = datetime.now(timezone.utc)
        duration_s = max((finished_perf - started_perf).total_seconds(), 0.0)
        runtime_entry = _build_runtime_entry(run_id=run_id, trace_id=trace_id, request=request, result=None, duration_s=duration_s, error_message=str(error))
        runtime_entry["surface"] = surface
        history_entry = build_product_workflow_history_entry(request=request, document_lookup=resolved_document_lookup, result=None, duration_s=duration_s, error_message=str(error))
        history_entry["id"] = run_id
        history_entry["trace_id"] = trace_id
        history_entry["surface"] = surface
        history_entry["reran_from_run_id"] = reran_from_run_id
        history_entry["status_classification"] = "live"
        append_product_workflow_history_entry(get_product_workflow_history_path(bootstrap.workspace_root), history_entry)
        append_runtime_execution_log_entry(get_runtime_execution_log_path(bootstrap.workspace_root), runtime_entry)
        telemetry_run = _build_telemetry_run(run_id=run_id, trace_id=trace_id, request=request, result=None, runtime_entry=runtime_entry, history_entry=history_entry, surface=surface, started_at=started_at, completed_at=_now_iso(), error_message=str(error), reran_from_run_id=reran_from_run_id)
        append_product_telemetry_run(get_product_telemetry_path(bootstrap.workspace_root), telemetry_run)
        persist_product_runtime_evals(bootstrap=bootstrap, telemetry_run=telemetry_run, result=None)
        raise
