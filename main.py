import time
from dataclasses import replace

import streamlit as st
from src.app.bootstrap import build_app_bootstrap
from src.config import get_ollama_settings, get_presentation_export_settings, get_rag_settings
from src.evidence_cv.config import build_evidence_config_from_rag_settings
from src.prompt_profiles import build_prompt_messages, get_prompt_profiles
from src.services.presentation_export import DEFAULT_PRESENTATION_EXPORT_KIND
from src.providers.registry import (
    build_embedding_provider_sidebar_state,
    build_provider_registry,
    filter_registry_by_capability,
    resolve_provider_runtime_profile,
)
from src.rag.loaders import describe_loader_strategy, load_document
from src.rag.pdf_extraction import describe_pdf_extraction_mode, normalize_pdf_extraction_mode
from src.rag.prompting import estimate_rag_context_budget_chars, inject_rag_context
from src.rag.service import (
    build_source_metadata,
    clear_persisted_rag_index,
    reset_chroma_persist_directory,
    get_indexed_documents,
    inspect_embedding_configuration_compatibility,
    inspect_vector_backend_status,
    normalize_rag_index,
    remove_documents_from_rag_index,
    retrieve_relevant_chunks_detailed,
    upsert_documents_in_rag_index,
)
from src.services.chat_state import (
    append_chat_message,
    clear_chat_state,
    get_chat_messages,
    get_last_latency,
    initialize_chat_state,
    set_last_latency,
)
from src.services.app_errors import build_ui_error_message
from src.services.app_logging import configure_logging, get_logger
from src.storage.chat_history import clear_chat_history, load_chat_history, save_chat_history
from src.storage.phase55_shadow_log import (
    append_shadow_log_entry,
    clear_shadow_log,
    load_shadow_log,
    summarize_shadow_log,
)
from src.storage.phase55_langgraph_shadow_log import (
    append_langgraph_shadow_log_entry,
    clear_langgraph_shadow_log,
    load_langgraph_shadow_log,
    summarize_langgraph_shadow_log,
)
from src.storage.phase6_document_agent_log import (
    clear_document_agent_log,
    load_document_agent_log,
    summarize_document_agent_log,
)
from src.storage.phase7_model_comparison_log import (
    append_model_comparison_log_entry,
    clear_model_comparison_log,
    load_model_comparison_log,
    summarize_model_comparison_log,
)
from src.storage.phase95_evidenceops_action_store import append_evidenceops_actions_from_worklog_entry
from src.storage.phase95_evidenceops_worklog import append_evidenceops_worklog_entry
from src.storage.phase8_eval_store import load_eval_runs, summarize_eval_runs
from src.storage.runtime_execution_log import (
    append_runtime_execution_log_entry,
    load_runtime_execution_log,
    summarize_runtime_execution_log,
)
from src.storage.rag_store import clear_rag_store, load_rag_store, save_rag_store
from src.storage.runtime_paths import (
    get_phase55_langgraph_shadow_log_path,
    get_phase55_shadow_log_path,
    get_phase6_document_agent_log_path,
    get_phase7_model_comparison_log_path,
    get_phase8_eval_db_path,
    get_phase95_evidenceops_action_store_path,
    get_phase95_evidenceops_worklog_path,
    get_runtime_execution_log_path,
)
from src.services.document_context import build_structured_document_context
from src.services.evidenceops_mcp_client import register_evidenceops_entry_via_mcp
from src.services.evidenceops_worklog import build_evidenceops_worklog_entry
from src.services.model_comparison import (
    MODEL_COMPARISON_FORMAT_OPTIONS,
    MODEL_COMPARISON_RUNTIME_BUCKET_LABELS,
    MODEL_COMPARISON_QUANTIZATION_LABELS,
    MODEL_COMPARISON_USE_CASE_PRESETS,
    run_model_comparison_candidate,
    summarize_model_comparison_results,
)
from src.services.runtime_budgeting import (
    assess_budget_quality_gate,
    build_budget_routing_decision,
    evaluate_budget_alerts,
    resolve_budget_provider_routing,
)
from src.services.runtime_economics import (
    aggregate_provider_call_native_usage,
    count_message_chars,
    estimate_runtime_usage_metrics,
    get_provider_native_usage_metrics,
)
from src.services.rag_state import (
    clear_rag_state,
    get_rag_index,
    initialize_rag_runtime_settings,
    initialize_rag_state,
    set_rag_index,
    set_rag_runtime_settings,
)
from src.services.runtime_snapshot import build_runtime_snapshot
from src.structured.base import DocumentAgentPayload
from src.structured.envelope import StructuredResult, TaskExecutionRequest
from src.structured.langgraph_workflow import (
    describe_structured_execution_strategy,
    run_structured_execution_workflow,
)
from src.structured.parsers import attempt_controlled_failure
from src.structured.registry import build_structured_task_registry
from src.structured.service import structured_service
from src.structured.tasks import (
    SUMMARY_FULL_DOCUMENT_TRIGGER_CHARS,
    SUMMARY_PART_CHUNK_SIZE,
    SUMMARY_PART_OVERLAP,
    build_extraction_execution_preview,
    build_checklist_execution_preview,
)
from src.ui.chat import render_chat_message
from src.ui.evidenceops_mcp_panel import render_evidenceops_mcp_panel
from src.ui.executive_deck_generation import render_executive_deck_generation_panel
from src.ui.sidebar import render_chat_sidebar, render_runtime_sidebar_panel
from src.ui.structured_outputs import render_structured_result


configure_logging()
logger = get_logger(__name__)

app_bootstrap = build_app_bootstrap()
settings = app_bootstrap.settings
rag_settings = app_bootstrap.rag_settings
evidence_config = app_bootstrap.evidence_config
provider_registry = app_bootstrap.provider_registry
prompt_profiles = app_bootstrap.prompt_profiles
structured_task_registry = app_bootstrap.structured_task_registry
presentation_export_settings = get_presentation_export_settings()
embedding_sidebar_state = app_bootstrap.embedding_sidebar_state
embedding_capable_registry = embedding_sidebar_state["available_registry"]
if not embedding_capable_registry:
    raise RuntimeError("Nenhum provider com suporte a embeddings está disponível no ambiente atual.")
embedding_provider_options = embedding_sidebar_state["available_options"]
embedding_models_by_provider = embedding_sidebar_state["available_models_by_provider"]
default_embedding_provider = (
    rag_settings.embedding_provider
    if rag_settings.embedding_provider in embedding_capable_registry
    else next(iter(embedding_capable_registry))
)
default_embedding_model_by_provider = {
    provider_key: (
        rag_settings.embedding_model
        if provider_key == default_embedding_provider and rag_settings.embedding_model
        else (models[0] if models else "")
    )
    for provider_key, models in embedding_models_by_provider.items()
}
STRUCTURED_RESULT_STATE_KEY = "phase5_structured_result"
STRUCTURED_RENDER_MODE_STATE_KEY = "phase5_structured_render_mode"
MODEL_COMPARISON_RESULT_STATE_KEY = "phase7_model_comparison_result"
CHAT_DOCUMENT_SELECTION_STATE_KEY = "phase5_chat_document_ids"
STRUCTURED_DOCUMENT_SELECTION_STATE_KEY = "phase5_structured_document_ids"
EVIDENCEOPS_MCP_LAST_ENTRY_STATE_KEY = "phase95_evidenceops_mcp_last_entry"
EVIDENCEOPS_MCP_LAST_REGISTER_RESULT_STATE_KEY = "phase95_evidenceops_mcp_last_register_result"
EVIDENCEOPS_MCP_LAST_TELEMETRY_STATE_KEY = "phase95_evidenceops_mcp_last_telemetry"
EVIDENCEOPS_MCP_CONSOLE_STATE_KEY = "phase95_evidenceops_mcp_console_state"
PHASE7_DOCUMENT_SELECTION_STATE_KEY = "phase7_model_comparison_document_ids"
PHASE55_SHADOW_LOG_PATH = settings.history_path.parent / ".phase55_langchain_shadow_log.json"
PHASE55_LANGGRAPH_SHADOW_LOG_PATH = settings.history_path.parent / ".phase55_langgraph_shadow_log.json"
PHASE6_DOCUMENT_AGENT_LOG_PATH = settings.history_path.parent / ".phase6_document_agent_log.json"
PHASE95_EVIDENCEOPS_ACTION_STORE_PATH = settings.history_path.parent / ".phase95_evidenceops_actions.sqlite3"
PHASE95_EVIDENCEOPS_WORKLOG_PATH = settings.history_path.parent / ".phase95_evidenceops_worklog.json"
PHASE95_EVIDENCEOPS_REPOSITORY_ROOT = settings.history_path.parent / "data" / "evidenceops_option_b_synthetic"
PHASE95_EVIDENCEOPS_REPOSITORY_SNAPSHOT_PATH = (
    PHASE95_EVIDENCEOPS_REPOSITORY_ROOT / ".phase95_evidenceops_repository_snapshot.json"
)
PHASE7_MODEL_COMPARISON_LOG_PATH = settings.history_path.parent / ".phase7_model_comparison_log.json"
PHASE8_EVAL_DB_PATH = settings.history_path.parent / ".phase8_eval_runs.sqlite3"
RUNTIME_EXECUTION_LOG_PATH = settings.history_path.parent / ".runtime_execution_log.json"
WORKSPACE_ROOT = settings.history_path.parent if settings.history_path.parent.name != "chat" else settings.history_path.parents[3]
PHASE55_SHADOW_LOG_PATH = get_phase55_shadow_log_path(WORKSPACE_ROOT)
PHASE55_LANGGRAPH_SHADOW_LOG_PATH = get_phase55_langgraph_shadow_log_path(WORKSPACE_ROOT)
PHASE6_DOCUMENT_AGENT_LOG_PATH = get_phase6_document_agent_log_path(WORKSPACE_ROOT)
PHASE95_EVIDENCEOPS_ACTION_STORE_PATH = get_phase95_evidenceops_action_store_path(WORKSPACE_ROOT)
PHASE95_EVIDENCEOPS_WORKLOG_PATH = get_phase95_evidenceops_worklog_path(WORKSPACE_ROOT)
PHASE95_EVIDENCEOPS_REPOSITORY_ROOT = WORKSPACE_ROOT / "data" / "evidenceops_option_b_synthetic"
PHASE95_EVIDENCEOPS_REPOSITORY_SNAPSHOT_PATH = (
    PHASE95_EVIDENCEOPS_REPOSITORY_ROOT / ".phase95_evidenceops_repository_snapshot.json"
)
PHASE7_MODEL_COMPARISON_LOG_PATH = get_phase7_model_comparison_log_path(WORKSPACE_ROOT)
PHASE8_EVAL_DB_PATH = get_phase8_eval_db_path(WORKSPACE_ROOT)
RUNTIME_EXECUTION_LOG_PATH = get_runtime_execution_log_path(WORKSPACE_ROOT)

AUTO_CONTEXT_WINDOW_CAP_BY_PROVIDER = {
    "ollama": 256000,
    "openai": 128000,
    "huggingface_local": 32768,
    "huggingface_server": 32768,
}

STRUCTURED_PROGRESS_STEP_DELAY_S = 0.018
STRUCTURED_PROGRESS_FINALIZE_DELAY_S = 0.012


def _estimate_selected_document_chars(
    rag_index: dict[str, object] | None,
    document_ids: list[str],
    *,
    input_text: str = "",
) -> int:
    full_document_text = _build_full_document_text_from_selection(rag_index, document_ids)
    return max(len(full_document_text or ""), len((input_text or "").strip()))


def _resolve_auto_context_window_cap(provider: str, fallback: int) -> int:
    configured = AUTO_CONTEXT_WINDOW_CAP_BY_PROVIDER.get(provider)
    if configured is None:
        return int(fallback)
    return max(int(fallback), int(configured))


def _resolve_chat_context_window(
    *,
    provider: str,
    mode: str,
    manual_context_window: int,
    document_ids: list[str],
    input_text: str,
    rag_index: dict[str, object] | None,
) -> tuple[int, int]:
    if mode != "auto":
        return int(manual_context_window), int(manual_context_window)

    cap = _resolve_auto_context_window_cap(provider, manual_context_window)
    document_chars = _estimate_selected_document_chars(rag_index, document_ids, input_text=input_text)
    prompt_chars = len((input_text or "").strip())

    desired = 12288
    if document_chars >= 180000:
        desired = 49152
    elif document_chars >= 80000:
        desired = 32768
    elif document_chars >= 25000:
        desired = 24576
    elif document_chars >= 6000:
        desired = 16384

    if prompt_chars >= 4000:
        desired = max(desired, 24576)
    elif prompt_chars >= 1500:
        desired = max(desired, 16384)

    resolved = max(4096, min(desired, cap))
    return int(resolved), int(cap)


def _normalize_document_selection(
    available_document_ids: list[str],
    requested_document_ids: list[str] | None,
    *,
    default_to_all: bool = True,
) -> list[str]:
    available = [str(item) for item in available_document_ids if item]
    if not available:
        return []

    available_set = set(available)
    normalized_requested = [
        str(item) for item in (requested_document_ids or []) if str(item) in available_set
    ]
    if normalized_requested:
        return normalized_requested
    return list(available) if default_to_all else []


def _build_document_preview_map(
    rag_index: dict[str, object] | None,
    indexed_documents: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    preview_map: dict[str, dict[str, object]] = {}
    document_by_id = {
        str(document.get("document_id")): document
        for document in indexed_documents
        if document.get("document_id")
    }
    chunks = rag_index.get("chunks", []) if isinstance(rag_index, dict) else []

    for document_id, document in document_by_id.items():
        related_chunks = [
            chunk
            for chunk in chunks
            if isinstance(chunk, dict) and str(chunk.get("document_id") or "") == document_id
        ]
        related_chunks = sorted(
            related_chunks,
            key=lambda chunk: (
                int(chunk.get("chunk_id") or 0),
                int(chunk.get("start_char") or 0),
            ),
        )
        snippet_samples = []
        for chunk in related_chunks[:3]:
            snippet = str(chunk.get("snippet") or chunk.get("text") or "").strip()
            if snippet:
                snippet_samples.append(snippet[:600])

        preview_map[document_id] = {
            "document": document,
            "snippets": snippet_samples,
            "chunks_count": len(related_chunks),
        }

    return preview_map


def _retrieval_chunk_signature(chunk: dict[str, object]) -> tuple[str, int, int, int]:
    return (
        str(chunk.get("document_id") or chunk.get("file_hash") or chunk.get("source") or "documento"),
        int(chunk.get("chunk_id") or 0),
        int(chunk.get("start_char") or 0),
        int(chunk.get("end_char") or 0),
    )


def _build_retrieval_shadow_summary(
    primary_details: dict[str, object] | None,
    alternate_details: dict[str, object] | None,
) -> dict[str, object] | None:
    if not isinstance(primary_details, dict) or not isinstance(alternate_details, dict):
        return None

    primary_chunks = [
        chunk for chunk in (primary_details.get("chunks") or []) if isinstance(chunk, dict)
    ]
    alternate_chunks = [
        chunk for chunk in (alternate_details.get("chunks") or []) if isinstance(chunk, dict)
    ]
    if not primary_chunks and not alternate_chunks:
        return None

    primary_signatures = [_retrieval_chunk_signature(chunk) for chunk in primary_chunks]
    alternate_signatures = [_retrieval_chunk_signature(chunk) for chunk in alternate_chunks]
    primary_set = set(primary_signatures)
    alternate_set = set(alternate_signatures)
    overlap_count = len(primary_set & alternate_set)

    def _chunk_label(chunk: dict[str, object] | None) -> str | None:
        if not isinstance(chunk, dict):
            return None
        source = str(chunk.get("source") or "documento")
        chunk_id = int(chunk.get("chunk_id") or 0)
        score = chunk.get("score")
        return f"{source}#{chunk_id} (score={score})"

    return {
        "primary_strategy": primary_details.get("retrieval_strategy_used") or primary_details.get("retrieval_strategy_requested"),
        "alternate_strategy": alternate_details.get("retrieval_strategy_used") or alternate_details.get("retrieval_strategy_requested"),
        "primary_count": len(primary_chunks),
        "alternate_count": len(alternate_chunks),
        "overlap_count": overlap_count,
        "overlap_ratio": round(overlap_count / max(len(primary_set), 1), 3) if primary_set else 0.0,
        "same_top_1": bool(primary_signatures and alternate_signatures and primary_signatures[0] == alternate_signatures[0]),
        "same_top_3_order": primary_signatures[:3] == alternate_signatures[:3] if primary_signatures and alternate_signatures else False,
        "primary_top_1": _chunk_label(primary_chunks[0]) if primary_chunks else None,
        "alternate_top_1": _chunk_label(alternate_chunks[0]) if alternate_chunks else None,
        "alternate_backend_message": alternate_details.get("backend_message"),
        "alternate_fallback_reason": alternate_details.get("retrieval_strategy_fallback_reason"),
    }


def _build_shadow_log_entry(
    *,
    query: str,
    provider: str,
    model: str,
    document_ids: list[str],
    shadow_summary: dict[str, object],
) -> dict[str, object]:
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "query": (query or "").strip()[:400],
        "provider": provider,
        "model": model,
        "document_ids": list(document_ids),
        **shadow_summary,
    }


def _extract_structured_execution_metrics(result: StructuredResult) -> dict[str, object]:
    metadata = result.execution_metadata if isinstance(result.execution_metadata, dict) else {}
    telemetry = metadata.get("telemetry") if isinstance(metadata.get("telemetry"), dict) else {}
    timings = telemetry.get("timings_s") if isinstance(telemetry.get("timings_s"), dict) else {}
    workflow_total_s = metadata.get("workflow_total_s") if isinstance(metadata.get("workflow_total_s"), (int, float)) else None
    total_s = timings.get("total_s") if isinstance(timings.get("total_s"), (int, float)) else None
    return {
        "strategy_requested": metadata.get("execution_strategy_requested"),
        "strategy_used": metadata.get("execution_strategy_used"),
        "fallback_reason": metadata.get("execution_strategy_fallback_reason"),
        "workflow_id": metadata.get("workflow_id"),
        "route_decision": metadata.get("workflow_route_decision"),
        "guardrail_decision": metadata.get("workflow_guardrail_decision"),
        "needs_review": bool(metadata.get("needs_review")),
        "needs_review_reason": metadata.get("needs_review_reason"),
        "workflow_attempts": int(metadata.get("workflow_attempts") or 0),
        "workflow_context_strategies": list(metadata.get("workflow_context_strategies") or []),
        "workflow_total_s": round(float(workflow_total_s), 4) if workflow_total_s is not None else (round(float(total_s), 4) if total_s is not None else None),
        "quality_score": float(result.quality_score) if isinstance(result.quality_score, (int, float)) else None,
        "success": bool(result.success),
    }


def _build_structured_shadow_summary(
    primary_result: StructuredResult,
    alternate_result: StructuredResult,
) -> dict[str, object]:
    primary = _extract_structured_execution_metrics(primary_result)
    alternate = _extract_structured_execution_metrics(alternate_result)
    primary_quality = primary.get("quality_score")
    alternate_quality = alternate.get("quality_score")
    primary_latency = primary.get("workflow_total_s")
    alternate_latency = alternate.get("workflow_total_s")
    quality_delta = None
    latency_delta_s = None
    if isinstance(primary_quality, (int, float)) and isinstance(alternate_quality, (int, float)):
        quality_delta = round(float(alternate_quality) - float(primary_quality), 3)
    if isinstance(primary_latency, (int, float)) and isinstance(alternate_latency, (int, float)):
        latency_delta_s = round(float(alternate_latency) - float(primary_latency), 3)

    alternate_better_quality = bool(quality_delta is not None and quality_delta > 0.01)
    primary_better_quality = bool(quality_delta is not None and quality_delta < -0.01)
    alternate_faster = bool(latency_delta_s is not None and latency_delta_s < -0.05)
    primary_faster = bool(latency_delta_s is not None and latency_delta_s > 0.05)

    return {
        "primary_strategy_requested": primary.get("strategy_requested"),
        "primary_strategy_used": primary.get("strategy_used"),
        "alternate_strategy_requested": alternate.get("strategy_requested"),
        "alternate_strategy_used": alternate.get("strategy_used"),
        "primary_success": primary.get("success"),
        "alternate_success": alternate.get("success"),
        "same_success": primary.get("success") == alternate.get("success"),
        "primary_quality_score": primary_quality,
        "alternate_quality_score": alternate_quality,
        "quality_delta": quality_delta,
        "alternate_better_quality": alternate_better_quality,
        "primary_better_quality": primary_better_quality,
        "primary_workflow_total_s": primary_latency,
        "alternate_workflow_total_s": alternate_latency,
        "latency_delta_s": latency_delta_s,
        "alternate_faster": alternate_faster,
        "primary_faster": primary_faster,
        "primary_workflow_attempts": primary.get("workflow_attempts"),
        "alternate_workflow_attempts": alternate.get("workflow_attempts"),
        "primary_needs_review": primary.get("needs_review"),
        "alternate_needs_review": alternate.get("needs_review"),
        "same_needs_review": primary.get("needs_review") == alternate.get("needs_review"),
        "alternate_avoided_review": bool(primary.get("needs_review") and not alternate.get("needs_review")),
        "primary_route_decision": primary.get("route_decision"),
        "alternate_route_decision": alternate.get("route_decision"),
        "primary_guardrail_decision": primary.get("guardrail_decision"),
        "alternate_guardrail_decision": alternate.get("guardrail_decision"),
        "alternate_fallback_reason": alternate.get("fallback_reason"),
    }


def _build_structured_shadow_log_entry(
    *,
    task_type: str,
    query: str,
    provider: str,
    model: str,
    document_ids: list[str],
    shadow_summary: dict[str, object],
) -> dict[str, object]:
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task_type": task_type,
        "query": (query or "").strip()[:400],
        "provider": provider,
        "model": model,
        "document_ids": list(document_ids),
        **shadow_summary,
    }


def _build_document_agent_log_entry(
    *,
    result: StructuredResult,
    query: str,
    provider: str,
    model: str,
    document_ids: list[str],
) -> dict[str, object]:
    metadata = result.execution_metadata if isinstance(result.execution_metadata, dict) else {}
    payload = result.validated_output
    tool_runs = list(getattr(payload, "tool_runs", []) or [])
    tool_status_counts: dict[str, int] = {}
    for item in tool_runs:
        status = str(getattr(item, "status", "") or "").strip().lower()
        if not status:
            continue
        tool_status_counts[status] = int(tool_status_counts.get(status, 0)) + 1

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "query": (query or "").strip()[:400],
        "provider": provider,
        "model": model,
        "document_ids": list(document_ids),
        "success": bool(result.success),
        "execution_strategy_used": metadata.get("execution_strategy_used"),
        "workflow_id": metadata.get("workflow_id"),
        "workflow_attempts": metadata.get("workflow_attempts"),
        "user_intent": getattr(payload, "user_intent", None) or metadata.get("agent_intent"),
        "tool_used": getattr(payload, "tool_used", None) or metadata.get("agent_tool"),
        "answer_mode": getattr(payload, "answer_mode", None) or metadata.get("agent_answer_mode"),
        "confidence": getattr(payload, "confidence", None) if payload is not None else result.quality_score,
        "needs_review": getattr(payload, "needs_review", None) if payload is not None else metadata.get("needs_review"),
        "needs_review_reason": getattr(payload, "needs_review_reason", None) if payload is not None else metadata.get("needs_review_reason"),
        "source_count": len(getattr(payload, "sources", []) or []),
        "available_tools_count": len(getattr(payload, "available_tools", []) or []),
        "successful_tool_runs": tool_status_counts.get("success", 0),
        "error_tool_runs": tool_status_counts.get("error", 0),
        "tool_status_counts": tool_status_counts,
        "limitations_count": len(getattr(payload, "limitations", []) or []),
        "recommended_actions_count": len(getattr(payload, "recommended_actions", []) or []),
        "guardrails_count": len(getattr(payload, "guardrails_applied", []) or []),
        "compared_documents_count": len(getattr(payload, "compared_documents", []) or []),
    }


def _build_model_comparison_candidate_option(provider_key: str, model_name: str) -> str:
    return f"{provider_key}::{model_name}"


def _parse_model_comparison_candidate_option(option: str) -> tuple[str, str]:
    provider_key, _, model_name = str(option or "").partition("::")
    return provider_key.strip(), model_name.strip()


def _format_model_comparison_candidate_option(option: str, provider_labels: dict[str, str]) -> str:
    provider_key, model_name = _parse_model_comparison_candidate_option(option)
    provider_label = provider_labels.get(provider_key, provider_key)
    return f"{provider_label} · {model_name}"


def _build_model_comparison_log_entry(
    *,
    prompt_text: str,
    benchmark_use_case: str,
    prompt_profile: str,
    response_format: str,
    retrieval_strategy: str,
    embedding_provider: str,
    embedding_model: str,
    embedding_context_window: int,
    context_window_mode: str,
    context_window_resolved: int,
    use_documents: bool,
    document_ids: list[str],
    candidate_results: list[dict[str, object]],
    aggregate: dict[str, object],
) -> dict[str, object]:
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "prompt_text": (prompt_text or "").strip()[:400],
        "benchmark_use_case": benchmark_use_case,
        "prompt_profile": prompt_profile,
        "response_format": response_format,
        "retrieval_strategy": retrieval_strategy,
        "embedding_provider": embedding_provider,
        "embedding_model": embedding_model,
        "embedding_context_window": int(embedding_context_window),
        "context_window_mode": context_window_mode,
        "context_window_resolved": int(context_window_resolved),
        "use_documents": bool(use_documents),
        "document_ids": list(document_ids),
        "candidate_results": candidate_results,
        "aggregate": aggregate,
    }


def _build_runtime_execution_log_entry(
    *,
    flow_type: str,
    task_type: str,
    provider: str,
    model: str,
    success: bool,
    latency_s: float | None = None,
    retrieval_latency_s: float | None = None,
    generation_latency_s: float | None = None,
    prompt_build_latency_s: float | None = None,
    context_window: int | None = None,
    context_window_mode: str | None = None,
    embedding_provider: str | None = None,
    embedding_model: str | None = None,
    retrieval_strategy_requested: str | None = None,
    retrieval_strategy_used: str | None = None,
    retrieval_backend_used: str | None = None,
    rag_chunk_size: int | None = None,
    rag_chunk_overlap: int | None = None,
    rag_top_k: int | None = None,
    prompt_chars: int | None = None,
    output_chars: int | None = None,
    context_chars: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    usage_source: str | None = None,
    cost_usd: float | None = None,
    cost_source: str | None = None,
    source_document_ids: list[str] | None = None,
    retrieved_chunks_count: int | None = None,
    needs_review: bool | None = None,
    error_message: str | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    entry: dict[str, object] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "flow_type": flow_type,
        "task_type": task_type,
        "provider": provider,
        "model": model,
        "success": bool(success),
        "source_document_ids": list(source_document_ids or []),
        "selected_documents": len(source_document_ids or []),
    }
    if latency_s is not None:
        entry["latency_s"] = round(float(latency_s), 4)
    if retrieval_latency_s is not None:
        entry["retrieval_latency_s"] = round(float(retrieval_latency_s), 4)
    if generation_latency_s is not None:
        entry["generation_latency_s"] = round(float(generation_latency_s), 4)
    if prompt_build_latency_s is not None:
        entry["prompt_build_latency_s"] = round(float(prompt_build_latency_s), 4)
    if context_window is not None:
        entry["context_window"] = int(context_window)
    if context_window_mode:
        entry["context_window_mode"] = context_window_mode
    if embedding_provider:
        entry["embedding_provider"] = embedding_provider
    if embedding_model:
        entry["embedding_model"] = embedding_model
    if retrieval_strategy_requested:
        entry["retrieval_strategy_requested"] = retrieval_strategy_requested
    if retrieval_strategy_used:
        entry["retrieval_strategy_used"] = retrieval_strategy_used
    if retrieval_backend_used:
        entry["retrieval_backend_used"] = retrieval_backend_used
    if rag_chunk_size is not None:
        entry["rag_chunk_size"] = int(rag_chunk_size)
    if rag_chunk_overlap is not None:
        entry["rag_chunk_overlap"] = int(rag_chunk_overlap)
    if rag_top_k is not None:
        entry["rag_top_k"] = int(rag_top_k)
    if prompt_chars is not None:
        entry["prompt_chars"] = int(prompt_chars)
    if output_chars is not None:
        entry["output_chars"] = int(output_chars)
    if context_chars is not None:
        entry["context_chars"] = int(context_chars)
    if prompt_tokens is not None:
        entry["prompt_tokens"] = int(prompt_tokens)
    if completion_tokens is not None:
        entry["completion_tokens"] = int(completion_tokens)
    if total_tokens is not None:
        entry["total_tokens"] = int(total_tokens)
    if usage_source:
        entry["usage_source"] = usage_source
    if cost_usd is not None:
        entry["cost_usd"] = round(float(cost_usd), 6)
    if cost_source:
        entry["cost_source"] = cost_source
    if retrieved_chunks_count is not None:
        entry["retrieved_chunks_count"] = int(retrieved_chunks_count)
    if needs_review is not None:
        entry["needs_review"] = bool(needs_review)
    if error_message:
        entry["error_message"] = error_message
    if isinstance(extra, dict):
        entry.update(extra)
    return entry


def _build_document_runtime_signal_summary(
    document_ids: list[str],
    document_preview_map: dict[str, dict[str, object]],
) -> dict[str, object]:
    selected_ids = [str(document_id) for document_id in document_ids if str(document_id or "").strip()]
    if not selected_ids:
        return {
            "evidence_pipeline_document_count": 0,
            "ocr_document_count": 0,
            "docling_document_count": 0,
            "vl_document_count": 0,
            "suspicious_pages_total": 0,
            "docling_pages_total": 0,
            "vl_regions_attempted_total": 0,
            "vl_regions_succeeded_total": 0,
            "ocr_backend_counts": {},
        }

    evidence_pipeline_document_count = 0
    ocr_document_count = 0
    docling_document_count = 0
    vl_document_count = 0
    suspicious_pages_total = 0
    docling_pages_total = 0
    vl_regions_attempted_total = 0
    vl_regions_succeeded_total = 0
    ocr_backend_counts: dict[str, int] = {}

    for document_id in selected_ids:
        preview = document_preview_map.get(document_id) or {}
        document = preview.get("document") if isinstance(preview, dict) else {}
        if not isinstance(document, dict):
            continue
        loader_metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
        if not isinstance(loader_metadata, dict):
            continue
        if bool(loader_metadata.get("evidence_pipeline_used")):
            evidence_pipeline_document_count += 1
        if bool(loader_metadata.get("ocr_fallback_applied") or loader_metadata.get("ocr_fallback_attempted")):
            ocr_document_count += 1
        docling_mode = str(loader_metadata.get("docling_mode") or "").strip().lower()
        docling_pages_used = loader_metadata.get("docling_pages_used") if isinstance(loader_metadata.get("docling_pages_used"), list) else []
        suspicious_pages = loader_metadata.get("suspicious_pages") if isinstance(loader_metadata.get("suspicious_pages"), list) else []
        if (docling_mode and docling_mode != "none") or docling_pages_used:
            docling_document_count += 1
        suspicious_pages_total += len(suspicious_pages)
        docling_pages_total += len(docling_pages_used)
        ocr_backend = str(loader_metadata.get("ocr_backend") or "").strip()
        if ocr_backend:
            ocr_backend_counts[ocr_backend] = int(ocr_backend_counts.get(ocr_backend, 0)) + 1

        vl_runtime = loader_metadata.get("vl_runtime") if isinstance(loader_metadata.get("vl_runtime"), dict) else {}
        vl_regions_attempted = int(vl_runtime.get("regions_attempted") or 0) if isinstance(vl_runtime.get("regions_attempted"), (int, float)) else 0
        vl_regions_succeeded = int(vl_runtime.get("regions_succeeded") or 0) if isinstance(vl_runtime.get("regions_succeeded"), (int, float)) else 0
        vl_fallback_used = bool(vl_runtime.get("fallback_used"))
        if vl_regions_attempted > 0 or vl_regions_succeeded > 0 or vl_fallback_used:
            vl_document_count += 1
        vl_regions_attempted_total += vl_regions_attempted
        vl_regions_succeeded_total += vl_regions_succeeded

    return {
        "evidence_pipeline_document_count": evidence_pipeline_document_count,
        "ocr_document_count": ocr_document_count,
        "docling_document_count": docling_document_count,
        "vl_document_count": vl_document_count,
        "suspicious_pages_total": suspicious_pages_total,
        "docling_pages_total": docling_pages_total,
        "vl_regions_attempted_total": vl_regions_attempted_total,
        "vl_regions_succeeded_total": vl_regions_succeeded_total,
        "ocr_backend_counts": ocr_backend_counts,
    }


def _build_full_document_text_from_selection(
    rag_index: dict[str, object] | None,
    document_ids: list[str],
) -> str:
    if not isinstance(rag_index, dict) or not document_ids:
        return ""
    allowed = {str(item) for item in document_ids if item}
    chunks = [
        chunk
        for chunk in rag_index.get("chunks", [])
        if isinstance(chunk, dict)
        and str(chunk.get("document_id") or chunk.get("file_hash") or "") in allowed
    ]
    ordered_chunks = sorted(
        chunks,
        key=lambda chunk: (
            str(chunk.get("document_id") or chunk.get("file_hash") or "document"),
            int(chunk.get("chunk_id") or 0),
            int(chunk.get("start_char") or 0),
        ),
    )
    parts = [str(chunk.get("text") or "").strip() for chunk in ordered_chunks if str(chunk.get("text") or "").strip()]
    return "\n\n".join(parts).strip()


def _split_text_for_summary_preview(
    text: str,
    chunk_size: int = SUMMARY_PART_CHUNK_SIZE,
    overlap: int = SUMMARY_PART_OVERLAP,
) -> list[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start += step
    return chunks


def _estimate_summary_next_execution_preview(
    *,
    rag_index: dict[str, object] | None,
    document_ids: list[str],
    input_text: str,
    context_strategy: str,
) -> dict[str, object]:
    full_document_text = _build_full_document_text_from_selection(rag_index, document_ids)
    if full_document_text and len(full_document_text) > SUMMARY_FULL_DOCUMENT_TRIGGER_CHARS:
        parts = _split_text_for_summary_preview(full_document_text)
        stages = [
            {
                "stage_type": "map",
                "label": f"Part {index} of {len(parts)}",
                "chars_sent": len(part),
                "context_preview": part[:6000],
                "prompt_preview": (
                    f"User intent / task:\n{input_text}\n\nDocument part:\n{part[:5000]}"
                ),
            }
            for index, part in enumerate(parts, start=1)
        ]
        reduce_preview = "\n\n".join(
            f"[PARTIAL SUMMARY {index}]\nExecutive summary: ...\nKey insights: ...\nTopics: ..."
            for index in range(1, len(parts) + 1)
        )[:6000]
        stages.append(
            {
                "stage_type": "reduce",
                "label": "Final synthesis",
                "chars_sent": len(reduce_preview),
                "context_preview": reduce_preview,
                "prompt_preview": f"User intent / task:\n{input_text}\n\nPartial summaries from the full document:\n{reduce_preview}",
            }
        )
        return {
            "summary_mode": "full_document_map_reduce",
            "full_document_chars": len(full_document_text),
            "document_parts": len(parts),
            "stages": stages,
        }

    preview_context = build_structured_document_context(
        query=input_text,
        document_ids=document_ids,
        strategy=context_strategy,
    )
    return {
        "summary_mode": "single_pass_context",
        "full_document_chars": len(full_document_text or ""),
        "context_chars_sent": len(preview_context),
        "context_strategy": context_strategy,
        "stages": [
            {
                "stage_type": "single_pass",
                "label": f"Single-pass summary ({context_strategy})",
                "chars_sent": len(preview_context),
                "context_preview": preview_context[:6000],
                "prompt_preview": f"Text to summarize:\n{input_text}\n\nContext:\n{preview_context[:5000]}",
            }
        ],
    }


def _resolve_structured_context_strategy(
    *,
    task_type: str,
    input_text: str,
    use_documents: bool,
    selected_document_ids: list[str],
) -> tuple[str, str]:
    """Choose document_scan vs retrieval automatically based on task and user input."""
    if not use_documents or not selected_document_ids:
        return "document_scan", "Sem documentos selecionados; estratégia interna padrão aplicada."

    normalized_input = (input_text or "").strip()
    has_meaningful_query = len(normalized_input) >= 24

    coverage_first_tasks = {"checklist", "extraction", "cv_analysis", "code_analysis"}
    mixed_tasks = {"summary"}
    agent_tasks = {"document_agent"}

    if task_type in coverage_first_tasks:
        if has_meaningful_query and task_type == "code_analysis":
            return "retrieval", "Estratégia automática: retrieval, porque há instrução textual específica para análise de código."
        return "document_scan", "Estratégia automática: document_scan, porque esta task prioriza cobertura estrutural do documento."

    if task_type in mixed_tasks:
        if has_meaningful_query:
            return "retrieval", "Estratégia automática: retrieval, porque há texto suficiente para orientar a busca dos trechos mais relevantes."
        return "document_scan", "Estratégia automática: document_scan, porque não há consulta forte no campo de texto e a task precisa cobrir melhor o documento."

    if task_type in agent_tasks:
        if has_meaningful_query:
            return "retrieval", "Estratégia automática inicial do agente: retrieval, porque há uma pergunta/instrução específica para orientar a grounding."
        return "document_scan", "Estratégia automática inicial do agente: document_scan, porque a intenção ainda depende de cobertura mais ampla do documento."

    return "document_scan", "Estratégia automática padrão: document_scan."


def _format_structured_progress_label(task_type: str, step: str, detail: str) -> str:
    if detail:
        return detail

    labels_by_task = {
        "checklist": {
            "initializing": "Iniciando checklist",
            "loading_document": "Carregando documento",
            "document_ready": "Preparando texto operacional",
            "preparing_document": "Preparando documento completo",
            "map_reduce_setup": "Dividindo checklist em partes",
            "map": "Processando parte do checklist",
            "reduce_prep": "Preparando consolidação final",
            "reduce": "Consolidando checklist",
            "building_context": "Montando contexto",
            "prompt_ready": "Montando prompt do checklist",
            "model_inference": "Gerando checklist no modelo",
            "parsing": "Validando checklist",
            "done": "Checklist finalizado",
        },
        "summary": {
            "initializing": "Iniciando resumo",
            "preparing_document": "Preparando documento",
            "provider_ready": "Provider pronto",
            "map_reduce_setup": "Dividindo documento em partes",
            "map": "Processando parte do resumo",
            "reduce": "Consolidando resumo",
            "building_context": "Montando contexto",
            "model_inference": "Gerando resumo no modelo",
            "parsing": "Validando resumo",
            "done": "Resumo finalizado",
        },
        "extraction": {
            "initializing": "Iniciando extração",
            "building_context": "Montando contexto",
            "provider_ready": "Provider pronto",
            "prompt_ready": "Montando prompt da extração",
            "model_inference": "Executando extração",
            "parsing": "Validando extração",
            "done": "Extração finalizada",
        },
        "cv_analysis": {
            "initializing": "Iniciando análise de CV",
            "grounding": "Preparando grounding",
            "provider_ready": "Provider pronto",
            "prompt_ready": "Montando prompt da análise",
            "model_inference": "Executando análise de CV",
            "parsing": "Validando análise de CV",
            "done": "Análise de CV finalizada",
        },
        "code_analysis": {
            "initializing": "Iniciando análise de código",
            "building_context": "Montando contexto",
            "provider_ready": "Provider pronto",
            "prompt_ready": "Montando prompt da análise",
            "model_inference": "Executando análise de código",
            "parsing": "Validando análise",
            "done": "Análise de código finalizada",
        },
        "document_agent": {
            "initializing": "Iniciando copiloto documental",
            "intent_routing": "Classificando intenção",
            "grounding": "Montando grounding documental",
            "tool_execution": "Executando tool do agente",
            "done": "Copiloto documental finalizado",
        },
    }

    return labels_by_task.get(task_type, {}).get(step, step.replace("_", " ").capitalize())

raw_rag_store = load_rag_store(rag_settings.store_path)
normalized_rag_store = normalize_rag_index(raw_rag_store, rag_settings)

if raw_rag_store and normalized_rag_store and (
    raw_rag_store.get("document") is not None
    or raw_rag_store.get("updated_at") is None
    or raw_rag_store.get("documents") is None
):
    save_rag_store(rag_settings.store_path, normalized_rag_store)

if "lista_mensagens" not in st.session_state:
    initialize_chat_state(load_chat_history(settings.history_path))
else:
    initialize_chat_state()

if "rag_index" not in st.session_state:
    initialize_rag_state(normalized_rag_store)
else:
    initialize_rag_state()
initialize_rag_runtime_settings(rag_settings)

messages = get_chat_messages()
last_latency = get_last_latency()
rag_index = get_rag_index()
indexed_documents_preview = get_indexed_documents(rag_index, rag_settings)
indexed_chunks_preview = len(rag_index.get("chunks", [])) if isinstance(rag_index, dict) else 0
vector_backend_status_preview = inspect_vector_backend_status(rag_index, rag_settings)
phase55_shadow_log_entries = load_shadow_log(PHASE55_SHADOW_LOG_PATH)
phase55_shadow_log_summary = summarize_shadow_log(phase55_shadow_log_entries)
phase55_langgraph_shadow_log_entries = load_langgraph_shadow_log(PHASE55_LANGGRAPH_SHADOW_LOG_PATH)
phase55_langgraph_shadow_log_summary = summarize_langgraph_shadow_log(phase55_langgraph_shadow_log_entries)
phase6_document_agent_log_entries = load_document_agent_log(PHASE6_DOCUMENT_AGENT_LOG_PATH)
phase6_document_agent_log_summary = summarize_document_agent_log(phase6_document_agent_log_entries)
phase7_model_comparison_log_entries = load_model_comparison_log(PHASE7_MODEL_COMPARISON_LOG_PATH)
phase7_model_comparison_log_summary = summarize_model_comparison_log(phase7_model_comparison_log_entries)
phase8_eval_entries = load_eval_runs(PHASE8_EVAL_DB_PATH, limit=200)
phase8_eval_summary = summarize_eval_runs(phase8_eval_entries)
runtime_execution_entries = load_runtime_execution_log(RUNTIME_EXECUTION_LOG_PATH)
runtime_execution_summary = summarize_runtime_execution_log(runtime_execution_entries)

chat_capable_registry = filter_registry_by_capability(provider_registry, "chat")
embedding_provider_unavailable_items = embedding_sidebar_state["unavailable_items"]

provider_options = {
    provider_key: provider_data["label"]
    for provider_key, provider_data in chat_capable_registry.items()
}
models_by_provider = {
    provider_key: provider_data["instance"].list_available_models()
    for provider_key, provider_data in chat_capable_registry.items()
}
default_model_by_provider = {
    provider_key: str(provider_data.get("default_model") or (provider_data["instance"].list_available_models()[0] if provider_data["instance"].list_available_models() else ""))
    for provider_key, provider_data in chat_capable_registry.items()
}
provider_details = {
    provider_key: provider_data.get("detail", "")
    for provider_key, provider_data in chat_capable_registry.items()
}
default_context_window_by_provider = {
    provider_key: int(provider_data.get("default_context_window") or settings.default_context_window)
    for provider_key, provider_data in chat_capable_registry.items()
}

(
    selected_provider,
    selected_model,
    selected_prompt_profile,
    temperature,
    context_window_mode,
    context_window,
    rag_chunk_size,
    rag_chunk_overlap,
    rag_top_k,
    selected_rerank_pool_size,
    selected_rerank_lexical_weight,
    selected_embedding_provider,
    selected_embedding_model,
    selected_embedding_truncate,
    selected_embedding_context_window,
    selected_loader_strategy,
    selected_chunking_strategy,
    selected_retrieval_strategy,
    selected_pdf_extraction_mode,
    selected_ocr_backend,
    selected_vl_model,
    clear_requested,
    debug_retrieval,
) = render_chat_sidebar(
    provider_options=provider_options,
    default_provider="ollama",
    models_by_provider=models_by_provider,
    default_model_by_provider=default_model_by_provider,
    prompt_profiles=prompt_profiles,
    default_prompt_profile=settings.default_prompt_profile,
    default_temperature=settings.default_temperature,
    default_context_window_by_provider=default_context_window_by_provider,
    default_rag_chunk_size=rag_settings.chunk_size,
    default_rag_chunk_overlap=rag_settings.chunk_overlap,
    default_rag_top_k=rag_settings.top_k,
    default_rag_loader_strategy=rag_settings.loader_strategy,
    default_rag_chunking_strategy=rag_settings.chunking_strategy,
    default_rag_retrieval_strategy=rag_settings.retrieval_strategy,
    default_pdf_extraction_mode=normalize_pdf_extraction_mode(rag_settings.pdf_extraction_mode),
    embedding_provider_options=embedding_provider_options,
    default_embedding_provider=default_embedding_provider,
    embedding_models_by_provider=embedding_models_by_provider,
    default_embedding_model_by_provider=default_embedding_model_by_provider,
    default_embedding_context_window=rag_settings.embedding_context_window,
    default_embedding_truncate=rag_settings.embedding_truncate,
    indexed_documents_count=len(indexed_documents_preview),
    indexed_chunks_count=indexed_chunks_preview,
    default_rerank_pool_size=rag_settings.rerank_pool_size,
    default_rerank_lexical_weight=rag_settings.rerank_lexical_weight,
    default_vl_model=evidence_config.vl_model,
    default_ocr_backend=evidence_config.ocr_backend,
    embedding_provider_unavailable_items=embedding_provider_unavailable_items,
    provider_details=provider_details,
    history_filename=settings.history_path.name,
    messages_count=len(messages),
    last_latency=last_latency,
)

embedding_runtime_profile = resolve_provider_runtime_profile(
    provider_registry,
    selected_embedding_provider,
    capability="embeddings",
    fallback_provider="ollama",
)
embedding_provider_key = embedding_runtime_profile.get("effective_provider")
embedding_provider_entry = embedding_runtime_profile.get("provider_entry")
embedding_provider_fallback_reason = embedding_runtime_profile.get("fallback_reason")
if not isinstance(embedding_provider_entry, dict):
    raise RuntimeError("Nenhum provider com suporte a embeddings está disponível no ambiente atual.")
embedding_provider = embedding_provider_entry["instance"]
embedding_provider_label = str(embedding_provider_entry.get("label") or embedding_provider_key or "embedding")

effective_rag_settings = replace(
    rag_settings,
    loader_strategy=selected_loader_strategy,
    embedding_provider=str(embedding_provider_key or selected_embedding_provider),
    embedding_model=selected_embedding_model,
    embedding_context_window=selected_embedding_context_window,
    embedding_truncate=bool(selected_embedding_truncate),
    chunk_size=rag_chunk_size,
    chunk_overlap=min(rag_chunk_overlap, rag_chunk_size // 2),
    top_k=rag_top_k,
    rerank_pool_size=max(selected_rerank_pool_size, rag_top_k),
    rerank_lexical_weight=selected_rerank_lexical_weight,
    chunking_strategy=selected_chunking_strategy,
    retrieval_strategy=selected_retrieval_strategy,
    pdf_extraction_mode=normalize_pdf_extraction_mode(selected_pdf_extraction_mode),
    evidence_vl_model=selected_vl_model,
    evidence_ocr_backend=selected_ocr_backend,
)
set_rag_runtime_settings(effective_rag_settings)
evidence_config = build_evidence_config_from_rag_settings(effective_rag_settings)

selected_provider_instance = chat_capable_registry[selected_provider]["instance"]
selected_provider_label = chat_capable_registry[selected_provider]["label"]
selected_prompt_profile_label = prompt_profiles[selected_prompt_profile]["label"]
selected_file_types_count = 0
estimated_rag_context_chars = effective_rag_settings.chunk_size * max(effective_rag_settings.top_k, 1)
rag_context_budget_chars = estimate_rag_context_budget_chars(context_window, effective_rag_settings)
context_usage_ratio = estimated_rag_context_chars / max(rag_context_budget_chars, 1)

if clear_requested:
    clear_chat_state()
    clear_chat_history(settings.history_path)
    st.rerun()

st.write(f"# {settings.project_name} — AI Lab")
st.caption(
    f"AI Lab runtime: provider=`{selected_provider}` · model=`{selected_model}` · prompt_profile=`{selected_prompt_profile}` · temperature=`{temperature:.1f}` · context ({context_window_mode})=`{context_window}``"
)
st.caption(
    "Esta superfície concentra benchmark, evals, observabilidade, MCP e inspeção técnica. Os workflows de produto passam a viver na UI em Gradio."
)
st.caption(
    f"Embedding: provider={effective_rag_settings.embedding_provider} · model={effective_rag_settings.embedding_model} · embedding_num_ctx={effective_rag_settings.embedding_context_window} · truncate={effective_rag_settings.embedding_truncate}"
)
if embedding_provider_fallback_reason:
    st.caption(
        f"Embedding provider efetivo: `{embedding_provider_key}` ({embedding_provider_label}) · fallback_reason=`{embedding_provider_fallback_reason}`"
    )
st.caption(
    f"RAG de teste: chunk_size={effective_rag_settings.chunk_size} · overlap={effective_rag_settings.chunk_overlap} · top_k={effective_rag_settings.top_k} · rerank_pool={effective_rag_settings.rerank_pool_size} · lexical_weight={effective_rag_settings.rerank_lexical_weight:.2f}"
)
st.caption(f"Loader nesta execução: {describe_loader_strategy(selected_loader_strategy)}")
st.caption(f"Chunking nesta execução: {selected_chunking_strategy}")
st.caption(f"Retrieval nesta execução: {selected_retrieval_strategy}")
st.caption(f"Extração PDF nesta execução: {describe_pdf_extraction_mode(effective_rag_settings.pdf_extraction_mode)}")
st.caption(f"OCR documental nesta execução: {effective_rag_settings.evidence_ocr_backend}")
st.caption(f"VLM documental nesta execução: {effective_rag_settings.evidence_vl_model}")
st.caption(
    "Backend vetorial: "
    f"status={vector_backend_status_preview.get('status')} · "
    f"json_chunks={vector_backend_status_preview.get('json_chunks')} · "
    f"chroma_chunks={vector_backend_status_preview.get('chroma_chunks')}"
)
st.caption(
    f"Persistência Chroma: `{vector_backend_status_preview.get('persist_dir')}` · existe_em_disco={vector_backend_status_preview.get('persist_dir_exists')}"
)
if vector_backend_status_preview.get("status") == "dessincronizado":
    st.warning(vector_backend_status_preview.get("message"))
elif vector_backend_status_preview.get("status") == "fallback_local":
    st.info(vector_backend_status_preview.get("message"))

if hasattr(selected_provider_instance, "inspect_context_window"):
    with st.expander(f"Validação de contexto do provider ({selected_provider_label})", expanded=False):
        context_validation = selected_provider_instance.inspect_context_window(
            model=selected_model,
            requested_context_window=context_window,
        )
        st.write(context_validation)
        if selected_provider == "ollama":
            st.caption(
                "Esta validação combina rota nativa `/api/chat`, leitura de `/api/show` e `ollama ps`. "
                "Use `ollama ps` apenas como sinal auxiliar, não como prova isolada."
            )
    with st.expander(f"Validação do provider de embedding ({embedding_provider_label})", expanded=False):
        embedding_context_validation = embedding_provider.inspect_embedding_context_window(
            model=effective_rag_settings.embedding_model,
            requested_context_window=effective_rag_settings.embedding_context_window,
        )
        st.write(embedding_context_validation)
        st.caption(
            "O app registra a configuração operacional do pipeline de embedding e delega ao provider ativo a aplicação efetiva desses parâmetros."
        )

st.divider()
overview_tab, documents_tab, chat_tab, structured_tab, comparison_tab, evals_tab, evidenceops_tab = st.tabs(
    [
        "🧭 Lab Overview",
        "📡 Runtime & Observability",
        "💬 Document / Chat Experiments",
        "🧠 Workflow Inspector & Structured",
        "⚖️ Benchmarks & Model Comparison",
        "📈 Evals & Diagnosis",
        "🧾 EvidenceOps / MCP",
    ]
)

with overview_tab:
    st.caption("1. Visão consolidada do AI Lab com benchmark, evals, runtime, tracing e estado operacional recente.")
    st.info(
        "Esta home do AI Lab resume o estado do sistema enquanto o produto em Gradio concentra os workflows de negócio. "
        "Use as guias abaixo para inspecionar benchmark/evals, runtime economics, workflow traces e operações EvidenceOps."
    )

    overview_col_1, overview_col_2, overview_col_3, overview_col_4 = st.columns(4)
    overview_col_1.metric("Benchmark runs", int(phase7_model_comparison_log_summary.get("total_runs") or 0))
    overview_col_2.metric("Eval PASS rate", f"{float(phase8_eval_summary.get('pass_rate') or 0.0):.0%}")
    overview_col_3.metric("Runtime runs", int(runtime_execution_summary.get("total_runs") or 0))
    overview_col_4.metric("Doc-agent runs", int(phase6_document_agent_log_summary.get("total_runs") or 0))

    overview_col_5, overview_col_6, overview_col_7, overview_col_8 = st.columns(4)
    overview_col_5.metric("Needs review", f"{float(runtime_execution_summary.get('needs_review_rate') or 0.0):.0%}")
    overview_col_6.metric("Avg runtime latency", f"{float(runtime_execution_summary.get('avg_latency_s') or 0.0):.2f}s")
    overview_col_7.metric("Indexed docs", len(indexed_documents_preview))
    overview_col_8.metric("Vector backend", str(vector_backend_status_preview.get("backend") or "n/a"))

    st.markdown("### Navigation map")
    st.write(
        {
            "Lab Overview": "Resumo executivo do AI Lab.",
            "Runtime & Observability": "Base documental, ingestão, indexação e sinais operacionais do runtime.",
            "Document / Chat Experiments": "Chat com RAG tratado como superfície experimental/diagnóstica, não como homepage do produto.",
            "Workflow Inspector & Structured": "Structured outputs, workflow traces e inspeção do Document Operations Copilot.",
            "Benchmarks & Model Comparison": "Benchmark de modelos/providers, estratégia e executive deck de benchmark/evals.",
            "Evals & Diagnosis": "Pass/warn/fail trends, suites e sinais de quality gate.",
            "EvidenceOps / MCP": "Console operacional de MCP, worklogs e actions.",
        }
    )

    suite_leaderboard_preview = phase8_eval_summary.get("suite_leaderboard") if isinstance(phase8_eval_summary.get("suite_leaderboard"), list) else []
    if suite_leaderboard_preview:
        st.markdown("### Current eval leadership")
        st.dataframe(suite_leaderboard_preview[:5], width="stretch")

    if runtime_execution_summary.get("flow_counts"):
        st.markdown("### Runtime flow distribution")
        st.write(
            {
                "flow_counts": runtime_execution_summary.get("flow_counts"),
                "task_counts": runtime_execution_summary.get("task_counts"),
                "provider_counts": runtime_execution_summary.get("provider_counts"),
            }
        )

with documents_tab:
    st.caption("2. Runtime & Observability: ingestão, indexação e manutenção da base documental compartilhada usada pelos módulos experimentais do AI Lab.")
    st.info(
        "O processamento de PDF, OCR e fallback para documentos escaneados acontece na etapa de indexação. "
        "Depois disso, as outras guias trabalham apenas sobre os documentos já indexados e selecionados pelo usuário, evitando conflito entre leitura OCR e uso do RAG em tempo de consulta."
    )
    st.divider()
    st.subheader("Documentos (Fase 4.5 — base documental)")
    uploaded_files = st.file_uploader(
        "Envie um ou mais documentos para indexar",
        type=["pdf", "txt", "csv", "md", "py"],
        accept_multiple_files=True,
        help="Formatos suportados: PDF, TXT, CSV, MD e PY.",
    )

    selected_uploaded_files = uploaded_files or []
    if uploaded_files:
        indexed_document_names_preview = {
            str(document.get("name"))
            for document in indexed_documents_preview
            if isinstance(document, dict) and document.get("name")
        }
        upload_name_options = [uploaded_file.name for uploaded_file in uploaded_files]
        selected_upload_names = st.multiselect(
            "Selecionar uploads para indexar/reindexar agora",
            options=upload_name_options,
            default=upload_name_options,
        )
        selected_uploaded_files = [
            uploaded_file
            for uploaded_file in uploaded_files
            if uploaded_file.name in selected_upload_names
        ]

        upload_preview = []
        for uploaded_file in uploaded_files:
            upload_preview.append(
                {
                    "arquivo": uploaded_file.name,
                    "tipo": uploaded_file.type or "desconhecido",
                    "tamanho_kb": round(uploaded_file.size / 1024, 1),
                    "ação": "reindexar" if uploaded_file.name in indexed_document_names_preview else "indexar",
                }
            )

        with st.expander("Prévia dos uploads atuais", expanded=False):
            st.dataframe(upload_preview, width="stretch")
            st.caption(
                "Indexar novamente os uploads atuais substitui no índice os documentos com o mesmo hash. "
                "Use isso quando mudar chunk_size, overlap ou o embedding model."
            )

    st.caption(
        f"Orçamento bruto do RAG nesta execução: ~{estimated_rag_context_chars} caracteres "
        f"(top-k={effective_rag_settings.top_k} × chunk_size={effective_rag_settings.chunk_size})."
    )
    st.caption(
        f"Budget operacional do prompt: ~{rag_context_budget_chars} caracteres "
        f"(ratio={effective_rag_settings.context_budget_ratio:.2f} · chars/token≈{effective_rag_settings.context_chars_per_token:.1f})."
    )
    if context_usage_ratio >= 1.0:
        st.warning(
            "O contexto bruto do RAG excede o budget operacional estimado do prompt. "
            "O app vai truncar o contexto recuperado antes da geração."
        )
    elif context_usage_ratio >= 0.7:
        st.info(
            "O contexto documental já ocupa boa parte do budget operacional do prompt. "
            "Isso ajuda respostas ancoradas, mas pode aumentar latência."
        )

    embedding_compatibility = inspect_embedding_configuration_compatibility(rag_index, effective_rag_settings)

    coluna_indexar, coluna_limpar, coluna_reset = st.columns(3)
    with coluna_indexar:
        index_requested = st.button(
            "📚 Indexar / reindexar uploads",
            width="stretch",
            disabled=not selected_uploaded_files,
        )
    with coluna_limpar:
        clear_rag_requested = st.button(
            "🗑️ Limpar índice",
            width="stretch",
            disabled=rag_index is None,
            help="Limpa o índice lógico (JSON + coleção Chroma) sem remover a pasta persistida, evitando erro de banco readonly na mesma sessão.",
        )
    with coluna_reset:
        reset_chroma_requested = st.button(
            "♻️ Reset físico Chroma",
            width="stretch",
            help="Remove fisicamente .chroma_rag. Use só com o app prestes a reiniciar; depois, feche e abra o Streamlit antes de reindexar.",
        )

    if index_requested and selected_uploaded_files:
        try:
            index_progress_placeholder = st.empty()
            index_progress_bar = st.progress(0)

            total_files = len(selected_uploaded_files)
            loaded_documents = []
            for index, uploaded_file in enumerate(selected_uploaded_files, start=1):
                progress_start = (index - 1) / max(total_files + 1, 1)
                index_progress_bar.progress(int(progress_start * 100))
                index_progress_placeholder.caption(
                    f"Indexing progress: {index}/{total_files} · extraindo `{uploaded_file.name}`"
                )
                loaded_documents.append(load_document(uploaded_file, effective_rag_settings))
                progress_end = index / max(total_files + 1, 1)
                index_progress_bar.progress(int(progress_end * 100))
                index_progress_placeholder.caption(
                    f"Indexing progress: {index}/{total_files} · arquivo processado `{uploaded_file.name}`"
                )

            index_progress_bar.progress(int((total_files / max(total_files + 1, 1)) * 100))
            index_progress_placeholder.caption("Indexing progress: gerando chunks, embeddings e sincronizando índice")

            base_rag_index = rag_index if embedding_compatibility.get("compatible", True) else None
            built_rag_index, sync_status = upsert_documents_in_rag_index(
                documents=loaded_documents,
                settings=effective_rag_settings,
                embedding_provider=embedding_provider,
                rag_index=base_rag_index,
            )
            set_rag_index(built_rag_index)
            save_rag_store(effective_rag_settings.store_path, built_rag_index)
            index_progress_bar.progress(100)
            index_progress_placeholder.caption("Indexing progress: 100% · indexação finalizada")
            if embedding_compatibility.get("compatible", True):
                st.success(f"{len(loaded_documents)} documento(s) indexado(s) ou reindexado(s) com sucesso.")
            else:
                st.success(
                    f"{len(loaded_documents)} documento(s) indexado(s) com novo embedding. O índice anterior incompatível foi descartado para evitar mistura de espaços vetoriais."
                )
            if sync_status.get("ok"):
                st.caption(sync_status.get("message"))
            else:
                st.warning(sync_status.get("message"))
            st.info(
                "Os parâmetros de chunk size e overlap são aplicados na indexação. "
                "Se você mudar esses valores, use este mesmo fluxo para reindexar apenas os uploads desejados."
            )
            st.rerun()
        except Exception as error:
            logger.exception("Document indexing failed")
            st.error(build_ui_error_message("Erro ao indexar documento", error))

    if clear_rag_requested:
        sync_status = clear_persisted_rag_index(effective_rag_settings)
        clear_rag_state()
        clear_rag_store(rag_settings.store_path)
        if sync_status.get("ok"):
            st.success("Índice RAG removido com sucesso do JSON local e do estado lógico do Chroma.")
            st.caption(sync_status.get("message"))
        else:
            st.warning(f"JSON local removido, mas o Chroma reportou problema: {sync_status.get('message')}")
        st.rerun()

    if reset_chroma_requested:
        reset_status = reset_chroma_persist_directory(effective_rag_settings)
        if reset_status.get("ok"):
            st.success("Persistência física do Chroma removida. Reinicie o app antes de indexar novamente.")
            st.caption(reset_status.get("message"))
        else:
            st.warning(reset_status.get("message"))

    rag_index = normalize_rag_index(get_rag_index(), effective_rag_settings)
    embedding_compatibility = inspect_embedding_configuration_compatibility(rag_index, effective_rag_settings)
    indexed_documents = get_indexed_documents(rag_index, effective_rag_settings)

    if rag_index:
        documents_count = len(indexed_documents)
        chunks = rag_index.get("chunks", []) if isinstance(rag_index, dict) else []
        rag_info = rag_index.get("settings", {}) if isinstance(rag_index, dict) else {}
        if not embedding_compatibility.get("compatible"):
            st.warning(embedding_compatibility.get("message"))
        else:
            st.success(embedding_compatibility.get("message"))
        selected_file_types_count = len(
            {
                str(document.get("file_type"))
                for document in indexed_documents
                if document.get("file_type")
            }
        )

        st.success(
            f"Base documental ativa: {documents_count} documento(s) · {len(chunks)} chunks"
        )
        metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
        metric_col_1.metric("Documentos indexados", documents_count)
        metric_col_2.metric("Chunks no índice", len(chunks))
        metric_col_3.metric("Tipos de arquivo", selected_file_types_count)

        with st.expander("Detalhes do índice RAG"):
            documents_table = []
            for document in indexed_documents:
                loader_metadata = document.get("loader_metadata") or {}
                documents_table.append(
                    {
                        "document_id": document.get("document_id"),
                        "arquivo": document.get("name"),
                        "tipo": document.get("file_type"),
                        "caracteres": document.get("char_count"),
                        "chunks": document.get("chunk_count"),
                        "loader": loader_metadata.get("loader_strategy_label") or loader_metadata.get("loader_strategy_used"),
                        "loader_fallback": loader_metadata.get("loader_strategy_fallback_reason"),
                        "chunking": loader_metadata.get("chunking_strategy_label") or loader_metadata.get("chunking_strategy_used"),
                        "chunking_fallback": loader_metadata.get("chunking_strategy_fallback_reason"),
                        "extração_pdf": loader_metadata.get("strategy_label") if document.get("file_type") == "pdf" else None,
                        "paginas_suspeitas": loader_metadata.get("suspicious_pages") if document.get("file_type") == "pdf" else None,
                        "paginas_docling": ", ".join(str(page) for page in loader_metadata.get("docling_pages_used", [])) if document.get("file_type") == "pdf" else None,
                        "modo_docling": loader_metadata.get("docling_mode") if document.get("file_type") == "pdf" else None,
                        "ocr_fallback": "sim" if loader_metadata.get("ocr_fallback_applied") else ("tentado" if loader_metadata.get("ocr_fallback_attempted") else None) if document.get("file_type") == "pdf" else None,
                        "ocr_backend": loader_metadata.get("ocr_backend") if document.get("file_type") == "pdf" else None,
                        "ocr_motivo": loader_metadata.get("ocr_fallback_reason") if document.get("file_type") == "pdf" else None,
                        "indexado_em": document.get("indexed_at"),
                    }
                )
            st.write(
                {
                    "documentos": documents_count,
                    "chunks": len(chunks),
                    "loader_strategy": rag_info.get("loader_strategy"),
                    "chunking_strategy": rag_info.get("chunking_strategy"),
                    "retrieval_strategy": rag_info.get("retrieval_strategy"),
                    "embedding_model": rag_info.get("embedding_model"),
                    "embedding_context_window": rag_info.get("embedding_context_window"),
                    "chunk_size": rag_info.get("chunk_size"),
                    "chunk_overlap": rag_info.get("chunk_overlap"),
                    "top_k": rag_info.get("top_k"),
                    "pdf_extraction_mode": describe_pdf_extraction_mode(rag_info.get("pdf_extraction_mode")),
                    "pdf_docling_enabled": rag_info.get("pdf_docling_enabled"),
                    "pdf_docling_ocr_enabled": rag_info.get("pdf_docling_ocr_enabled"),
                    "pdf_docling_picture_description": rag_info.get("pdf_docling_picture_description"),
                    "pdf_ocr_fallback_enabled": rag_info.get("pdf_ocr_fallback_enabled"),
                    "pdf_ocr_fallback_languages": rag_info.get("pdf_ocr_fallback_languages"),
                    "atualizado_em": rag_index.get("updated_at") or rag_index.get("created_at"),
                }
            )
            if documents_table:
                st.dataframe(documents_table, width="stretch")

        if len(chunks) > 300:
            st.warning(
                "Seu índice RAG está grande e isso pode deixar indexação e consultas mais lentas. "
                "Se quiser melhorar desempenho, tente aumentar `RAG_CHUNK_SIZE`, reduzir `RAG_TOP_K` ou remover documentos menos importantes do índice."
            )

        document_labels = {
            str(document.get("document_id")): f"{document.get('name')} ({document.get('file_type')})"
            for document in indexed_documents
            if document.get("document_id")
        }
        indexed_document_ids = list(document_labels.keys())
        st.caption(
            "Esses documentos ficam disponíveis para seleção independente nas guias de Chat com RAG e Documento estruturado."
        )

        operation_document_ids = st.multiselect(
            "Selecionar documentos para remover do índice",
            options=indexed_document_ids,
            default=[],
            format_func=lambda item: document_labels.get(item, item),
            help="Você pode remover vários documentos de uma vez sem limpar toda a base.",
        )

        operation_col_1, operation_col_2 = st.columns(2)
        with operation_col_1:
            remove_selected_requested = st.button(
                "Remover documentos selecionados",
                width="stretch",
                disabled=not operation_document_ids,
            )
        with operation_col_2:
            remove_filtered_requested = st.button(
                "Remover todos os documentos indexados",
                width="stretch",
                disabled=not indexed_document_ids,
                help="Remove em lote todos os documentos atualmente indexados.",
            )

        document_ids_to_remove = (
            operation_document_ids
            if remove_selected_requested
            else indexed_document_ids if remove_filtered_requested else []
        )

        if document_ids_to_remove:
            updated_rag_index, sync_status = remove_documents_from_rag_index(
                rag_index=rag_index,
                settings=effective_rag_settings,
                document_ids=document_ids_to_remove,
            )
            if updated_rag_index is None:
                clear_rag_state()
                clear_rag_store(rag_settings.store_path)
            else:
                set_rag_index(updated_rag_index)
                save_rag_store(rag_settings.store_path, updated_rag_index)
            st.success(f"{len(document_ids_to_remove)} documento(s) removido(s) do índice com sucesso.")
            if sync_status.get("ok"):
                st.caption(sync_status.get("message"))
            else:
                st.warning(sync_status.get("message"))
            st.rerun()
    else:
        st.info("Nenhum documento indexado ainda. Faça upload de um ou mais arquivos e clique em 'Indexar documento'.")

    if selected_provider == "openai":
        st.info("Provider cloud habilitado por configuração local. Benchmark real com cloud continua sendo foco principal da Fase 7.")
    elif selected_provider == "huggingface_local":
        st.info("Provider local experimental via Hugging Face/Transformers habilitado. Use como trilha controlada de evolução arquitetural, não como baseline principal ainda.")
    elif selected_provider == "huggingface_server":
        st.info("Provider Hugging Face via servidor local HTTP habilitado. Ideal para comparar modelos do ecossistema HF sem carregar pesos dentro do processo do app.")
    elif selected_provider == "huggingface_inference":
        st.info("Provider Hugging Face Inference habilitado. Útil para comparação remota e para cenários de deploy com pouca memória local, como a VPS da Oracle.")


rag_index = normalize_rag_index(get_rag_index(), effective_rag_settings)
embedding_compatibility = inspect_embedding_configuration_compatibility(rag_index, effective_rag_settings)
indexed_documents = get_indexed_documents(rag_index, effective_rag_settings)
all_indexed_document_ids = [
    str(document.get("document_id"))
    for document in indexed_documents
    if document.get("document_id")
]
document_labels = {
    str(document.get("document_id")): f"{document.get('name')} ({document.get('file_type')})"
    for document in indexed_documents
    if document.get("document_id")
}
document_preview_map = _build_document_preview_map(rag_index, indexed_documents)


with chat_tab:
    st.caption("3. Chat experimental com RAG para exploração, debug de grounding e inspeção operacional — não é mais a homepage do produto.")
    st.info(
        "O chat usa apenas os documentos selecionados abaixo. PDFs escaneados já entram processados pela etapa de indexação, então não há disputa entre OCR e recuperação em tempo de conversa."
    )

    chat_document_ids_default = _normalize_document_selection(
        all_indexed_document_ids,
        st.session_state.get(CHAT_DOCUMENT_SELECTION_STATE_KEY),
        default_to_all=True,
    )

    if all_indexed_document_ids:
        chat_selected_document_ids = st.multiselect(
            "Documentos que o chat pode usar",
            options=all_indexed_document_ids,
            default=chat_document_ids_default,
            format_func=lambda item: document_labels.get(item, item),
            key="phase5_chat_document_selector",
            help="Selecione um ou vários documentos já indexados para limitar o contexto do RAG nesta conversa.",
        )
        st.session_state[CHAT_DOCUMENT_SELECTION_STATE_KEY] = chat_selected_document_ids
        st.caption(f"{len(chat_selected_document_ids)} documento(s) selecionado(s) para o chat.")
    else:
        chat_selected_document_ids = []
        st.session_state[CHAT_DOCUMENT_SELECTION_STATE_KEY] = []
        st.info("Nenhum documento indexado ainda. Primeiro use a guia Documentos para carregar e indexar arquivos.")

    with st.expander("Fase 5.5 · histórico de comparação manual vs LangChain", expanded=False):
        st.caption(f"Log local: `{PHASE55_SHADOW_LOG_PATH.name}`")
        st.write(phase55_shadow_log_summary)
        if phase55_shadow_log_entries:
            recent_entries = list(reversed(phase55_shadow_log_entries[-10:]))
            st.dataframe(
                [
                    {
                        "timestamp": entry.get("timestamp"),
                        "primary": entry.get("primary_strategy"),
                        "alternate": entry.get("alternate_strategy"),
                        "overlap_ratio": entry.get("overlap_ratio"),
                        "same_top_1": entry.get("same_top_1"),
                        "same_top_3": entry.get("same_top_3_order"),
                        "query": entry.get("query"),
                    }
                    for entry in recent_entries
                ],
                width="stretch",
            )
            if st.button("Limpar histórico da Fase 5.5", key="phase55_clear_shadow_log"):
                clear_shadow_log(PHASE55_SHADOW_LOG_PATH)
                st.rerun()
        else:
            st.caption("Nenhuma comparação shadow registrada ainda.")

    st.caption("Modo conversacional com RAG. Use para perguntas abertas, exploração e follow-up sobre os documentos selecionados.")
    for mensagem in messages:
        render_chat_message(mensagem)

    texto_usuario = st.chat_input("Digite sua mensagem")

    if texto_usuario:
        chat_total_started_at = time.perf_counter()
        chat_success = False
        chat_error_message = None
        retrieval_details: dict[str, object] = {}
        chat_effective_context_window, chat_context_window_cap = _resolve_chat_context_window(
            provider=selected_provider,
            mode=context_window_mode,
            manual_context_window=context_window,
            document_ids=chat_selected_document_ids,
            input_text=texto_usuario,
            rag_index=rag_index,
        )
        st.chat_message("user").write(texto_usuario)
        user_metadata = {
            "provider": selected_provider,
            "provider_label": selected_provider_label,
            "model": selected_model,
            "prompt_profile": selected_prompt_profile,
            "prompt_profile_label": selected_prompt_profile_label,
            "temperature": round(temperature, 1),
            "context_window": chat_effective_context_window,
            "context_window_mode": context_window_mode,
            "context_window_cap": chat_context_window_cap,
            "source_document_ids": list(chat_selected_document_ids),
        }
        append_chat_message("user", texto_usuario, metadata=user_metadata)
        save_chat_history(settings.history_path, get_chat_messages())

        texto_resposta_ia = ""
        retrieved_chunks = []
        retrieval_latency = None
        retrieval_backend_used = None
        retrieval_backend_message = None
        retrieval_vector_status = None
        filtered_chunks_available = 0
        retrieval_candidate_pool_size = 0
        retrieval_rerank_strategy = None
        alternate_retrieval_details: dict[str, object] | None = None
        retrieval_shadow_summary: dict[str, object] | None = None
        chat_context_budget_chars = estimate_rag_context_budget_chars(chat_effective_context_window, effective_rag_settings)
        chat_budget_decision = build_budget_routing_decision(
            task_type="chat_rag",
            provider=selected_provider,
            has_document_context=bool(chat_selected_document_ids),
            document_count=len(chat_selected_document_ids),
            requested_top_k=effective_rag_settings.top_k,
            requested_rerank_pool_size=effective_rag_settings.rerank_pool_size,
            context_budget_chars=chat_context_budget_chars,
            estimated_context_chars=(effective_rag_settings.chunk_size * max(effective_rag_settings.top_k, 1) if chat_selected_document_ids else 0),
            prompt_chars=len(texto_usuario or ""),
            allow_auto_degrade=True,
        )
        chat_quality_gate = assess_budget_quality_gate(
            task_type="chat_rag",
            eval_db_path=PHASE8_EVAL_DB_PATH,
        )
        chat_provider_routing = resolve_budget_provider_routing(
            selected_provider=selected_provider,
            task_type="chat_rag",
            available_chat_providers=list(chat_capable_registry.keys()),
            routing_decision=chat_budget_decision,
            quality_gate=chat_quality_gate,
            auto_switch_enabled=True,
        )
        chat_effective_provider = str(chat_provider_routing.get("effective_provider") or selected_provider)
        chat_provider_entry = chat_capable_registry.get(chat_effective_provider) or chat_capable_registry[selected_provider]
        chat_execution_provider_instance = chat_provider_entry["instance"]
        chat_execution_provider_label = str(chat_provider_entry.get("label") or chat_effective_provider)
        chat_provider_models = models_by_provider.get(chat_effective_provider, [])
        chat_execution_model = (
            selected_model
            if selected_model in chat_provider_models
            else default_model_by_provider.get(
                chat_effective_provider,
                chat_provider_models[0] if chat_provider_models else selected_model,
            )
        )
        chat_runtime_rag_settings = replace(
            effective_rag_settings,
            top_k=int(chat_budget_decision.get("top_k_effective") or effective_rag_settings.top_k),
            rerank_pool_size=int(chat_budget_decision.get("rerank_pool_size_effective") or effective_rag_settings.rerank_pool_size),
        )
        prompt_context_details = {
            "budget_chars": chat_context_budget_chars,
            "used_chars": 0,
            "used_chunks": 0,
            "dropped_chunks": 0,
            "truncated": False,
            "context_injected": False,
            "context_chunks": [],
        }
        prompt_build_latency = None
        generation_latency = None
        total_latency = None
        model_messages: list[dict[str, object]] = []

        if rag_index and chat_selected_document_ids and embedding_compatibility.get("compatible", True):
            try:
                retrieval_started_at = time.perf_counter()
                retrieval_details = retrieve_relevant_chunks_detailed(
                    query=texto_usuario,
                    rag_index=rag_index,
                    settings=chat_runtime_rag_settings,
                    embedding_provider=embedding_provider,
                    document_ids=chat_selected_document_ids,
                    file_types=None,
                )
                retrieved_chunks = retrieval_details.get("chunks", [])
                retrieval_backend_used = retrieval_details.get("backend_used")
                retrieval_backend_message = retrieval_details.get("backend_message")
                retrieval_vector_status = retrieval_details.get("vector_backend_status")
                filtered_chunks_available = retrieval_details.get("filtered_chunks_available")
                retrieval_candidate_pool_size = retrieval_details.get("candidate_pool_size") or 0
                retrieval_rerank_strategy = retrieval_details.get("rerank_strategy")
                retrieval_latency = time.perf_counter() - retrieval_started_at

                if debug_retrieval:
                    alternate_strategy = (
                        "manual_hybrid"
                        if selected_retrieval_strategy == "langchain_chroma"
                        else "langchain_chroma"
                    )
                    try:
                        alternate_retrieval_details = retrieve_relevant_chunks_detailed(
                            query=texto_usuario,
                            rag_index=rag_index,
                            settings=replace(chat_runtime_rag_settings, retrieval_strategy=alternate_strategy),
                            embedding_provider=embedding_provider,
                            document_ids=chat_selected_document_ids,
                            file_types=None,
                        )
                    except Exception as shadow_error:
                        alternate_retrieval_details = {
                            "retrieval_strategy_requested": alternate_strategy,
                            "retrieval_strategy_used": "error",
                            "backend_message": str(shadow_error),
                            "chunks": [],
                        }
                    retrieval_shadow_summary = _build_retrieval_shadow_summary(
                        retrieval_details,
                        alternate_retrieval_details,
                    )
                    if retrieval_shadow_summary:
                        phase55_shadow_log_entries = append_shadow_log_entry(
                            PHASE55_SHADOW_LOG_PATH,
                            _build_shadow_log_entry(
                                query=texto_usuario,
                                provider=selected_provider,
                                model=selected_model,
                                document_ids=chat_selected_document_ids,
                                shadow_summary=retrieval_shadow_summary,
                            ),
                        )
                        phase55_shadow_log_summary = summarize_shadow_log(phase55_shadow_log_entries)
            except Exception as error:
                logger.exception("Chat retrieval failed; continuing without RAG")
                st.warning(build_ui_error_message("Não foi possível recuperar contexto do documento. A resposta seguirá sem RAG", error))
                retrieved_chunks = []
                retrieval_backend_used = "error"
                retrieval_backend_message = str(error)
                retrieval_vector_status = None
                filtered_chunks_available = 0
                retrieval_candidate_pool_size = 0
                retrieval_rerank_strategy = None
        elif rag_index and not embedding_compatibility.get("compatible", True):
            retrieval_backend_used = "disabled_incompatible_embedding"
            retrieval_backend_message = embedding_compatibility.get("message")
            retrieval_vector_status = inspect_vector_backend_status(rag_index, effective_rag_settings)
            st.info("RAG desativado nesta pergunta porque o embedding ativo não é compatível com o índice carregado. Reindexe para voltar a usar a base documental.")
        elif rag_index and not chat_selected_document_ids:
            retrieval_backend_used = "disabled_no_documents_selected"
            retrieval_backend_message = "Nenhum documento foi selecionado para esta conversa."

        with st.chat_message("assistant"):
            placeholder = st.empty()
            try:
                prompt_build_started_at = time.perf_counter()
                model_messages, prompt_context_details = inject_rag_context(
                    build_prompt_messages(selected_prompt_profile, get_chat_messages()),
                    retrieved_chunks,
                    context_window=chat_effective_context_window,
                    settings=chat_runtime_rag_settings,
                )
                prompt_build_latency = time.perf_counter() - prompt_build_started_at
                generation_started_at = time.perf_counter()
                stream = chat_execution_provider_instance.stream_chat_completion(
                    messages=model_messages,
                    model=chat_execution_model,
                    temperature=temperature,
                    context_window=chat_effective_context_window,
                )

                partes = []
                for token in chat_execution_provider_instance.iter_stream_text(stream):
                    partes.append(token)
                    placeholder.markdown("".join(partes) + "▌")

                texto_resposta_ia = "".join(partes).strip() or "A resposta veio vazia."
                placeholder.markdown(texto_resposta_ia)

                generation_latency = time.perf_counter() - generation_started_at
                total_latency = time.perf_counter() - chat_total_started_at
                set_last_latency(total_latency)
                st.caption(f"Resposta total em {total_latency:.2f}s")
                timing_parts = []
                if retrieval_latency is not None:
                    timing_parts.append(f"retrieval={retrieval_latency:.2f}s")
                if prompt_build_latency is not None:
                    timing_parts.append(f"prompt={prompt_build_latency:.2f}s")
                if generation_latency is not None:
                    timing_parts.append(f"geração={generation_latency:.2f}s")
                if timing_parts:
                    st.caption(" · ".join(timing_parts))
                st.caption(
                    f"Contexto do chat nesta execução: modo `{context_window_mode}` · resolvido em `{chat_effective_context_window}` · cap `{chat_context_window_cap}`"
                )
                if bool(chat_provider_routing.get("provider_switch_applied")):
                    st.caption(
                        f"Budget provider routing no chat: `{selected_provider}` -> `{chat_effective_provider}` ({chat_execution_provider_label}) · model efetivo `{chat_execution_model}`"
                    )
                if bool(chat_budget_decision.get("auto_degrade_applied")):
                    st.caption(
                        f"Budget routing ativo no chat: modo `{chat_budget_decision.get('routing_mode')}` · razão `{chat_budget_decision.get('reason')}` · top_k efetivo `{chat_budget_decision.get('top_k_effective')}` · rerank_pool efetivo `{chat_budget_decision.get('rerank_pool_size_effective')}`"
                    )
                chat_success = True

                if debug_retrieval:
                    with st.expander("Debug de retrieval", expanded=False):
                        st.write(
                            {
                                "chunk_size": effective_rag_settings.chunk_size,
                                "chunk_overlap": effective_rag_settings.chunk_overlap,
                                "top_k": effective_rag_settings.top_k,
                                "embedding_model": effective_rag_settings.embedding_model,
                                "embedding_context_window": effective_rag_settings.embedding_context_window,
                                "embedding_index_compatibility": embedding_compatibility,
                                "selected_document_ids": chat_selected_document_ids,
                                "retrieved_chunks": len(retrieved_chunks),
                                "retrieval_latency_s": round(retrieval_latency, 2) if retrieval_latency is not None else None,
                                "prompt_build_latency_s": round(prompt_build_latency, 2) if prompt_build_latency is not None else None,
                                "generation_latency_s": round(generation_latency, 2) if generation_latency is not None else None,
                                "total_latency_s": round(total_latency, 2) if total_latency is not None else None,
                                "provider": selected_provider,
                                "model": selected_model,
                                "context_window": chat_effective_context_window,
                                "context_window_mode": context_window_mode,
                                "context_window_cap": chat_context_window_cap,
                                "vector_backend_used": retrieval_backend_used,
                                "vector_backend_message": retrieval_backend_message,
                                "retrieval_strategy_requested": retrieval_details.get("retrieval_strategy_requested") if isinstance(retrieval_details, dict) else None,
                                "retrieval_strategy_used": retrieval_details.get("retrieval_strategy_used") if isinstance(retrieval_details, dict) else None,
                                "retrieval_strategy_fallback_reason": retrieval_details.get("retrieval_strategy_fallback_reason") if isinstance(retrieval_details, dict) else None,
                                "filtered_chunks_available": filtered_chunks_available,
                                "candidate_pool_size": retrieval_candidate_pool_size,
                                "rerank_strategy": retrieval_rerank_strategy,
                                "prompt_context": {
                                    "budget_chars": prompt_context_details.get("budget_chars"),
                                    "used_chars": prompt_context_details.get("used_chars"),
                                    "used_chunks": prompt_context_details.get("used_chunks"),
                                    "dropped_chunks": prompt_context_details.get("dropped_chunks"),
                                    "truncated": prompt_context_details.get("truncated"),
                                },
                                "budget_routing": chat_budget_decision,
                                "vector_backend_status": retrieval_vector_status,
                            }
                        )
                        for index, chunk in enumerate(retrieved_chunks, start=1):
                            st.markdown(
                                f"**{index}. {chunk.get('source', 'documento')} · score={chunk.get('score')} · vector={chunk.get('vector_score')} · lexical={chunk.get('lexical_score')} · chunk={chunk.get('chunk_id')}**"
                            )
                            snippet = chunk.get("snippet") or str(chunk.get("text", ""))[:500]
                            if snippet:
                                st.code(snippet)
                        if isinstance(alternate_retrieval_details, dict):
                            st.markdown("---")
                            st.caption("Comparação shadow · estratégia alternativa")
                            st.write(
                                {
                                    "retrieval_strategy_requested": alternate_retrieval_details.get("retrieval_strategy_requested"),
                                    "retrieval_strategy_used": alternate_retrieval_details.get("retrieval_strategy_used"),
                                    "retrieval_strategy_fallback_reason": alternate_retrieval_details.get("retrieval_strategy_fallback_reason"),
                                    "backend_used": alternate_retrieval_details.get("backend_used"),
                                    "backend_message": alternate_retrieval_details.get("backend_message"),
                                    "candidate_pool_size": alternate_retrieval_details.get("candidate_pool_size"),
                                    "retrieved_chunks": len(alternate_retrieval_details.get("chunks") or []),
                                }
                            )
                            if retrieval_shadow_summary:
                                st.caption("Resumo comparativo")
                                st.write(retrieval_shadow_summary)
                            for shadow_index, shadow_chunk in enumerate(alternate_retrieval_details.get("chunks") or [], start=1):
                                st.markdown(
                                    f"**alt {shadow_index}. {shadow_chunk.get('source', 'documento')} · score={shadow_chunk.get('score')} · vector={shadow_chunk.get('vector_score')} · lexical={shadow_chunk.get('lexical_score')} · chunk={shadow_chunk.get('chunk_id')}**"
                                )
                                shadow_snippet = shadow_chunk.get("snippet") or str(shadow_chunk.get("text", ""))[:500]
                                if shadow_snippet:
                                    st.code(shadow_snippet)
            except Exception as erro:
                logger.exception("Chat generation failed")
                set_last_latency(None)
                chat_error_message = str(erro)
                texto_resposta_ia = chat_execution_provider_instance.format_error(chat_execution_model, erro)
                placeholder.empty()
                st.error(texto_resposta_ia)

        chat_native_usage_metrics = get_provider_native_usage_metrics(chat_execution_provider_instance)
        assistant_metadata = {
            **user_metadata,
            "provider": chat_effective_provider,
            "provider_requested": selected_provider,
            "provider_effective": chat_effective_provider,
            "provider_effective_label": chat_execution_provider_label,
            "model": chat_execution_model,
            "model_requested": selected_model,
            "model_effective": chat_execution_model,
            "latency_s": round(get_last_latency(), 2) if get_last_latency() is not None else None,
            "retrieval_latency_s": round(retrieval_latency, 2) if retrieval_latency is not None else None,
            "prompt_build_latency_s": round(prompt_build_latency, 2) if prompt_build_latency is not None else None,
            "generation_latency_s": round(generation_latency, 2) if generation_latency is not None else None,
            "retrieved_chunks_count": len(retrieved_chunks),
            "vector_backend_used": retrieval_backend_used,
            "vector_backend_message": retrieval_backend_message,
            "vector_backend_status": retrieval_vector_status,
            "retrieval_strategy_requested": retrieval_details.get("retrieval_strategy_requested") if 'retrieval_details' in locals() and isinstance(retrieval_details, dict) else None,
            "retrieval_strategy_used": retrieval_details.get("retrieval_strategy_used") if 'retrieval_details' in locals() and isinstance(retrieval_details, dict) else None,
            "retrieval_strategy_fallback_reason": retrieval_details.get("retrieval_strategy_fallback_reason") if 'retrieval_details' in locals() and isinstance(retrieval_details, dict) else None,
            "filtered_chunks_available": filtered_chunks_available,
            "rag_chunk_size": effective_rag_settings.chunk_size,
            "rag_chunk_overlap": effective_rag_settings.chunk_overlap,
            "rag_top_k": effective_rag_settings.top_k,
            "debug_retrieval": debug_retrieval,
            "rerank_strategy": retrieval_rerank_strategy,
            "retrieval_candidate_pool_size": retrieval_candidate_pool_size,
            "retrieval_shadow_summary": retrieval_shadow_summary,
            "budget_routing_mode": chat_budget_decision.get("routing_mode"),
            "budget_routing_reason": chat_budget_decision.get("reason"),
            "budget_auto_degrade_applied": chat_budget_decision.get("auto_degrade_applied"),
            "budget_sensitivity": chat_budget_decision.get("sensitivity"),
            "budget_quality_gate": chat_quality_gate,
            "budget_provider_routing": chat_provider_routing,
            "prompt_context": {
                "budget_chars": prompt_context_details.get("budget_chars"),
                "used_chars": prompt_context_details.get("used_chars"),
                "used_chunks": prompt_context_details.get("used_chunks"),
                "dropped_chunks": prompt_context_details.get("dropped_chunks"),
                "truncated": prompt_context_details.get("truncated"),
            },
            "sources": build_source_metadata(prompt_context_details.get("context_chunks") or retrieved_chunks),
        }
        chat_usage_metrics = estimate_runtime_usage_metrics(
            prompt_chars=count_message_chars(model_messages),
            completion_chars=len(texto_resposta_ia or ""),
            context_chars=int(prompt_context_details.get("used_chars") or 0),
            provider=chat_effective_provider,
            native_usage=chat_native_usage_metrics,
            chars_per_token=effective_rag_settings.context_chars_per_token,
        )
        chat_document_runtime_signals = _build_document_runtime_signal_summary(
            chat_selected_document_ids,
            document_preview_map,
        )
        chat_budget_alerts = evaluate_budget_alerts(
            task_type="chat_rag",
            provider=chat_effective_provider,
            total_tokens=int(chat_usage_metrics.get("total_tokens") or 0),
            cost_usd=(float(chat_usage_metrics.get("cost_usd")) if isinstance(chat_usage_metrics.get("cost_usd"), (int, float)) else None),
            latency_s=(get_last_latency() if get_last_latency() is not None else total_latency),
            context_pressure_ratio=(float(chat_budget_decision.get("context_pressure_ratio")) if isinstance(chat_budget_decision.get("context_pressure_ratio"), (int, float)) else None),
            auto_degrade_applied=bool(chat_budget_decision.get("auto_degrade_applied")),
        )
        assistant_metadata["budget_alert_status"] = chat_budget_alerts.get("status")
        assistant_metadata["budget_alerts"] = chat_budget_alerts.get("alerts")
        assistant_metadata["usage"] = chat_usage_metrics
        append_chat_message("assistant", texto_resposta_ia, metadata=assistant_metadata)
        save_chat_history(settings.history_path, get_chat_messages())
        append_runtime_execution_log_entry(
            RUNTIME_EXECUTION_LOG_PATH,
            _build_runtime_execution_log_entry(
                flow_type="chat_rag",
                task_type="chat_rag",
                provider=chat_effective_provider,
                model=chat_execution_model,
                success=chat_success,
                latency_s=(get_last_latency() if get_last_latency() is not None else (time.perf_counter() - chat_total_started_at)),
                retrieval_latency_s=retrieval_latency,
                generation_latency_s=generation_latency,
                prompt_build_latency_s=prompt_build_latency,
                context_window=chat_effective_context_window,
                context_window_mode=context_window_mode,
                embedding_provider=str(embedding_provider_key or selected_embedding_provider),
                embedding_model=selected_embedding_model,
                retrieval_strategy_requested=(retrieval_details.get("retrieval_strategy_requested") if isinstance(retrieval_details, dict) else None),
                retrieval_strategy_used=(retrieval_details.get("retrieval_strategy_used") if isinstance(retrieval_details, dict) else None),
                retrieval_backend_used=retrieval_backend_used,
                rag_chunk_size=effective_rag_settings.chunk_size,
                rag_chunk_overlap=effective_rag_settings.chunk_overlap,
                rag_top_k=chat_runtime_rag_settings.top_k,
                prompt_chars=int(chat_usage_metrics.get("prompt_chars") or 0),
                output_chars=int(chat_usage_metrics.get("output_chars") or 0),
                context_chars=int(chat_usage_metrics.get("context_chars") or 0),
                prompt_tokens=int(chat_usage_metrics.get("prompt_tokens") or 0),
                completion_tokens=int(chat_usage_metrics.get("completion_tokens") or 0),
                total_tokens=int(chat_usage_metrics.get("total_tokens") or 0),
                usage_source=str(chat_usage_metrics.get("usage_source") or "estimated_chars"),
                cost_usd=(float(chat_usage_metrics.get("cost_usd")) if isinstance(chat_usage_metrics.get("cost_usd"), (int, float)) else None),
                cost_source=str(chat_usage_metrics.get("cost_source") or "pricing_not_configured"),
                source_document_ids=chat_selected_document_ids,
                retrieved_chunks_count=len(retrieved_chunks),
                error_message=chat_error_message,
                extra={
                    "budget_routing_mode": chat_budget_decision.get("routing_mode"),
                    "budget_routing_reason": chat_budget_decision.get("reason"),
                    "budget_sensitivity": chat_budget_decision.get("sensitivity"),
                    "budget_quality_floor": chat_budget_decision.get("quality_floor"),
                    "budget_auto_degrade_applied": chat_budget_decision.get("auto_degrade_applied"),
                    "rerank_pool_size_effective": chat_budget_decision.get("rerank_pool_size_effective"),
                    "top_k_requested": chat_budget_decision.get("requested_top_k"),
                    "top_k_effective": chat_budget_decision.get("top_k_effective"),
                    "context_budget_chars": chat_budget_decision.get("context_budget_chars"),
                    "estimated_context_chars": chat_budget_decision.get("estimated_context_chars"),
                    "context_pressure_ratio": chat_budget_decision.get("context_pressure_ratio"),
                    "prompt_context_used_chunks": prompt_context_details.get("used_chunks"),
                    "prompt_context_dropped_chunks": prompt_context_details.get("dropped_chunks"),
                    "prompt_context_truncated": bool(prompt_context_details.get("truncated")),
                    "provider_requested": selected_provider,
                    "model_requested": selected_model,
                    "provider_switch_applied": bool(chat_provider_routing.get("provider_switch_applied")),
                    "provider_switch_reason": chat_provider_routing.get("reason"),
                    "quality_gate_status": chat_quality_gate.get("status"),
                    "quality_gate_reason": chat_quality_gate.get("reason"),
                    "quality_gate_pass_rate": chat_quality_gate.get("pass_rate"),
                    "quality_gate_min_pass_rate": chat_quality_gate.get("min_pass_rate"),
                    "quality_gate_recent_runs": chat_quality_gate.get("recent_runs"),
                    "budget_alert_status": chat_budget_alerts.get("status"),
                    "budget_alerts": chat_budget_alerts.get("alerts"),
                    "budget_thresholds": chat_budget_alerts.get("thresholds"),
                    **chat_document_runtime_signals,
                },
            ),
        )


with structured_tab:
    st.caption("4. Workflow Inspector & Structured: inspeção de structured outputs, execuções LangGraph e comportamento do Document Operations Copilot.")
    st.info(
        "Fluxo recomendado: 1) escolha a task, 2) selecione um ou mais documentos indexados, 3) rode a análise e revise o resultado em JSON ou visualização friendly."
    )

    structured_task_definitions = structured_task_registry.list_tasks()
    structured_task_options = list(structured_task_definitions.keys())
    structured_task_descriptions = structured_task_registry.get_available_tasks()
    default_structured_task = "summary" if rag_index else "extraction"
    if default_structured_task not in structured_task_options:
        default_structured_task = structured_task_options[0]

    structured_document_ids_default = _normalize_document_selection(
        all_indexed_document_ids,
        st.session_state.get(STRUCTURED_DOCUMENT_SELECTION_STATE_KEY),
        default_to_all=True,
    )

    task_help = {
        "extraction": "Extrai entidades, datas, números, riscos e ações a partir de um documento.",
        "summary": "Resume notas de reunião, briefs e textos técnicos em formato estruturado.",
        "checklist": "Transforma instruções e procedimentos em checklist operacional.",
        "document_agent": "Copiloto documental com roteamento de intenção, seleção de tool, fontes e sinalização de revisão humana.",
        "cv_analysis": "Analisa um currículo com base no documento selecionado. Melhor usar 1 CV por vez.",
        "code_analysis": "Analisa código ou texto técnico com foco em propósito, problemas e plano de refatoração.",
    }
    structured_execution_strategy_options = ["direct", "langgraph_context_retry"]

    active_structured_document_ids: list[str] = []
    structured_use_documents = False
    structured_context_strategy = "document_scan"
    structured_input_text = st.session_state.get("phase5_structured_input", "")
    effective_structured_context_preview = ""
    effective_structured_context_chars = 0
    effective_structured_context_blocks = 0

    # Calculate effective context outside the form to enable reactive updates
    if all_indexed_document_ids:
        active_structured_document_ids = st.multiselect(
            "Documentos para a análise estruturada",
            options=all_indexed_document_ids,
            default=structured_document_ids_default,
            format_func=lambda item: document_labels.get(item, item),
            key="phase5_structured_document_selector_main",
            help="Selecione um ou vários documentos já indexados para usar nesta task estruturada.",
        )
        st.session_state[STRUCTURED_DOCUMENT_SELECTION_STATE_KEY] = active_structured_document_ids
    else:
        active_structured_document_ids = []
        st.session_state[STRUCTURED_DOCUMENT_SELECTION_STATE_KEY] = []
        st.caption("Nenhum documento indexado disponível.")

    selected_structured_task = st.selectbox(
        "Task",
        structured_task_options,
        index=structured_task_options.index(default_structured_task),
        format_func=lambda item: f"{item} · {structured_task_descriptions.get(item, item)}",
        key="phase5_structured_task_selector",
    )
    st.caption(task_help.get(selected_structured_task, ""))
    selected_structured_execution_strategy = st.selectbox(
        "Estratégia de execução estruturada",
        structured_execution_strategy_options,
        index=0,
        format_func=describe_structured_execution_strategy,
        key="phase55_structured_execution_strategy_selector",
        help="`direct` usa o caminho atual. `langgraph_context_retry` usa um workflow experimental com LangGraph que pode refazer a execução usando `retrieval` se a primeira tentativa falhar com `document_scan`.",
    )
    st.caption(
        f"Execução estruturada nesta rodada: {describe_structured_execution_strategy(selected_structured_execution_strategy)}"
    )
    shadow_compare_structured = st.checkbox(
        "Comparar execução direta vs LangGraph (shadow)",
        value=False,
        key="phase55_structured_shadow_compare",
        help="Executa a estratégia alternativa em segundo plano para comparar robustez, latência e guardrails entre `direct` e `langgraph_context_retry`.",
    )

    with st.expander("Fase 5.5 · histórico direct vs LangGraph", expanded=False):
        st.caption(f"Log local: `{PHASE55_LANGGRAPH_SHADOW_LOG_PATH.name}`")
        st.write(phase55_langgraph_shadow_log_summary)
        if phase55_langgraph_shadow_log_entries:
            recent_entries = list(reversed(phase55_langgraph_shadow_log_entries[-10:]))
            st.dataframe(
                [
                    {
                        "timestamp": entry.get("timestamp"),
                        "task": entry.get("task_type"),
                        "primary": entry.get("primary_strategy_used"),
                        "alternate": entry.get("alternate_strategy_used"),
                        "same_success": entry.get("same_success"),
                        "quality_delta": entry.get("quality_delta"),
                        "latency_delta_s": entry.get("latency_delta_s"),
                        "alternate_avoided_review": entry.get("alternate_avoided_review"),
                    }
                    for entry in recent_entries
                ],
                width="stretch",
            )
            if st.button("Limpar histórico direct vs LangGraph", key="phase55_clear_langgraph_shadow_log"):
                clear_langgraph_shadow_log(PHASE55_LANGGRAPH_SHADOW_LOG_PATH)
                st.rerun()
        else:
            st.caption("Nenhuma comparação direct vs LangGraph registrada ainda.")

    with st.expander("Fase 6 · histórico do Document Operations Copilot", expanded=False):
        st.caption(f"Log local: `{PHASE6_DOCUMENT_AGENT_LOG_PATH.name}`")
        st.write(phase6_document_agent_log_summary)
        if phase6_document_agent_log_entries:
            recent_entries = list(reversed(phase6_document_agent_log_entries[-10:]))
            st.dataframe(
                [
                    {
                        "timestamp": entry.get("timestamp"),
                        "intent": entry.get("user_intent"),
                        "tool": entry.get("tool_used"),
                        "confidence": entry.get("confidence"),
                        "needs_review": entry.get("needs_review"),
                        "source_count": entry.get("source_count"),
                        "query": entry.get("query"),
                    }
                    for entry in recent_entries
                ],
                width="stretch",
            )
            if st.button("Limpar histórico do agente documental", key="phase6_clear_document_agent_log"):
                clear_document_agent_log(PHASE6_DOCUMENT_AGENT_LOG_PATH)
                st.rerun()
        else:
            st.caption("Nenhuma execução auditável do Document Operations Copilot registrada ainda.")

    structured_input_text = st.text_area(
        "Input text (opcional quando usar documentos)",
        value=st.session_state.get("phase5_structured_input", ""),
        height=220,
        placeholder="Cole o texto aqui. Para CV analysis e extraction, você também pode usar só os documentos selecionados.",
        key="phase5_structured_input_text",
    )

    structured_use_documents = st.checkbox(
        "Usar documentos selecionados",
        value=bool(active_structured_document_ids),
        disabled=not bool(active_structured_document_ids),
        help="Usa os documentos selecionados/indexados como contexto para a task estruturada.",
        key="phase5_structured_use_documents",
    )
    if active_structured_document_ids:
        st.caption(f"{len(active_structured_document_ids)} documento(s) selecionado(s)")
        st.caption(
            "Esses documentos já foram processados na etapa de indexação, incluindo PDF/OCR quando necessário; a task estruturada usa o índice consolidado em vez de disputar com o leitor de PDF em tempo real."
        )
    else:
        st.caption("Nenhum documento selecionado")

    structured_context_strategy, structured_context_strategy_reason = _resolve_structured_context_strategy(
        task_type=selected_structured_task,
        input_text=structured_input_text,
        use_documents=structured_use_documents,
        selected_document_ids=active_structured_document_ids,
    )
    if structured_use_documents:
        st.caption(f"Estratégia automática: `{structured_context_strategy}`")
        st.caption(structured_context_strategy_reason)
        if selected_structured_task == "cv_analysis" and len(active_structured_document_ids) > 1:
            st.warning("Para `cv_analysis`, o ideal é selecionar 1 currículo por vez para evitar mistura de perfis.")
    else:
        st.caption("Estratégia automática pronta, mas nenhum documento será usado nesta execução.")

    # Calculate effective context outside the form for reactive updates
    if structured_use_documents and active_structured_document_ids:
        effective_structured_context_preview = build_structured_document_context(
            query=structured_input_text,
            document_ids=active_structured_document_ids,
            strategy=structured_context_strategy,
        )
        effective_structured_context_chars = len(effective_structured_context_preview)
        effective_structured_context_blocks = effective_structured_context_preview.count("[Source:")
    else:
        effective_structured_context_preview = ""
        effective_structured_context_chars = 0
        effective_structured_context_blocks = 0

    estimated_structured_document_chars = _estimate_selected_document_chars(
        rag_index,
        active_structured_document_ids if structured_use_documents else [],
        input_text=structured_input_text,
    )
    structured_context_window_cap = (
        context_window
        if context_window_mode == "manual"
        else _resolve_auto_context_window_cap(
            selected_provider,
            default_context_window_by_provider.get(selected_provider, context_window),
        )
    )
    structured_context_window_resolved = structured_service.resolve_context_window(
        TaskExecutionRequest(
            task_type=selected_structured_task,
            input_text=structured_input_text,
            use_rag_context=False,
            use_document_context=bool(structured_use_documents and active_structured_document_ids),
            source_document_ids=list(active_structured_document_ids if structured_use_documents else []),
            context_strategy=structured_context_strategy,
            provider=selected_provider,
            model=selected_model,
            temperature=temperature,
            context_window=None if context_window_mode == "auto" else structured_context_window_cap,
        ),
        max_context_window=structured_context_window_cap,
    )
    structured_context_budget_chars = estimate_rag_context_budget_chars(
        structured_context_window_resolved,
        effective_rag_settings,
    )
    structured_budget_decision = build_budget_routing_decision(
        task_type=selected_structured_task,
        provider=selected_provider,
        has_document_context=bool(structured_use_documents and active_structured_document_ids),
        document_count=len(active_structured_document_ids if structured_use_documents else []),
        requested_top_k=effective_rag_settings.top_k,
        requested_rerank_pool_size=effective_rag_settings.rerank_pool_size,
        context_budget_chars=structured_context_budget_chars,
        estimated_context_chars=(estimated_structured_document_chars if structured_use_documents else len(structured_input_text or "")),
        prompt_chars=len(structured_input_text or ""),
        allow_auto_degrade=False,
    )
    structured_quality_gate = assess_budget_quality_gate(
        task_type=selected_structured_task,
        eval_db_path=PHASE8_EVAL_DB_PATH,
    )
    structured_provider_routing = resolve_budget_provider_routing(
        selected_provider=selected_provider,
        task_type=selected_structured_task,
        available_chat_providers=list(chat_capable_registry.keys()),
        routing_decision=structured_budget_decision,
        quality_gate=structured_quality_gate,
        auto_switch_enabled=True,
    )
    structured_effective_provider = str(structured_provider_routing.get("effective_provider") or selected_provider)
    structured_provider_models = models_by_provider.get(structured_effective_provider, [])
    structured_execution_model = (
        selected_model
        if selected_model in structured_provider_models
        else default_model_by_provider.get(
            structured_effective_provider,
            structured_provider_models[0] if structured_provider_models else selected_model,
        )
    )

    can_run_structured = bool(structured_input_text.strip()) or bool(structured_use_documents and active_structured_document_ids)

    stored_structured_result_preview = st.session_state.get(STRUCTURED_RESULT_STATE_KEY)
    rendered_result_preview = (
        StructuredResult.model_validate(stored_structured_result_preview)
        if stored_structured_result_preview
        else None
    )

    next_execution_summary_preview = {}
    next_execution_extraction_preview = {}
    next_execution_checklist_preview = {}
    if selected_structured_task == "summary" and structured_use_documents and active_structured_document_ids:
        next_execution_summary_preview = _estimate_summary_next_execution_preview(
            rag_index=rag_index,
            document_ids=active_structured_document_ids,
            input_text=structured_input_text,
            context_strategy=structured_context_strategy,
        )
    elif selected_structured_task == "extraction" and structured_use_documents and active_structured_document_ids:
        full_document_text_for_extraction = _build_full_document_text_from_selection(rag_index, active_structured_document_ids)
        next_execution_extraction_preview = build_extraction_execution_preview(
            input_text=structured_input_text,
            document_text=full_document_text_for_extraction,
            context_text_from_scan=effective_structured_context_preview,
        )
    elif selected_structured_task == "checklist" and structured_use_documents and active_structured_document_ids:
        full_document_text_for_checklist = _build_full_document_text_from_selection(rag_index, active_structured_document_ids)
        next_execution_checklist_preview = build_checklist_execution_preview(
            input_text=structured_input_text,
            document_text=full_document_text_for_checklist,
            context_text_from_scan=effective_structured_context_preview,
        )

    # Show context preview outside the form
    with st.container(border=True):
        context_panel_title = "### Contexto final enviado para a IA"
        if selected_structured_task == "checklist":
            context_panel_title = "### Prévia do contexto para gerar o checklist"
        elif selected_structured_task == "summary":
            context_panel_title = "### Prévia do contexto para gerar o resumo"
        elif selected_structured_task == "extraction":
            context_panel_title = "### Prévia do contexto para gerar a extração"
        st.markdown(context_panel_title)
        st.caption(
            f"Context window desta execução: modo `{context_window_mode}` · resolvido em `{structured_context_window_resolved}` (cap usado: `{structured_context_window_cap}` · chars estimados do documento: `{estimated_structured_document_chars}`)."
        )
        st.caption(
            f"Budget routing estruturado: modo `{structured_budget_decision.get('routing_mode')}` · sensibilidade `{structured_budget_decision.get('sensitivity')}` · quality_floor `{structured_budget_decision.get('quality_floor')}` · razão `{structured_budget_decision.get('reason')}`"
        )
        summary_metadata = (
            rendered_result_preview.execution_metadata
            if rendered_result_preview is not None
            and rendered_result_preview.task_type == "summary"
            and isinstance(rendered_result_preview.execution_metadata, dict)
            else {}
        )
        summary_stages = summary_metadata.get("stages") if isinstance(summary_metadata.get("stages"), list) else []

        if selected_structured_task == "summary" and next_execution_summary_preview:
            st.markdown("#### Preview da próxima execução")
            preview_mode = str(next_execution_summary_preview.get("summary_mode") or "unknown")
            preview_stages = next_execution_summary_preview.get("stages") if isinstance(next_execution_summary_preview.get("stages"), list) else []
            metric_col_a, metric_col_b, metric_col_c = st.columns(3)
            metric_col_a.metric("Modo previsto", preview_mode)
            metric_col_b.metric("Documento chars", next_execution_summary_preview.get("full_document_chars", 0))
            metric_col_c.metric("Etapas previstas", len(preview_stages))
            for index, stage in enumerate(preview_stages, start=1):
                if not isinstance(stage, dict):
                    continue
                label = str(stage.get("label") or f"Stage {index}")
                chars_sent = stage.get("chars_sent")
                expander_title = label + (f" · chars={chars_sent}" if chars_sent is not None else "")
                with st.expander(expander_title, expanded=False):
                    context_preview = str(stage.get("context_preview") or "")
                    prompt_preview = str(stage.get("prompt_preview") or "")
                    if context_preview:
                        st.caption("Contexto que seria enviado")
                        st.text_area(
                            f"Preview contexto etapa {index}",
                            value=context_preview,
                            height=220,
                            disabled=True,
                            key=f"phase5_structured_next_stage_context_{index}",
                        )
                    if prompt_preview and prompt_preview != context_preview:
                        st.caption("Prompt estimado da etapa")
                        st.text_area(
                            f"Preview prompt etapa {index}",
                            value=prompt_preview,
                            height=180,
                            disabled=True,
                            key=f"phase5_structured_next_stage_prompt_{index}",
                        )

        if selected_structured_task == "extraction" and next_execution_extraction_preview:
            st.markdown("#### Preview da próxima execução")
            metric_col_a, metric_col_b, metric_col_c = st.columns(3)
            metric_col_a.metric("Modo previsto", next_execution_extraction_preview.get("extraction_mode", "-"))
            metric_col_b.metric("Documento chars", next_execution_extraction_preview.get("full_document_chars", 0))
            metric_col_c.metric("Chars reais enviados", next_execution_extraction_preview.get("context_chars_sent", 0))
            context_preview_value = str(next_execution_extraction_preview.get("context_preview") or "")
            if context_preview_value:
                st.text_area(
                    "Texto real previsto para envio ao modelo",
                    value=context_preview_value,
                    height=520,
                    disabled=True,
                    key="phase5_structured_extraction_real_execution_preview",
                )
            prompt_preview_value = str(next_execution_extraction_preview.get("prompt_preview") or "")
            if prompt_preview_value and prompt_preview_value != context_preview_value:
                with st.expander("Prompt completo previsto", expanded=False):
                    st.text_area(
                        "Prompt previsto da extração",
                        value=prompt_preview_value,
                        height=320,
                        disabled=True,
                        key="phase5_structured_extraction_prompt_preview",
                    )
        elif selected_structured_task == "checklist" and next_execution_checklist_preview:
            st.markdown("#### Preview da próxima execução")
            metric_col_a, metric_col_b, metric_col_c = st.columns(3)
            metric_col_a.metric("Modo previsto", next_execution_checklist_preview.get("checklist_mode", "-"))
            metric_col_b.metric("Documento chars", next_execution_checklist_preview.get("full_document_chars", 0))
            metric_col_c.metric("Chars reais enviados", next_execution_checklist_preview.get("context_chars_sent", 0))
            context_preview_value = str(next_execution_checklist_preview.get("context_preview") or "")
            if context_preview_value:
                st.text_area(
                    "Texto real previsto para envio ao modelo",
                    value=context_preview_value,
                    height=520,
                    disabled=True,
                    key="phase5_structured_checklist_real_execution_preview",
                )
            else:
                st.warning("Não foi possível estimar o texto real que será enviado ao modelo para o checklist.")

        elif active_structured_document_ids and not next_execution_summary_preview and not next_execution_extraction_preview:
            if selected_structured_task == "checklist":
                st.caption("Este é o contexto-base que será usado para montar o checklist antes da geração. Assim você consegue revisar o material de origem antes de rodar a análise.")
            else:
                st.caption("Este painel mostra o contexto montado pela pipeline estruturada com base na seleção atual.")
            metric_col_a, metric_col_b = st.columns(2)
            metric_col_a.metric("Docs selecionados", len(active_structured_document_ids))
            metric_col_b.metric("Chars do contexto", effective_structured_context_chars)
            st.caption(
                f"Estratégia: {structured_context_strategy} · blocos de origem: {effective_structured_context_blocks}"
            )

            if effective_structured_context_preview:
                st.text_area(
                    "Contexto que será enviado ao modelo",
                    value=effective_structured_context_preview,
                    height=520,
                    disabled=True,
                    key="phase5_structured_effective_context_preview",
                )
            else:
                st.warning("Nenhum contexto textual foi montado com a seleção atual.")
        else:
            st.info("Selecione um ou mais documentos para ver o contexto final que será enviado para a IA.")

    # Form for execution only
    with st.form("phase5_structured_form", clear_on_submit=False):
        st.markdown("### Executar análise estruturada")
        structured_submit = st.form_submit_button(
            "Run structured analysis",
            width="stretch",
            disabled=not can_run_structured,
        )

        if structured_submit:
            st.session_state["phase5_structured_input"] = structured_input_text
            progress_placeholder = st.empty()
            progress_bar = st.progress(0)
            displayed_progress = {"value": 0}

            def _structured_progress_callback(*, step: str, progress: float, detail: str = "") -> None:
                normalized = max(0.0, min(float(progress), 1.0))
                target_progress = int(normalized * 100)
                label = _format_structured_progress_label(selected_structured_task, step, detail)
                current_progress = displayed_progress["value"]

                if target_progress <= current_progress:
                    progress_placeholder.markdown(f"**{current_progress}%** · {label}")
                    return

                for next_progress in range(current_progress + 1, target_progress + 1):
                    displayed_progress["value"] = next_progress
                    progress_placeholder.markdown(f"**{next_progress}%** · {label}")
                    progress_bar.progress(next_progress)
                    time.sleep(STRUCTURED_PROGRESS_STEP_DELAY_S)

            structured_request = TaskExecutionRequest(
                task_type=selected_structured_task,
                input_text=structured_input_text,
                use_rag_context=False,
                use_document_context=bool(structured_use_documents and active_structured_document_ids),
                source_document_ids=list(active_structured_document_ids if structured_use_documents else []),
                context_strategy=structured_context_strategy,
                provider=structured_effective_provider,
                model=structured_execution_model,
                temperature=temperature,
                context_window=None if context_window_mode == "auto" else structured_context_window_cap,
                progress_callback=_structured_progress_callback,
                telemetry={
                    "current_stage": "structured_request_initialized",
                    "budget_routing_mode": structured_budget_decision.get("routing_mode"),
                    "budget_routing_reason": structured_budget_decision.get("reason"),
                    "budget_sensitivity": structured_budget_decision.get("sensitivity"),
                    "budget_quality_floor": structured_budget_decision.get("quality_floor"),
                    "budget_auto_degrade_applied": structured_budget_decision.get("auto_degrade_applied"),
                    "budget_context_pressure_ratio": structured_budget_decision.get("context_pressure_ratio"),
                    "budget_context_budget_chars": structured_budget_decision.get("context_budget_chars"),
                    "budget_provider_requested": selected_provider,
                    "budget_provider_effective": structured_effective_provider,
                    "budget_provider_switch_applied": bool(structured_provider_routing.get("provider_switch_applied")),
                    "budget_provider_switch_reason": structured_provider_routing.get("reason"),
                    "budget_quality_gate": structured_quality_gate,
                },
            )
            structured_shadow_summary = None
            try:
                structured_result = run_structured_execution_workflow(
                    structured_request,
                    strategy=selected_structured_execution_strategy,
                )
                if shadow_compare_structured:
                    alternate_strategy = (
                        "direct"
                        if selected_structured_execution_strategy == "langgraph_context_retry"
                        else "langgraph_context_retry"
                    )
                    progress_placeholder.markdown("**97%** · Executando comparação shadow direct vs LangGraph")
                    alternate_request = structured_request.model_copy(
                        update={
                            "progress_callback": None,
                            "telemetry": {"current_stage": "structured_shadow_initialized"},
                        }
                    )
                    alternate_structured_result = run_structured_execution_workflow(
                        alternate_request,
                        strategy=alternate_strategy,
                    )
                    structured_shadow_summary = _build_structured_shadow_summary(
                        structured_result,
                        alternate_structured_result,
                    )
                    metadata = structured_result.execution_metadata if isinstance(structured_result.execution_metadata, dict) else {}
                    structured_result.execution_metadata = {
                        **metadata,
                        "execution_shadow_summary": structured_shadow_summary,
                    }
                    phase55_langgraph_shadow_log_entries = append_langgraph_shadow_log_entry(
                        PHASE55_LANGGRAPH_SHADOW_LOG_PATH,
                        _build_structured_shadow_log_entry(
                            task_type=selected_structured_task,
                            query=structured_input_text,
                            provider=selected_provider,
                            model=selected_model,
                            document_ids=list(active_structured_document_ids if structured_use_documents else []),
                            shadow_summary=structured_shadow_summary,
                        ),
                    )
                    phase55_langgraph_shadow_log_summary = summarize_langgraph_shadow_log(phase55_langgraph_shadow_log_entries)
            except Exception as error:
                logger.exception("Structured execution failed")
                structured_error_message = build_ui_error_message("Falha na execução estruturada", error)
                structured_result = attempt_controlled_failure(
                    raw_response="",
                    task_type=selected_structured_task,
                    error_message=structured_error_message,
                )
                structured_result.execution_metadata = {
                    "provider": structured_effective_provider,
                    "model": structured_execution_model,
                    "execution_strategy_used": selected_structured_execution_strategy,
                    "context_strategy": structured_context_strategy,
                    "telemetry": {
                        "budget_routing_mode": structured_budget_decision.get("routing_mode"),
                        "budget_routing_reason": structured_budget_decision.get("reason"),
                        "budget_auto_degrade_applied": structured_budget_decision.get("auto_degrade_applied"),
                        "budget_alert_status": "warn",
                        "budget_alerts": [structured_error_message],
                        "timings_s": {},
                        "provider_calls": [],
                    },
                }
                st.error(structured_error_message)
            if displayed_progress["value"] < 100:
                for next_progress in range(displayed_progress["value"] + 1, 101):
                    displayed_progress["value"] = next_progress
                    progress_placeholder.markdown(f"**{next_progress}%** · Finalizando")
                    progress_bar.progress(next_progress)
                    time.sleep(STRUCTURED_PROGRESS_FINALIZE_DELAY_S)
            progress_bar.progress(100)
            progress_placeholder.markdown("**100%** · Finalizado")
            structured_result_metadata = structured_result.execution_metadata if isinstance(structured_result.execution_metadata, dict) else {}
            structured_result_telemetry = structured_result_metadata.get("telemetry") if isinstance(structured_result_metadata.get("telemetry"), dict) else {}
            structured_result_timings = structured_result_telemetry.get("timings_s") if isinstance(structured_result_telemetry.get("timings_s"), dict) else {}
            structured_total_latency = (
                structured_result_metadata.get("workflow_total_s")
                if isinstance(structured_result_metadata.get("workflow_total_s"), (int, float))
                else structured_result_timings.get("total_s")
                if isinstance(structured_result_timings.get("total_s"), (int, float))
                else None
            )
            structured_generation_latency = (
                structured_result_timings.get("provider_total_s")
                if isinstance(structured_result_timings.get("provider_total_s"), (int, float))
                else None
            )
            structured_provider_calls = structured_result_telemetry.get("provider_calls") if isinstance(structured_result_telemetry.get("provider_calls"), list) else []
            structured_prompt_chars = sum(
                int(call.get("prompt_chars") or 0)
                for call in structured_provider_calls
                if isinstance(call, dict) and isinstance(call.get("prompt_chars"), (int, float))
            )
            structured_context_chars = int(structured_result_metadata.get("context_chars_sent") or 0) if isinstance(structured_result_metadata.get("context_chars_sent"), (int, float)) else 0
            structured_usage_metrics = estimate_runtime_usage_metrics(
                prompt_chars=structured_prompt_chars,
                completion_chars=len(str(structured_result.raw_output_text or "")),
                context_chars=structured_context_chars,
                provider=str(structured_result_metadata.get("provider") or selected_provider),
                native_usage=aggregate_provider_call_native_usage(structured_provider_calls),
                chars_per_token=effective_rag_settings.context_chars_per_token,
            )
            structured_result_telemetry["budget_total_tokens"] = structured_usage_metrics.get("total_tokens")
            structured_result_telemetry["budget_cost_usd"] = structured_usage_metrics.get("cost_usd")
            structured_result_telemetry["budget_usage_source"] = structured_usage_metrics.get("usage_source")
            structured_result_telemetry["budget_cost_source"] = structured_usage_metrics.get("cost_source")
            structured_result_telemetry["budget_native_usage_available"] = structured_usage_metrics.get("native_usage_available")
            structured_budget_alerts = evaluate_budget_alerts(
                task_type=selected_structured_task,
                provider=str(structured_result_metadata.get("provider") or structured_effective_provider),
                total_tokens=int(structured_usage_metrics.get("total_tokens") or 0),
                cost_usd=(float(structured_usage_metrics.get("cost_usd")) if isinstance(structured_usage_metrics.get("cost_usd"), (int, float)) else None),
                latency_s=(float(structured_total_latency) if isinstance(structured_total_latency, (int, float)) else None),
                context_pressure_ratio=(float(structured_budget_decision.get("context_pressure_ratio")) if isinstance(structured_budget_decision.get("context_pressure_ratio"), (int, float)) else None),
                auto_degrade_applied=bool(structured_budget_decision.get("auto_degrade_applied")),
            )
            structured_result_telemetry["budget_alert_status"] = structured_budget_alerts.get("status")
            structured_result_telemetry["budget_alerts"] = structured_budget_alerts.get("alerts")
            structured_result_telemetry["budget_thresholds"] = structured_budget_alerts.get("thresholds")
            structured_document_runtime_signals = _build_document_runtime_signal_summary(
                list(active_structured_document_ids if structured_use_documents else []),
                document_preview_map,
            )
            structured_error_message = (
                structured_result.validation_error
                or structured_result.parsing_error
                or (structured_result.error.message if structured_result.error else None)
            )
            evidenceops_mcp_summary: dict[str, object] = {}
            if selected_structured_task == "document_agent" and isinstance(structured_result.validated_output, DocumentAgentPayload):
                evidenceops_entry = build_evidenceops_worklog_entry(
                    payload=structured_result.validated_output,
                    query=structured_input_text,
                    document_ids=list(active_structured_document_ids if structured_use_documents else []),
                    execution_metadata=structured_result_metadata,
                )
                try:
                    evidenceops_mcp_result, evidenceops_mcp_summary = register_evidenceops_entry_via_mcp(evidenceops_entry)
                    st.session_state[EVIDENCEOPS_MCP_LAST_ENTRY_STATE_KEY] = evidenceops_entry
                    st.session_state[EVIDENCEOPS_MCP_LAST_REGISTER_RESULT_STATE_KEY] = evidenceops_mcp_result
                    st.session_state[EVIDENCEOPS_MCP_LAST_TELEMETRY_STATE_KEY] = evidenceops_mcp_summary
                    if isinstance(structured_result_metadata, dict):
                        structured_result_metadata["evidenceops_mcp"] = {
                            **evidenceops_mcp_summary,
                            "register_result": evidenceops_mcp_result,
                        }
                except Exception as error:
                    logger.exception("EvidenceOps MCP registration failed; falling back to local stores")
                    append_evidenceops_worklog_entry(
                        PHASE95_EVIDENCEOPS_WORKLOG_PATH,
                        evidenceops_entry,
                    )
                    inserted_actions = append_evidenceops_actions_from_worklog_entry(
                        PHASE95_EVIDENCEOPS_ACTION_STORE_PATH,
                        evidenceops_entry,
                    )
                    evidenceops_mcp_summary = {
                        "server_name": "evidenceops-local-mcp",
                        "transport": "stdio",
                        "status": "fallback_local",
                        "tool_call_count": 1,
                        "read_call_count": 0,
                        "write_call_count": 1,
                        "error_call_count": 1,
                        "total_latency_s": 0.0,
                        "tool_names": ["register_evidenceops_entry"],
                        "error_message": str(error),
                        "fallback_actions_inserted": int(inserted_actions),
                    }
                    st.session_state[EVIDENCEOPS_MCP_LAST_ENTRY_STATE_KEY] = evidenceops_entry
                    st.session_state[EVIDENCEOPS_MCP_LAST_REGISTER_RESULT_STATE_KEY] = {
                        "fallback": True,
                        "actions_inserted": int(inserted_actions),
                    }
                    st.session_state[EVIDENCEOPS_MCP_LAST_TELEMETRY_STATE_KEY] = dict(evidenceops_mcp_summary)
                    if isinstance(structured_result_metadata, dict):
                        structured_result_metadata["evidenceops_mcp"] = dict(evidenceops_mcp_summary)
            append_runtime_execution_log_entry(
                RUNTIME_EXECUTION_LOG_PATH,
                _build_runtime_execution_log_entry(
                    flow_type="structured",
                    task_type=selected_structured_task,
                    provider=str(structured_result_metadata.get("provider") or selected_provider),
                    model=str(structured_result_metadata.get("model") or selected_model),
                    success=bool(structured_result.success),
                    latency_s=structured_total_latency,
                    generation_latency_s=structured_generation_latency,
                    context_window=structured_context_window_resolved,
                    context_window_mode=context_window_mode,
                    embedding_provider=str(embedding_provider_key or selected_embedding_provider),
                    embedding_model=selected_embedding_model,
                    rag_chunk_size=effective_rag_settings.chunk_size,
                    rag_chunk_overlap=effective_rag_settings.chunk_overlap,
                    rag_top_k=effective_rag_settings.top_k,
                    prompt_chars=int(structured_usage_metrics.get("prompt_chars") or 0),
                    output_chars=int(structured_usage_metrics.get("output_chars") or 0),
                    context_chars=int(structured_usage_metrics.get("context_chars") or 0),
                    prompt_tokens=int(structured_usage_metrics.get("prompt_tokens") or 0),
                    completion_tokens=int(structured_usage_metrics.get("completion_tokens") or 0),
                    total_tokens=int(structured_usage_metrics.get("total_tokens") or 0),
                    usage_source=str(structured_usage_metrics.get("usage_source") or "estimated_chars"),
                    cost_usd=(float(structured_usage_metrics.get("cost_usd")) if isinstance(structured_usage_metrics.get("cost_usd"), (int, float)) else None),
                    cost_source=str(structured_usage_metrics.get("cost_source") or "pricing_not_configured"),
                    source_document_ids=list(active_structured_document_ids if structured_use_documents else []),
                    needs_review=(structured_result_metadata.get("needs_review") if isinstance(structured_result_metadata.get("needs_review"), bool) else None),
                    error_message=structured_error_message,
                    extra={
                        "execution_strategy_used": structured_result_metadata.get("execution_strategy_used"),
                        "workflow_id": structured_result_metadata.get("workflow_id"),
                        "workflow_attempts": structured_result_metadata.get("workflow_attempts"),
                        "workflow_context_strategies": structured_result_metadata.get("workflow_context_strategies"),
                        "agent_intent": structured_result_metadata.get("agent_intent"),
                        "agent_tool": structured_result_metadata.get("agent_tool"),
                        "agent_answer_mode": structured_result_metadata.get("agent_answer_mode"),
                        "needs_review_reason": structured_result_metadata.get("needs_review_reason"),
                        "budget_routing_mode": structured_budget_decision.get("routing_mode"),
                        "budget_routing_reason": structured_budget_decision.get("reason"),
                        "budget_sensitivity": structured_budget_decision.get("sensitivity"),
                        "budget_quality_floor": structured_budget_decision.get("quality_floor"),
                        "budget_auto_degrade_applied": structured_budget_decision.get("auto_degrade_applied"),
                        "context_budget_chars": structured_budget_decision.get("context_budget_chars"),
                        "estimated_context_chars": structured_budget_decision.get("estimated_context_chars"),
                        "context_pressure_ratio": structured_budget_decision.get("context_pressure_ratio"),
                        "document_context_strategy": structured_context_strategy,
                        "structured_context_blocks": effective_structured_context_blocks,
                        "estimated_document_chars": estimated_structured_document_chars,
                        "provider_requested": selected_provider,
                        "model_requested": selected_model,
                        "provider_switch_applied": bool(structured_provider_routing.get("provider_switch_applied")),
                        "provider_switch_reason": structured_provider_routing.get("reason"),
                        "quality_gate_status": structured_quality_gate.get("status"),
                        "quality_gate_reason": structured_quality_gate.get("reason"),
                        "quality_gate_pass_rate": structured_quality_gate.get("pass_rate"),
                        "quality_gate_min_pass_rate": structured_quality_gate.get("min_pass_rate"),
                        "quality_gate_recent_runs": structured_quality_gate.get("recent_runs"),
                        "budget_alert_status": structured_budget_alerts.get("status"),
                        "budget_alerts": structured_budget_alerts.get("alerts"),
                        "budget_thresholds": structured_budget_alerts.get("thresholds"),
                        "mcp_server": evidenceops_mcp_summary.get("server_name"),
                        "mcp_transport": evidenceops_mcp_summary.get("transport"),
                        "mcp_status": evidenceops_mcp_summary.get("status"),
                        "mcp_tool_call_count": evidenceops_mcp_summary.get("tool_call_count"),
                        "mcp_read_call_count": evidenceops_mcp_summary.get("read_call_count"),
                        "mcp_write_call_count": evidenceops_mcp_summary.get("write_call_count"),
                        "mcp_error_call_count": evidenceops_mcp_summary.get("error_call_count"),
                        "mcp_total_latency_s": evidenceops_mcp_summary.get("total_latency_s"),
                        "mcp_tool_names": evidenceops_mcp_summary.get("tool_names"),
                        **structured_document_runtime_signals,
                    },
                ),
            )
            st.session_state[STRUCTURED_RESULT_STATE_KEY] = structured_result.model_dump(mode="json")
            default_mode = structured_result.primary_render_mode or "json"
            st.session_state[STRUCTURED_RENDER_MODE_STATE_KEY] = default_mode

    stored_structured_result = st.session_state.get(STRUCTURED_RESULT_STATE_KEY)
    if stored_structured_result:
        structured_result = StructuredResult.model_validate(stored_structured_result)
        st.markdown("**3. Structured output**")
        available_modes = sorted(
            [mode for mode in structured_result.available_render_modes if mode.available],
            key=lambda mode: mode.priority,
        )
        if available_modes:
            selected_render_mode = st.radio(
                "Render mode",
                options=[mode.mode for mode in available_modes],
                index=next(
                    (
                        index
                        for index, mode in enumerate(available_modes)
                        if mode.mode == st.session_state.get(STRUCTURED_RENDER_MODE_STATE_KEY, structured_result.primary_render_mode)
                    ),
                    0,
                ),
                format_func=lambda mode_key: next(
                    (mode.label for mode in available_modes if mode.mode == mode_key),
                    mode_key,
                ),
                horizontal=True,
                key="phase5_structured_render_mode_selector",
            )
        else:
            selected_render_mode = structured_result.primary_render_mode or "json"
        st.session_state[STRUCTURED_RENDER_MODE_STATE_KEY] = selected_render_mode
        render_structured_result(structured_result, requested_mode=selected_render_mode)

with comparison_tab:
    st.caption("5. Benchmarks & Model Comparison: compare múltiplos modelos/providers lado a lado usando o mesmo prompt e, opcionalmente, o mesmo grounding documental.")
    st.info(
        "Slice inicial da Fase 7: comparação local entre combinações de provider/model com métricas básicas de latência, tamanho de resposta e aderência ao formato pedido."
    )
    st.caption(
        "A Fase 7 agora também suporta presets por caso de uso e classificação automática de família de quantização para tornar o benchmark mais repetível e mais fácil de defender."
    )

    st.caption("AI Lab deck exports: esta superfície prioriza o executive review de benchmark/evals. Os decks de workflows de negócio migram para o produto em Gradio.")
    render_executive_deck_generation_panel(
        model_comparison_entries=phase7_model_comparison_log_entries,
        phase8_eval_db_path=PHASE8_EVAL_DB_PATH,
        structured_result=st.session_state.get(STRUCTURED_RESULT_STATE_KEY),
        phase95_evidenceops_worklog_path=PHASE95_EVIDENCEOPS_WORKLOG_PATH,
        phase95_evidenceops_action_store_path=PHASE95_EVIDENCEOPS_ACTION_STORE_PATH,
        settings=presentation_export_settings,
        allowed_export_kinds=[DEFAULT_PRESENTATION_EXPORT_KIND],
        surface_label="AI Lab",
    )

    comparison_document_ids_default = _normalize_document_selection(
        all_indexed_document_ids,
        st.session_state.get(PHASE7_DOCUMENT_SELECTION_STATE_KEY),
        default_to_all=False,
    )
    comparison_candidate_options = [
        _build_model_comparison_candidate_option(provider_key, model_name)
        for provider_key, model_names in models_by_provider.items()
        for model_name in model_names
        if model_name
    ]
    default_candidate_options: list[str] = []
    current_candidate = _build_model_comparison_candidate_option(selected_provider, selected_model)
    if current_candidate in comparison_candidate_options:
        default_candidate_options.append(current_candidate)
    for option in comparison_candidate_options:
        if option not in default_candidate_options:
            default_candidate_options.append(option)
        if len(default_candidate_options) >= 2:
            break

    with st.expander("Fase 7 · histórico local de comparação entre modelos", expanded=False):
        st.caption(f"Log local: `{PHASE7_MODEL_COMPARISON_LOG_PATH.name}`")
        st.write(phase7_model_comparison_log_summary)
        if phase7_model_comparison_log_summary.get("total_candidates"):
            summary_col_1, summary_col_2, summary_col_3, summary_col_4 = st.columns(4)
            summary_col_1.metric("Runs", int(phase7_model_comparison_log_summary.get("total_runs") or 0))
            summary_col_2.metric("Candidatos", int(phase7_model_comparison_log_summary.get("total_candidates") or 0))
            summary_col_3.metric("Sucesso médio", f"{float(phase7_model_comparison_log_summary.get('success_rate', 0.0)):.0%}")
            summary_col_4.metric("Latência média", f"{float(phase7_model_comparison_log_summary.get('avg_latency_s', 0.0)):.2f}s")

            top_provider = phase7_model_comparison_log_summary.get("top_provider") if isinstance(phase7_model_comparison_log_summary.get("top_provider"), dict) else None
            top_model = phase7_model_comparison_log_summary.get("top_model") if isinstance(phase7_model_comparison_log_summary.get("top_model"), dict) else None
            top_format = phase7_model_comparison_log_summary.get("top_format") if isinstance(phase7_model_comparison_log_summary.get("top_format"), dict) else None
            if top_provider:
                st.caption(
                    f"Top provider agregado: {top_provider.get('provider')} · success={float(top_provider.get('success_rate', 0.0)):.0%} · latency={float(top_provider.get('avg_latency_s', 0.0)):.2f}s"
                )
            if top_model:
                st.caption(
                    f"Top model agregado: {top_model.get('model')} · success={float(top_model.get('success_rate', 0.0)):.0%} · adherence={float(top_model.get('avg_format_adherence', 0.0)):.0%}"
                )
            if top_format:
                st.caption(
                    f"Top formato agregado: {top_format.get('response_format')} · success={float(top_format.get('success_rate', 0.0)):.0%}"
                )
            top_benchmark_use_case = phase7_model_comparison_log_summary.get("top_benchmark_use_case") if isinstance(phase7_model_comparison_log_summary.get("top_benchmark_use_case"), dict) else None
            if top_benchmark_use_case:
                top_use_case_key = str(top_benchmark_use_case.get("benchmark_use_case") or "ad_hoc")
                top_use_case_label = MODEL_COMPARISON_USE_CASE_PRESETS.get(top_use_case_key, {}).get("label", top_use_case_key)
                st.caption(
                    f"Top caso de uso agregado: {top_use_case_label} · success={float(top_benchmark_use_case.get('success_rate', 0.0)):.0%} · latency={float(top_benchmark_use_case.get('avg_latency_s', 0.0)):.2f}s"
                )

            provider_leaderboard = phase7_model_comparison_log_summary.get("provider_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("provider_leaderboard"), list) else []
            model_leaderboard = phase7_model_comparison_log_summary.get("model_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("model_leaderboard"), list) else []
            format_leaderboard = phase7_model_comparison_log_summary.get("format_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("format_leaderboard"), list) else []
            if provider_leaderboard:
                st.write("**Leaderboard por provider**")
                st.dataframe(provider_leaderboard[:5], width="stretch")
            if model_leaderboard:
                st.write("**Leaderboard por model**")
                st.dataframe(model_leaderboard[:5], width="stretch")
            if format_leaderboard:
                st.write("**Leaderboard por formato**")
                st.dataframe(format_leaderboard[:5], width="stretch")
            runtime_bucket_leaderboard = phase7_model_comparison_log_summary.get("runtime_bucket_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("runtime_bucket_leaderboard"), list) else []
            top_runtime_bucket = phase7_model_comparison_log_summary.get("top_runtime_bucket") if isinstance(phase7_model_comparison_log_summary.get("top_runtime_bucket"), dict) else None
            if top_runtime_bucket:
                runtime_bucket_label = MODEL_COMPARISON_RUNTIME_BUCKET_LABELS.get(
                    str(top_runtime_bucket.get("runtime_bucket") or ""),
                    str(top_runtime_bucket.get("runtime_bucket") or "runtime"),
                )
                st.caption(
                    f"Top bucket de runtime: {runtime_bucket_label} · success={float(top_runtime_bucket.get('success_rate', 0.0)):.0%} · latency={float(top_runtime_bucket.get('avg_latency_s', 0.0)):.2f}s"
                )
            if runtime_bucket_leaderboard:
                st.write("**Leaderboard por bucket de runtime**")
                st.dataframe(
                    [
                        {
                            **item,
                            "runtime_bucket_label": MODEL_COMPARISON_RUNTIME_BUCKET_LABELS.get(
                                str(item.get("runtime_bucket") or ""),
                                str(item.get("runtime_bucket") or "runtime"),
                            ),
                        }
                        for item in runtime_bucket_leaderboard[:5]
                    ],
                    width="stretch",
                )
            quantization_family_leaderboard = phase7_model_comparison_log_summary.get("quantization_family_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("quantization_family_leaderboard"), list) else []
            top_quantization_family = phase7_model_comparison_log_summary.get("top_quantization_family") if isinstance(phase7_model_comparison_log_summary.get("top_quantization_family"), dict) else None
            if top_quantization_family:
                quantization_label = MODEL_COMPARISON_QUANTIZATION_LABELS.get(
                    str(top_quantization_family.get("quantization_family") or ""),
                    str(top_quantization_family.get("quantization_family") or "quantization"),
                )
                st.caption(
                    f"Top família de quantização: {quantization_label} · success={float(top_quantization_family.get('success_rate', 0.0)):.0%} · latency={float(top_quantization_family.get('avg_latency_s', 0.0)):.2f}s"
                )
            if quantization_family_leaderboard:
                st.write("**Leaderboard por família de quantização**")
                st.dataframe(
                    [
                        {
                            **item,
                            "quantization_family_label": MODEL_COMPARISON_QUANTIZATION_LABELS.get(
                                str(item.get("quantization_family") or ""),
                                str(item.get("quantization_family") or "quantization"),
                            ),
                        }
                        for item in quantization_family_leaderboard[:5]
                    ],
                    width="stretch",
                )
            retrieval_strategy_leaderboard = phase7_model_comparison_log_summary.get("retrieval_strategy_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("retrieval_strategy_leaderboard"), list) else []
            embedding_provider_leaderboard = phase7_model_comparison_log_summary.get("embedding_provider_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("embedding_provider_leaderboard"), list) else []
            embedding_model_leaderboard = phase7_model_comparison_log_summary.get("embedding_model_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("embedding_model_leaderboard"), list) else []
            prompt_profile_leaderboard = phase7_model_comparison_log_summary.get("prompt_profile_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("prompt_profile_leaderboard"), list) else []
            document_usage_leaderboard = phase7_model_comparison_log_summary.get("document_usage_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("document_usage_leaderboard"), list) else []
            benchmark_use_case_leaderboard = phase7_model_comparison_log_summary.get("benchmark_use_case_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("benchmark_use_case_leaderboard"), list) else []
            if retrieval_strategy_leaderboard:
                st.write("**Leaderboard por retrieval strategy**")
                st.dataframe(retrieval_strategy_leaderboard[:5], width="stretch")
            if embedding_provider_leaderboard:
                st.write("**Leaderboard por embedding provider**")
                st.dataframe(embedding_provider_leaderboard[:5], width="stretch")
            if embedding_model_leaderboard:
                st.write("**Leaderboard por embedding model**")
                st.dataframe(embedding_model_leaderboard[:5], width="stretch")
            if prompt_profile_leaderboard:
                st.write("**Leaderboard por prompt profile**")
                st.dataframe(prompt_profile_leaderboard[:5], width="stretch")
            if document_usage_leaderboard:
                st.write("**Leaderboard por uso de documentos**")
                st.dataframe(document_usage_leaderboard[:5], width="stretch")
            if benchmark_use_case_leaderboard:
                st.write("**Leaderboard por caso de uso do benchmark**")
                st.dataframe(benchmark_use_case_leaderboard[:5], width="stretch")
        if phase7_model_comparison_log_entries:
            recent_entries = list(reversed(phase7_model_comparison_log_entries[-10:]))
            st.dataframe(
                [
                    {
                        "timestamp": entry.get("timestamp"),
                        "use_case": entry.get("benchmark_use_case"),
                        "profile": entry.get("prompt_profile"),
                        "format": entry.get("response_format"),
                        "docs": len(entry.get("document_ids") or []),
                        "candidates": len(entry.get("candidate_results") or []),
                        "success_rate": (entry.get("aggregate") or {}).get("success_rate") if isinstance(entry.get("aggregate"), dict) else None,
                        "avg_latency_s": (entry.get("aggregate") or {}).get("avg_latency_s") if isinstance(entry.get("aggregate"), dict) else None,
                        "prompt": entry.get("prompt_text"),
                    }
                    for entry in recent_entries
                ],
                width="stretch",
            )
            if st.button("Limpar histórico de comparação da Fase 7", key="phase7_clear_model_comparison_log"):
                clear_model_comparison_log(PHASE7_MODEL_COMPARISON_LOG_PATH)
                st.rerun()
        else:
            st.caption("Nenhuma comparação registrada ainda.")

    with st.expander("Fase 7 · benchmark de estratégias adjacentes", expanded=False):
        retrieval_metric_col_1, retrieval_metric_col_2, retrieval_metric_col_3 = st.columns(3)
        retrieval_metric_col_1.metric("Retrieval shadow runs", int(phase55_shadow_log_summary.get("total_runs") or 0))
        retrieval_metric_col_2.metric("Same top-1", f"{float(phase55_shadow_log_summary.get('same_top_1_rate', 0.0)):.0%}")
        retrieval_metric_col_3.metric("Overlap médio", f"{float(phase55_shadow_log_summary.get('avg_overlap_ratio', 0.0)):.0%}")
        st.caption("Manual hybrid vs LangChain/Chroma: benchmark de recuperação reaproveitado como evidência comparativa da Fase 7.")
        if phase55_shadow_log_summary.get("strategy_pairs"):
            st.write({
                "retrieval_strategy_pairs": phase55_shadow_log_summary.get("strategy_pairs"),
                "retrieval_alternate_fallbacks": phase55_shadow_log_summary.get("alternate_fallbacks"),
            })

        langgraph_metric_col_1, langgraph_metric_col_2, langgraph_metric_col_3, langgraph_metric_col_4 = st.columns(4)
        langgraph_metric_col_1.metric("LangGraph shadow runs", int(phase55_langgraph_shadow_log_summary.get("total_runs") or 0))
        langgraph_metric_col_2.metric("Same success", f"{float(phase55_langgraph_shadow_log_summary.get('same_success_rate', 0.0)):.0%}")
        langgraph_metric_col_3.metric("Δ latência média", f"{float(phase55_langgraph_shadow_log_summary.get('avg_latency_delta_s', 0.0)):.2f}s")
        langgraph_metric_col_4.metric("Δ qualidade média", f"{float(phase55_langgraph_shadow_log_summary.get('avg_quality_delta', 0.0)):.3f}")
        st.caption("Direct vs LangGraph context retry: benchmark estruturado reaproveitado como benchmark de estratégia da Fase 7.")
        if phase55_langgraph_shadow_log_summary.get("strategy_pairs"):
            st.write({
                "langgraph_strategy_pairs": phase55_langgraph_shadow_log_summary.get("strategy_pairs"),
                "langgraph_alternate_fallbacks": phase55_langgraph_shadow_log_summary.get("alternate_fallbacks"),
            })

    comparison_use_case = st.selectbox(
        "Caso de uso do benchmark",
        options=list(MODEL_COMPARISON_USE_CASE_PRESETS.keys()),
        index=0,
        format_func=lambda key: MODEL_COMPARISON_USE_CASE_PRESETS[key]["label"],
        key="phase7_model_comparison_use_case",
        help="Use presets para criar comparações repetíveis por tipo de tarefa.",
    )
    selected_use_case_preset = MODEL_COMPARISON_USE_CASE_PRESETS.get(comparison_use_case, MODEL_COMPARISON_USE_CASE_PRESETS["ad_hoc"])
    last_applied_use_case = st.session_state.get("phase7_model_comparison_last_applied_use_case")
    if comparison_use_case != last_applied_use_case:
        st.session_state["phase7_model_comparison_last_applied_use_case"] = comparison_use_case
        if comparison_use_case != "ad_hoc":
            preset_prompt_text = str(selected_use_case_preset.get("prompt_text") or "")
            preset_prompt_profile = str(selected_use_case_preset.get("prompt_profile") or "")
            preset_response_format = str(selected_use_case_preset.get("response_format") or "")
            st.session_state["phase7_model_comparison_prompt"] = preset_prompt_text
            st.session_state["phase7_model_comparison_prompt_text"] = preset_prompt_text
            if preset_prompt_profile in prompt_profiles:
                st.session_state["phase7_model_comparison_prompt_profile"] = preset_prompt_profile
            if preset_response_format in MODEL_COMPARISON_FORMAT_OPTIONS:
                st.session_state["phase7_model_comparison_response_format"] = preset_response_format
            st.rerun()
    comparison_prompt_text = st.text_area(
        "Prompt para comparar",
        value=st.session_state.get(
            "phase7_model_comparison_prompt_text",
            st.session_state.get("phase7_model_comparison_prompt", ""),
        ),
        height=180,
        placeholder="Ex.: Resuma os principais riscos e próximos passos em bullets curtos.",
        key="phase7_model_comparison_prompt_text",
    )
    st.caption(str(selected_use_case_preset.get("description") or ""))
    if comparison_use_case != "ad_hoc":
        st.caption(f"Preset sugerido: formato `{selected_use_case_preset.get('response_format')}` · profile `{selected_use_case_preset.get('prompt_profile')}`")
        if not comparison_prompt_text.strip():
            comparison_prompt_text = str(selected_use_case_preset.get("prompt_text") or "")
    comparison_prompt_profile = st.selectbox(
        "Perfil de prompt da comparação",
        options=list(prompt_profiles.keys()),
        index=list(prompt_profiles.keys()).index(
            selected_use_case_preset.get("prompt_profile")
            if comparison_use_case != "ad_hoc" and selected_use_case_preset.get("prompt_profile") in prompt_profiles
            else selected_prompt_profile if selected_prompt_profile in prompt_profiles else list(prompt_profiles.keys())[0]
        ),
        format_func=lambda key: prompt_profiles[key]["label"],
        key="phase7_model_comparison_prompt_profile",
    )
    comparison_response_format = st.selectbox(
        "Formato desejado da resposta",
        options=list(MODEL_COMPARISON_FORMAT_OPTIONS.keys()),
        index=list(MODEL_COMPARISON_FORMAT_OPTIONS.keys()).index(
            selected_use_case_preset.get("response_format")
            if comparison_use_case != "ad_hoc" and selected_use_case_preset.get("response_format") in MODEL_COMPARISON_FORMAT_OPTIONS
            else list(MODEL_COMPARISON_FORMAT_OPTIONS.keys())[0]
        ),
        format_func=lambda key: MODEL_COMPARISON_FORMAT_OPTIONS.get(key, key),
        key="phase7_model_comparison_response_format",
    )
    comparison_candidates = st.multiselect(
        "Combinações de provider/model para comparar",
        options=comparison_candidate_options,
        default=default_candidate_options,
        format_func=lambda option: _format_model_comparison_candidate_option(option, provider_options),
        key="phase7_model_comparison_candidates",
        help="Selecione pelo menos 2 combinações para comparar lado a lado.",
    )
    comparison_use_documents = st.checkbox(
        "Usar documentos indexados na comparação",
        value=False,
        disabled=not bool(all_indexed_document_ids),
        key="phase7_model_comparison_use_documents",
    )
    if comparison_use_documents and all_indexed_document_ids:
        comparison_document_ids = st.multiselect(
            "Documentos para grounding da comparação",
            options=all_indexed_document_ids,
            default=comparison_document_ids_default,
            format_func=lambda item: document_labels.get(item, item),
            key="phase7_model_comparison_document_selector",
        )
        st.session_state[PHASE7_DOCUMENT_SELECTION_STATE_KEY] = comparison_document_ids
    else:
        comparison_document_ids = []
        st.session_state[PHASE7_DOCUMENT_SELECTION_STATE_KEY] = []

    comparison_effective_context_window, comparison_context_window_cap = _resolve_chat_context_window(
        provider=selected_provider,
        mode=context_window_mode,
        manual_context_window=context_window,
        document_ids=comparison_document_ids,
        input_text=comparison_prompt_text,
        rag_index=rag_index,
    )
    st.caption(
        f"Contexto da comparação: modo `{context_window_mode}` · resolvido em `{comparison_effective_context_window}` · cap `{comparison_context_window_cap}`"
    )

    comparison_can_run = bool(comparison_prompt_text.strip()) and len(comparison_candidates) >= 2
    if comparison_candidates and len(comparison_candidates) < 2:
        st.warning("Selecione pelo menos 2 combinações de provider/model para comparar lado a lado.")

    if st.button("Executar comparação entre modelos", disabled=not comparison_can_run, key="phase7_run_model_comparison"):
        st.session_state["phase7_model_comparison_prompt"] = comparison_prompt_text
        retrieved_chunks_for_comparison: list[dict[str, object]] = []
        if comparison_use_documents and comparison_document_ids and embedding_compatibility.get("compatible", True):
            try:
                retrieval_details = retrieve_relevant_chunks_detailed(
                    query=comparison_prompt_text,
                    rag_index=rag_index,
                    settings=effective_rag_settings,
                    embedding_provider=embedding_provider,
                    document_ids=comparison_document_ids,
                    file_types=None,
                )
                retrieved_chunks_for_comparison = retrieval_details.get("chunks") or []
            except Exception as error:
                logger.exception("Model comparison retrieval failed; continuing without document grounding")
                st.warning(build_ui_error_message("A comparação seguirá sem grounding documental porque o retrieval falhou", error))
        elif comparison_use_documents and comparison_document_ids and not embedding_compatibility.get("compatible", True):
            st.warning("A comparação seguirá sem grounding documental porque o embedding ativo não é compatível com o índice atual.")

        comparison_progress = st.progress(0)
        comparison_status = st.empty()
        comparison_results: list[dict[str, object]] = []
        total_candidates = len(comparison_candidates)
        for index, candidate_option in enumerate(comparison_candidates, start=1):
            provider_key, model_name = _parse_model_comparison_candidate_option(candidate_option)
            comparison_status.caption(
                f"Comparando {index}/{total_candidates}: {_format_model_comparison_candidate_option(candidate_option, provider_options)}"
            )
            comparison_results.append(
                run_model_comparison_candidate(
                    registry=chat_capable_registry,
                    provider_name=provider_key,
                    model_name=model_name,
                    prompt_profile=comparison_prompt_profile,
                    prompt_text=comparison_prompt_text,
                    benchmark_use_case=comparison_use_case,
                    response_format=comparison_response_format,
                    temperature=temperature,
                    context_window=comparison_effective_context_window,
                    retrieved_chunks=retrieved_chunks_for_comparison,
                    rag_settings=effective_rag_settings,
                )
            )
            comparison_progress.progress(int((index / max(total_candidates, 1)) * 100))

        comparison_status.caption("Comparação finalizada.")
        aggregate = summarize_model_comparison_results(comparison_results)
        phase7_model_comparison_log_entries = append_model_comparison_log_entry(
            PHASE7_MODEL_COMPARISON_LOG_PATH,
            _build_model_comparison_log_entry(
                prompt_text=comparison_prompt_text,
                benchmark_use_case=comparison_use_case,
                prompt_profile=comparison_prompt_profile,
                response_format=comparison_response_format,
                retrieval_strategy=selected_retrieval_strategy,
                embedding_provider=str(embedding_provider_key or selected_embedding_provider),
                embedding_model=selected_embedding_model,
                embedding_context_window=selected_embedding_context_window,
                context_window_mode=context_window_mode,
                context_window_resolved=comparison_effective_context_window,
                use_documents=bool(comparison_use_documents and comparison_document_ids),
                document_ids=list(comparison_document_ids),
                candidate_results=comparison_results,
                aggregate=aggregate,
            ),
        )
        phase7_model_comparison_log_summary = summarize_model_comparison_log(phase7_model_comparison_log_entries)
        st.session_state[MODEL_COMPARISON_RESULT_STATE_KEY] = {
            "benchmark_use_case": comparison_use_case,
            "prompt_text": comparison_prompt_text,
            "prompt_profile": comparison_prompt_profile,
            "response_format": comparison_response_format,
            "document_ids": list(comparison_document_ids),
            "candidate_results": comparison_results,
            "aggregate": aggregate,
        }

    stored_model_comparison_result = st.session_state.get(MODEL_COMPARISON_RESULT_STATE_KEY)
    if isinstance(stored_model_comparison_result, dict):
        aggregate = stored_model_comparison_result.get("aggregate") if isinstance(stored_model_comparison_result.get("aggregate"), dict) else {}
        candidate_results = stored_model_comparison_result.get("candidate_results") if isinstance(stored_model_comparison_result.get("candidate_results"), list) else []
        stored_use_case = str(stored_model_comparison_result.get("benchmark_use_case") or "ad_hoc")
        stored_use_case_label = MODEL_COMPARISON_USE_CASE_PRESETS.get(stored_use_case, {}).get("label", stored_use_case)
        st.markdown("### Resultado da comparação")
        st.caption(f"Caso de uso desta execução: {stored_use_case_label}")
        metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
        metric_col_1.metric("Candidatos", aggregate.get("total_candidates", 0))
        metric_col_2.metric("Taxa de sucesso", f"{float(aggregate.get('success_rate', 0.0)):.0%}")
        metric_col_3.metric("Latência média", f"{float(aggregate.get('avg_latency_s', 0.0)):.2f}s")
        metric_col_4.metric("Aderência média", f"{float(aggregate.get('avg_format_adherence', 0.0)):.0%}")
        if comparison_use_documents:
            st.caption(f"Groundedness média: {float(aggregate.get('avg_groundedness_score', 0.0)):.0%}")
        if comparison_response_format == "json":
            st.caption(f"Schema adherence média: {float(aggregate.get('avg_schema_adherence', 0.0)):.0%}")
        st.caption(f"Use-case fit médio: {float(aggregate.get('avg_use_case_fit_score', 0.0)):.0%}")

        best_latency = aggregate.get("best_latency_candidate") if isinstance(aggregate.get("best_latency_candidate"), dict) else None
        best_format = aggregate.get("best_format_candidate") if isinstance(aggregate.get("best_format_candidate"), dict) else None
        best_overall = aggregate.get("best_overall_candidate") if isinstance(aggregate.get("best_overall_candidate"), dict) else None
        if best_latency:
            st.caption(
                f"Melhor latência: {best_latency.get('provider')} · {best_latency.get('model')} · {best_latency.get('latency_s')}s"
            )
        if best_format:
            st.caption(
                f"Melhor aderência ao formato: {best_format.get('provider')} · {best_format.get('model')} · {float(best_format.get('format_adherence', 0.0)):.0%}"
            )
        if best_overall:
            st.caption(
                f"Melhor geral: {best_overall.get('provider')} · {best_overall.get('model')} · score={float(best_overall.get('comparison_score', 0.0)):.3f}"
            )

        candidate_ranking = aggregate.get("candidate_ranking") if isinstance(aggregate.get("candidate_ranking"), list) else []
        if candidate_ranking:
            with st.expander("Ranking consolidado da execução", expanded=False):
                st.dataframe(candidate_ranking, width="stretch")

        columns_count = min(3, max(1, len(candidate_results)))
        cols = st.columns(columns_count)
        for index, candidate in enumerate(candidate_results):
            with cols[index % columns_count]:
                with st.container(border=True):
                    st.write(
                        f"**{candidate.get('provider_label') or candidate.get('provider_effective')} · {candidate.get('model_effective')}**"
                    )
                    st.caption(
                        f"{MODEL_COMPARISON_RUNTIME_BUCKET_LABELS.get(str(candidate.get('runtime_bucket') or ''), str(candidate.get('runtime_bucket') or 'runtime'))} · {MODEL_COMPARISON_QUANTIZATION_LABELS.get(str(candidate.get('quantization_family') or ''), str(candidate.get('quantization_family') or 'quantization'))} · success={candidate.get('success')} · latency={candidate.get('latency_s')}s · adherence={float(candidate.get('format_adherence', 0.0)):.0%}"
                    )
                    st.caption(
                        f"chars={candidate.get('output_chars')} · words={candidate.get('output_words')} · used_chunks={candidate.get('used_chunks')} · grounded={float(candidate.get('groundedness_score', 0.0)):.0%} · use-case-fit={float(candidate.get('use_case_fit_score', 0.0)):.0%}"
                    )
                    if isinstance(candidate.get("schema_adherence"), (int, float)):
                        st.caption(f"schema={float(candidate.get('schema_adherence', 0.0)):.0%}")
                    if candidate.get("error"):
                        st.error(str(candidate.get("error")))
                    st.text_area(
                        f"comparison_output_{index}",
                        value=str(candidate.get("response_text") or ""),
                        height=260,
                        disabled=True,
                        label_visibility="collapsed",
                    )

with evals_tab:
    st.caption("6. Evals & Diagnosis: acompanhe suites, pass/warn/fail trends e sinais de quality gate do sistema.")
    if not phase8_eval_entries:
        st.info("Nenhuma run de eval registrada ainda. Use os scripts/suites da Fase 8 para alimentar esta visão diagnóstica.")
    else:
        eval_metric_col_1, eval_metric_col_2, eval_metric_col_3, eval_metric_col_4 = st.columns(4)
        eval_metric_col_1.metric("Eval runs", int(phase8_eval_summary.get("total_runs") or 0))
        eval_metric_col_2.metric("PASS", f"{float(phase8_eval_summary.get('pass_rate') or 0.0):.0%}")
        eval_metric_col_3.metric("WARN", f"{float(phase8_eval_summary.get('warn_rate') or 0.0):.0%}")
        eval_metric_col_4.metric("FAIL", f"{float(phase8_eval_summary.get('fail_rate') or 0.0):.0%}")

        eval_metric_col_5, eval_metric_col_6, eval_metric_col_7 = st.columns(3)
        eval_metric_col_5.metric("Needs review", f"{float(phase8_eval_summary.get('needs_review_rate') or 0.0):.0%}")
        eval_metric_col_6.metric("Avg score ratio", f"{float(phase8_eval_summary.get('avg_score_ratio') or 0.0):.0%}")
        eval_metric_col_7.metric("Avg latency", f"{float(phase8_eval_summary.get('avg_latency_s') or 0.0):.2f}s")

        suite_leaderboard = phase8_eval_summary.get("suite_leaderboard") if isinstance(phase8_eval_summary.get("suite_leaderboard"), list) else []
        task_leaderboard = phase8_eval_summary.get("task_leaderboard") if isinstance(phase8_eval_summary.get("task_leaderboard"), list) else []
        if suite_leaderboard:
            st.markdown("### Suite leaderboard")
            st.dataframe(suite_leaderboard[:10], width="stretch")
        if task_leaderboard:
            st.markdown("### Task leaderboard")
            st.dataframe(task_leaderboard[:10], width="stretch")

        recent_eval_rows = [
            {
                "created_at": entry.get("created_at"),
                "suite_name": entry.get("suite_name"),
                "task_type": entry.get("task_type"),
                "case_name": entry.get("case_name"),
                "status": entry.get("status"),
                "score": entry.get("score"),
                "max_score": entry.get("max_score"),
                "needs_review": entry.get("needs_review"),
                "latency_s": entry.get("latency_s"),
            }
            for entry in phase8_eval_entries[:20]
        ]
        if recent_eval_rows:
            st.markdown("### Recent eval cases")
            st.dataframe(recent_eval_rows, width="stretch")

with evidenceops_tab:
    render_evidenceops_mcp_panel(
        console_state_key=EVIDENCEOPS_MCP_CONSOLE_STATE_KEY,
        last_mcp_entry=st.session_state.get(EVIDENCEOPS_MCP_LAST_ENTRY_STATE_KEY),
        last_mcp_register_result=st.session_state.get(EVIDENCEOPS_MCP_LAST_REGISTER_RESULT_STATE_KEY),
        last_mcp_telemetry=st.session_state.get(EVIDENCEOPS_MCP_LAST_TELEMETRY_STATE_KEY),
    )

runtime_snapshot = build_runtime_snapshot(
    selected_provider=selected_provider,
    selected_provider_label=selected_provider_label,
    provider_detail=provider_details.get(selected_provider),
    selected_model=selected_model,
    selected_embedding_provider=str(embedding_provider_key or selected_embedding_provider),
    selected_embedding_model=selected_embedding_model,
    selected_loader_strategy=selected_loader_strategy,
    selected_chunking_strategy=selected_chunking_strategy,
    selected_retrieval_strategy=selected_retrieval_strategy,
    selected_pdf_extraction_mode=selected_pdf_extraction_mode,
    chat_selected_document_ids=chat_selected_document_ids if 'chat_selected_document_ids' in locals() else [],
    structured_selected_document_ids=active_structured_document_ids if 'active_structured_document_ids' in locals() else [],
    selected_structured_task=selected_structured_task if 'selected_structured_task' in locals() else "",
    selected_structured_execution_strategy=selected_structured_execution_strategy if 'selected_structured_execution_strategy' in locals() else "direct",
    messages=get_chat_messages(),
    structured_result=structured_result if 'structured_result' in locals() else None,
    structured_task_registry=structured_task_registry,
    document_preview_map=document_preview_map,
    indexed_documents_count=len(indexed_documents),
    ollama_base_url=settings.base_url,
    default_vl_model=evidence_config.vl_model,
    default_ocr_backend=evidence_config.ocr_backend,
    phase6_document_agent_log_path=PHASE6_DOCUMENT_AGENT_LOG_PATH,
    phase95_evidenceops_action_store_path=PHASE95_EVIDENCEOPS_ACTION_STORE_PATH,
    phase95_evidenceops_repository_root=PHASE95_EVIDENCEOPS_REPOSITORY_ROOT,
    phase95_evidenceops_repository_snapshot_path=PHASE95_EVIDENCEOPS_REPOSITORY_SNAPSHOT_PATH,
    phase95_evidenceops_worklog_path=PHASE95_EVIDENCEOPS_WORKLOG_PATH,
    phase8_eval_db_path=PHASE8_EVAL_DB_PATH,
    runtime_execution_log_path=RUNTIME_EXECUTION_LOG_PATH,
)
render_runtime_sidebar_panel(runtime_snapshot)