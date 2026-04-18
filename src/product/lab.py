from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import get_evidenceops_external_settings
from src.product.models import ProductWorkflowRequest, ProductWorkflowResult
from src.product.service import run_product_workflow
from src.providers.registry import build_provider_registry, resolve_provider_runtime_profile
from src.rag.service import build_source_metadata, retrieve_relevant_chunks_detailed
from src.services.document_context import build_structured_document_context
from src.services.evidenceops_repository import (
    build_evidenceops_repository_snapshot,
    diff_evidenceops_repository_snapshots,
    list_evidenceops_repository_documents,
    summarize_evidenceops_repository_documents,
)
from src.storage.phase6_document_agent_log import load_document_agent_log, summarize_document_agent_log
from src.storage.phase8_eval_diagnosis import build_eval_diagnosis
from src.storage.phase8_eval_store import load_eval_runs, summarize_eval_runs
from src.storage.phase95_evidenceops_action_store import (
    append_evidenceops_actions_from_worklog_entry,
    load_evidenceops_actions,
    summarize_evidenceops_actions,
)
from src.storage.phase95_evidenceops_repository_snapshot import load_evidenceops_repository_snapshot
from src.storage.chat_history import load_chat_history as load_chat_history_store, save_chat_history
from src.storage.lab_state import (
    append_lab_chat_message,
    append_lab_workflow_run,
    create_lab_chat_session,
    get_lab_chat_session,
    get_lab_workflow_run,
    load_lab_chat_sessions,
    load_lab_workflow_runs,
    update_lab_chat_session_runtime,
)
from src.services.runtime_controls import build_effective_rag_settings
from src.services.runtime_economics import count_message_chars, estimate_runtime_usage_metrics, get_provider_native_usage_metrics
from src.storage.phase95_evidenceops_worklog import (
    append_evidenceops_worklog_entry,
    load_evidenceops_worklog,
    summarize_evidenceops_worklog,
)
from src.storage.runtime_execution_log import append_runtime_execution_log_entry, load_runtime_execution_log, summarize_runtime_execution_log
from src.storage.runtime_paths import (
    get_artifact_root,
    get_chat_history_path,
    get_lab_chat_sessions_path,
    get_lab_workflow_runs_path,
    get_phase6_document_agent_log_path,
    get_phase7_model_comparison_log_path,
    get_phase8_eval_db_path,
    get_phase95_evidenceops_action_store_path,
    get_phase95_evidenceops_repository_snapshot_path,
    get_phase95_evidenceops_worklog_path,
    get_product_workflow_history_path,
    get_rag_chroma_path,
    get_rag_store_path,
    get_runtime_controls_state_path,
    get_runtime_execution_log_path,
)

TOOL_LABELS: dict[str, str] = {
    "review_document_risks": "Document Risk Review",
    "extract_operational_tasks": "Action Plan Extraction",
    "compare_documents": "Document Comparison",
    "consult_documents": "Document Q&A",
    "review_policy_compliance": "Policy Compliance Review",
    "assist_technical_document": "Technical Assistance",
    "draft_business_response": "Business Response Drafting",
}

TOOL_DESCRIPTIONS: dict[str, str] = {
    "review_document_risks": "Grounded review of risks, gaps and blockers surfaced by the document agent.",
    "extract_operational_tasks": "Operational action-plan extraction with owners, deadlines and evidence gaps.",
    "compare_documents": "Structured comparison mode for policy or contract deltas.",
    "consult_documents": "Question answering over indexed documents with grounding checks.",
    "review_policy_compliance": "Compliance-oriented review of policy posture and control gaps.",
    "assist_technical_document": "Technical document assistance and implementation guidance.",
    "draft_business_response": "Business-facing response drafting using grounded sources.",
}

WORKFLOW_LABELS: dict[str, str] = {
    "document_review": "Document Review",
    "policy_contract_comparison": "Policy / Contract Comparison",
    "action_plan_evidence_review": "Action Plan / Evidence Review",
    "candidate_review": "Candidate Review",
}

ARTIFACT_TYPE_BY_EXPORT_KIND: dict[str, tuple[str, str]] = {
    "benchmark_eval_executive_deck": ("benchmark", "Benchmarks"),
    "document_review_deck": ("report", "Workflow Decks"),
    "policy_contract_comparison_deck": ("report", "Workflow Decks"),
    "action_plan_deck": ("report", "Workflow Decks"),
    "candidate_review_deck": ("report", "Workflow Decks"),
    "evidence_pack_deck": ("report", "Evidence Packs"),
}

STATUS_PREFERRED_ORDER = {"completed": 0, "warning": 1, "error": 2, "failed": 3}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_ratio(numerator: float | int, denominator: float | int, default: float = 0.0) -> float:
    if not isinstance(denominator, (int, float)) or float(denominator) == 0:
        return float(default)
    if not isinstance(numerator, (int, float)):
        return float(default)
    return round(float(numerator) / float(denominator), 4)


def _read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return payload


def _normalize_timestamp(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    if "T" not in normalized and " " in normalized:
        normalized = normalized.replace(" ", "T", 1)
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return text
    if parsed.tzinfo is None:
        return parsed.isoformat()
    return parsed.astimezone(timezone.utc).isoformat()


def _parse_timestamp(value: object) -> datetime | None:
    normalized = _normalize_timestamp(value)
    if not normalized:
        return None
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_size_label(size_bytes: int | None) -> str:
    if not isinstance(size_bytes, int) or size_bytes <= 0:
        return "—"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{round(size_bytes / 1024, 1)} KB"
    return f"{round(size_bytes / (1024 * 1024), 1)} MB"


def _format_duration_label(duration_s: float | int | None) -> str:
    if not isinstance(duration_s, (int, float)):
        return "—"
    total_seconds = max(float(duration_s), 0.0)
    if total_seconds < 60:
        return f"{total_seconds:.1f}s"
    minutes = int(total_seconds // 60)
    seconds = int(round(total_seconds % 60))
    return f"{minutes}m {seconds:02d}s"


def _slugify(value: object) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower())
    return normalized.strip("-") or "item"


def _labelize_slug(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "Unknown"
    return re.sub(r"[_-]+", " ", text).strip().title()


def _titleize_model_family(model_name: str) -> str:
    normalized = str(model_name or "").strip()
    if not normalized:
        return "Unknown"
    family_source = normalized.split(":", 1)[0].split("/", 1)[-1]
    family_source = family_source.replace("-", " ").replace("_", " ").strip()
    return family_source.title() if family_source else normalized


def _quantization_label(model_name: str) -> str:
    normalized = str(model_name or "").strip()
    if not normalized:
        return "—"
    if ":" in normalized:
        return normalized.split(":", 1)[1]
    return "managed"


def _build_meta(*, source: str, updated_at: str | None = None, notes: list[str] | None = None) -> dict[str, Any]:
    return {
        "source": source,
        "updated_at": updated_at,
        "notes": [str(item) for item in (notes or []) if str(item).strip()],
    }


def _load_runtime_controls_state(workspace_root: Path) -> dict[str, Any]:
    path = get_runtime_controls_state_path(workspace_root)
    payload = _read_json_file(path, {})
    return payload if isinstance(payload, dict) else {}


def _load_rag_store(workspace_root: Path) -> dict[str, Any]:
    path = get_rag_store_path(workspace_root)
    payload = _read_json_file(path, {})
    return payload if isinstance(payload, dict) else {}


def _resolve_document_status(document: dict[str, Any]) -> str:
    raw_status = str(document.get("status") or "").strip().lower()
    if raw_status in {"indexed", "indexing", "warning", "error", "pending"}:
        return raw_status
    if document.get("indexed_at") or _safe_int(document.get("chunk_count")) > 0:
        return "indexed"
    return "pending"


def _build_document_catalog(workspace_root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], int, str, str]:
    rag_store = _load_rag_store(workspace_root)
    raw_documents = rag_store.get("documents") if isinstance(rag_store.get("documents"), list) else []
    chunks = rag_store.get("chunks") if isinstance(rag_store.get("chunks"), list) else []
    chroma_path = get_rag_chroma_path(workspace_root)
    vector_backend = "ChromaDB" if chroma_path.exists() else "RAG JSON Store"
    vector_status = "healthy" if raw_documents else ("degraded" if Path(get_rag_store_path(workspace_root)).exists() else "offline")
    total_chunks = len(chunks)
    if total_chunks <= 0:
        total_chunks = sum(_safe_int(item.get("chunk_count")) for item in raw_documents if isinstance(item, dict))

    documents: list[dict[str, Any]] = []
    lookup: dict[str, dict[str, Any]] = {}
    for raw_document in raw_documents:
        if not isinstance(raw_document, dict):
            continue
        document_id = str(raw_document.get("document_id") or "").strip()
        if not document_id:
            continue
        warnings = raw_document.get("warnings") if isinstance(raw_document.get("warnings"), list) else []
        normalized = {
            "document_id": document_id,
            "name": str(raw_document.get("name") or document_id).strip() or document_id,
            "status": _resolve_document_status(raw_document),
            "chunk_count": _safe_int(raw_document.get("chunk_count")),
            "char_count": _safe_int(raw_document.get("char_count")),
            "indexed_at": _normalize_timestamp(raw_document.get("indexed_at")),
            "loader_strategy_label": raw_document.get("loader_strategy_label"),
            "size_bytes": _safe_int(raw_document.get("size_bytes")) or None,
            "size_label": _format_size_label(_safe_int(raw_document.get("size_bytes")) or None),
            "source_type": raw_document.get("source_type"),
            "page_count": _safe_int(raw_document.get("page_count")) or None,
            "warnings": [str(item) for item in warnings if str(item).strip()],
        }
        documents.append(normalized)
        lookup[document_id] = normalized
    return documents, lookup, total_chunks, vector_backend, vector_status


def _resolve_document_names(document_ids: list[object] | None, lookup: dict[str, dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for raw_document_id in document_ids or []:
        document_id = str(raw_document_id or "").strip()
        if not document_id:
            continue
        name = str((lookup.get(document_id) or {}).get("name") or document_id[:12]).strip()
        names.append(name)
    return names


def _load_workflow_history(workspace_root: Path) -> list[dict[str, Any]]:
    payload = _read_json_file(get_product_workflow_history_path(workspace_root), [])
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _load_chat_history(workspace_root: Path) -> list[dict[str, Any]]:
    payload = _read_json_file(get_chat_history_path(workspace_root), [])
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _context_window_from_label(value: object) -> int | None:
    normalized = str(value or "").strip().lower()
    mapping = {
        "auto": None,
        "4k": 4096,
        "8k": 8192,
        "16k": 16384,
        "24k": 24576,
        "32k": 32768,
        "48k": 49152,
        "64k": 65536,
        "128k": 131072,
    }
    if normalized in mapping:
        return mapping[normalized]
    if normalized.isdigit():
        return int(normalized)
    return None


def _resolve_live_provider_profile(
    runtime_controls_state: dict[str, Any],
    *,
    capability: str,
) -> dict[str, Any]:
    profile = runtime_controls_state.get("profile") if isinstance(runtime_controls_state.get("profile"), dict) else {}
    requested_provider = str(profile.get("primaryConnectionId") or "ollama").strip().lower() or "ollama"
    requested_model = str(profile.get("primaryModel") or "").strip()
    if capability == "embeddings":
        requested_provider = str(profile.get("embeddingConnectionId") or requested_provider).strip().lower() or requested_provider
        requested_model = str(profile.get("embeddingModel") or requested_model).strip()

    registry = build_provider_registry()
    hosted_available = "ollama_hosted" in registry
    if requested_provider == "ollama" and hosted_available and "cloud" in requested_model.lower():
        requested_provider = "ollama_hosted"

    fallback_provider = None
    if requested_provider != "ollama" and "ollama" in registry:
        fallback_provider = "ollama"
    elif requested_provider != "ollama_hosted" and hosted_available:
        fallback_provider = "ollama_hosted"
    elif "ollama" in registry:
        fallback_provider = "ollama"

    runtime_profile = resolve_provider_runtime_profile(
        registry,
        requested_provider,
        capability=capability,
        fallback_provider=fallback_provider,
    )
    provider_entry = runtime_profile.get("provider_entry") if isinstance(runtime_profile.get("provider_entry"), dict) else {}
    provider_instance = provider_entry.get("instance")
    resolved_model = requested_model or str(runtime_profile.get("default_model") or "").strip()
    if not resolved_model and provider_instance is not None and hasattr(provider_instance, "list_available_models"):
        try:
            available_models = provider_instance.list_available_models()  # type: ignore[attr-defined]
            resolved_model = str(available_models[0]) if available_models else ""
        except Exception:
            resolved_model = ""

    generation = profile.get("generation") if isinstance(profile.get("generation"), dict) else {}
    return {
        "requested_provider": requested_provider,
        "effective_provider": runtime_profile.get("effective_provider") or requested_provider,
        "provider_entry": provider_entry,
        "provider_instance": provider_instance,
        "provider_label": runtime_profile.get("provider_label") or provider_entry.get("label") or requested_provider,
        "model": resolved_model,
        "context_window": _context_window_from_label(generation.get("contextWindow")) if capability == "chat" else None,
        "temperature": _safe_float(generation.get("temperature"), 0.2),
        "top_p": _safe_float(generation.get("topP"), 0.95),
        "max_tokens": _safe_int(generation.get("maxOutputTokens"), 4096),
        "fallback_reason": runtime_profile.get("fallback_reason"),
        "available": provider_instance is not None and bool(resolved_model),
    }


def _chat_history_message(role: str, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": role,
        "content": str(content or ""),
    }
    if metadata:
        payload["metadata"] = metadata
    return payload


def _append_legacy_chat_history(
    workspace_root: Path,
    *,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    history_path = get_chat_history_path(workspace_root)
    history = load_chat_history_store(history_path)
    history.append(_chat_history_message(role, content, metadata))
    save_chat_history(history_path, history)


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
        "timestamp": _now_iso(),
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


def _fallback_chunks_from_catalog(
    *,
    rag_store: dict[str, Any],
    query: str,
    document_ids: list[str] | None,
    limit: int,
) -> list[dict[str, Any]]:
    raw_chunks = rag_store.get("chunks") if isinstance(rag_store.get("chunks"), list) else []
    selected_document_ids = {str(document_id) for document_id in (document_ids or []) if str(document_id or "").strip()}
    normalized_chunks: list[dict[str, Any]] = []
    query_terms = [term.lower() for term in re.findall(r"[a-zA-Z0-9_]{3,}", str(query or ""))]
    for raw_chunk in raw_chunks:
        if not isinstance(raw_chunk, dict):
            continue
        chunk_document_id = str(raw_chunk.get("document_id") or raw_chunk.get("file_hash") or "").strip()
        if selected_document_ids and chunk_document_id not in selected_document_ids:
            continue
        text_value = str(raw_chunk.get("text") or raw_chunk.get("snippet") or "").strip()
        if not text_value:
            continue
        lowered = text_value.lower()
        lexical_hits = sum(lowered.count(term) for term in query_terms)
        normalized = dict(raw_chunk)
        normalized["score"] = round(float(lexical_hits), 3)
        normalized["snippet"] = text_value[:420]
        normalized_chunks.append(normalized)
    normalized_chunks.sort(
        key=lambda item: (
            -_safe_float(item.get("score")),
            _safe_int(item.get("chunk_index"), 0),
            str(item.get("chunk_id") or ""),
        )
    )
    if not normalized_chunks and selected_document_ids:
        for raw_chunk in raw_chunks:
            if not isinstance(raw_chunk, dict):
                continue
            chunk_document_id = str(raw_chunk.get("document_id") or raw_chunk.get("file_hash") or "").strip()
            if chunk_document_id not in selected_document_ids:
                continue
            text_value = str(raw_chunk.get("text") or raw_chunk.get("snippet") or "").strip()
            if not text_value:
                continue
            normalized = dict(raw_chunk)
            normalized["score"] = 0.0
            normalized["snippet"] = text_value[:420]
            normalized_chunks.append(normalized)
            if len(normalized_chunks) >= limit:
                break
    return normalized_chunks[:limit]


def _compose_chat_prompt(*, question: str, selected_document_names: list[str], context_chunks: list[dict[str, Any]]) -> str:
    context_sections: list[str] = []
    total_chars = 0
    for index, chunk in enumerate(context_chunks, start=1):
        source_name = str(chunk.get("source") or chunk.get("document_id") or f"chunk-{index}")
        snippet = str(chunk.get("snippet") or chunk.get("text") or "").strip()
        if not snippet:
            continue
        section = f"[Source {index}: {source_name}]\n{snippet}"
        if total_chars + len(section) > 22000:
            break
        context_sections.append(section)
        total_chars += len(section)
    source_list = ", ".join(selected_document_names[:4]) if selected_document_names else "the indexed workspace documents"
    context_block = "\n\n".join(context_sections) if context_sections else "[No retrieved context available.]"
    return (
        "You are the AI LAB document assistant. Answer the user question using the provided retrieved evidence whenever possible. "
        "If evidence is incomplete or weak, say that clearly and avoid inventing facts.\n\n"
        f"Selected documents: {source_list}\n\n"
        f"Question:\n{question.strip()}\n\n"
        f"Retrieved context:\n{context_block}\n\n"
        "Answer in a concise, grounded way and mention uncertainty when needed."
    )


def _format_chat_sources_for_ui(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    formatted: list[dict[str, Any]] = []
    for source in sources[:4]:
        label = str(source.get("source") or source.get("document_id") or "source").strip() or "source"
        detail = str(source.get("snippet") or "").strip()[:180] or None
        score = source.get("score")
        formatted.append(
            {
                "label": label,
                "detail": detail,
                "score": round(float(score), 3) if isinstance(score, (int, float)) else None,
            }
        )
    return formatted


def _write_lab_execution_artifact(
    workspace_root: Path,
    *,
    category: str,
    identifier: str,
    payload: dict[str, Any],
) -> Path:
    artifact_root = get_artifact_root(workspace_root) / "presentation_exports" / "ai_lab" / category
    artifact_root.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_root / f"{_slugify(identifier)}.json"
    artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return artifact_path


def _normalize_session_messages_for_ui(session: dict[str, Any]) -> list[dict[str, Any]]:
    messages = session.get("messages") if isinstance(session.get("messages"), list) else []
    normalized: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "user").strip().lower()
        if role not in {"user", "assistant"}:
            continue
        normalized.append(
            {
                "id": str(message.get("id") or _slugify(message.get("timestamp") or len(normalized))),
                "role": role,
                "content": str(message.get("content") or ""),
                "timestamp": _normalize_timestamp(message.get("timestamp")),
                "sources": [item for item in (message.get("sources") if isinstance(message.get("sources"), list) else []) if isinstance(item, dict)],
            }
        )
    return normalized


def _build_chat_payload_from_session(
    *,
    session: dict[str, Any],
    documents: list[dict[str, Any]],
    document_lookup: dict[str, dict[str, Any]],
    runtime_snapshot: dict[str, Any],
    runtime_controls_state: dict[str, Any],
    can_send: bool,
    capability_reason: str | None,
    provider_runtime: dict[str, Any],
) -> dict[str, Any]:
    selected_documents = [
        document_lookup[str(document_id)]
        for document_id in (session.get("document_ids") if isinstance(session.get("document_ids"), list) else [])
        if str(document_id) in document_lookup
    ]
    if not selected_documents:
        selected_documents = documents[:4]
    selected_document_names = [str(item.get("name") or item.get("document_id")) for item in selected_documents]
    messages = _normalize_session_messages_for_ui(session)
    session_runtime = session.get("runtime") if isinstance(session.get("runtime"), dict) else {}
    latest_assistant = None
    for message in reversed(session.get("messages") if isinstance(session.get("messages"), list) else []):
        if isinstance(message, dict) and str(message.get("role") or "").strip().lower() == "assistant":
            latest_assistant = message
            break
    latest_diagnostics = latest_assistant.get("diagnostics") if isinstance(latest_assistant, dict) and isinstance(latest_assistant.get("diagnostics"), dict) else session_runtime
    context_used = _safe_int(latest_diagnostics.get("context_chars"))
    context_budget = _safe_int(latest_diagnostics.get("context_budget_chars"))
    if context_budget <= 0:
        context_budget = _safe_int(runtime_snapshot.get("contextBudgetTotal"))
    session_diagnostics = [
        {"label": "Messages", "value": str(len(messages))},
        {"label": "Tokens used", "value": f"{_safe_int(latest_diagnostics.get('total_tokens')):,}" if _safe_int(latest_diagnostics.get('total_tokens')) else "—"},
        {"label": "Avg latency", "value": _format_duration_label(_safe_float(session_runtime.get('avg_latency_s') or latest_diagnostics.get('latency_s'))) if (_safe_float(session_runtime.get('avg_latency_s') or latest_diagnostics.get('latency_s')) > 0) else "—"},
        {"label": "Model", "value": str(latest_diagnostics.get("model") or provider_runtime.get("model") or runtime_snapshot.get("generationModel"))},
        {"label": "Top-K", "value": str(latest_diagnostics.get("rag_top_k") or runtime_snapshot.get("topK"))},
        {"label": "Context used", "value": f"{context_used:,} / {context_budget:,}" if context_used and context_budget else "—"},
    ]
    retrieval_quality = [
        {"label": "Strategy", "value": str(latest_diagnostics.get("retrieval_strategy_used") or runtime_snapshot.get("retrievalStrategy"))},
        {"label": "Backend", "value": str(latest_diagnostics.get("retrieval_backend_used") or runtime_snapshot.get("vectorBackend"))},
        {"label": "Retrieved chunks", "value": str(_safe_int(latest_diagnostics.get("retrieved_chunks_count")))},
        {"label": "Rerank pool", "value": str(latest_diagnostics.get("rerank_pool_size_effective") or runtime_snapshot.get("rerankPoolSize"))},
        {"label": "Context pressure", "value": f"{round(_safe_float(latest_diagnostics.get('context_pressure_ratio') or runtime_snapshot.get('contextPressure')) * 100)}%"},
    ]
    suggestions = [
        prompt
        for prompt in [
            f"Summarize the most important operational risks in {selected_document_names[0]}." if selected_document_names else "Summarize the highest-priority findings in the selected documents.",
            f"What evidence supports the main conclusion in {selected_document_names[0]}?" if selected_document_names else "What evidence supports the main conclusion?",
            "List the missing evidence, open questions and next validation steps.",
        ]
        if prompt
    ]
    notes = [
        "This tab now uses persisted AI LAB chat sessions plus live backend execution instead of replaying a mock conversation.",
    ]
    if str(session.get("last_error") or "").strip():
        notes.append(str(session.get("last_error") or "").strip())
    return {
        "ok": True,
        "meta": _build_meta(
            source="live",
            updated_at=_normalize_timestamp(session.get("updated_at")) or _normalize_timestamp(runtime_controls_state.get("updated_at")) or _now_iso(),
            notes=notes,
        ),
        "capabilities": {
            "can_send": can_send,
            "reason": capability_reason,
        },
        "active_session_id": session.get("session_id"),
        "sessions": [
            {
                "session_id": session.get("session_id"),
                "title": session.get("title"),
                "updated_at": session.get("updated_at"),
                "message_count": len(messages),
            }
        ],
        "messages": messages,
        "suggested_prompts": suggestions[:3],
        "selected_documents": selected_documents,
        "session_diagnostics": session_diagnostics,
        "retrieval_quality": retrieval_quality,
    }


def _task_to_workflow_id(task_id: str) -> str:
    normalized = str(task_id or "").strip()
    mapping = {
        "review_document_risks": "document_review",
        "consult_documents": "document_review",
        "review_policy_compliance": "document_review",
        "assist_technical_document": "document_review",
        "draft_business_response": "document_review",
        "compare_documents": "policy_contract_comparison",
        "extract_operational_tasks": "action_plan_evidence_review",
        "candidate_review": "candidate_review",
        "document_review": "document_review",
        "policy_contract_comparison": "policy_contract_comparison",
        "action_plan_evidence_review": "action_plan_evidence_review",
    }
    return mapping.get(normalized, "document_review")


def _default_workflow_prompt(task_id: str, document_names: list[str]) -> str:
    label = _task_label(task_id)
    if _task_to_workflow_id(task_id) == "policy_contract_comparison":
        return f"Compare the selected documents for {label.lower()} and explain the operational impact of the main differences."
    if _task_to_workflow_id(task_id) == "action_plan_evidence_review":
        return f"Derive a grounded action plan from the selected evidence for {label.lower()}, including owners, deadlines and missing evidence."
    if _task_to_workflow_id(task_id) == "candidate_review":
        return f"Review the selected CV and summarize strengths, gaps and interview priorities."
    document_hint = ", ".join(document_names[:2]) if document_names else "the selected evidence"
    return f"Review {document_hint} and summarize the most important findings, risks and next actions for {label.lower()}."


def _result_items_from_workflow_result(result: ProductWorkflowResult) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if result.summary:
        items.append({"label": "Summary", "value": result.summary, "confidence": None})
    for highlight in result.highlights[:4]:
        highlight_text = str(highlight or "").strip()
        if highlight_text:
            items.append({"label": "Highlight", "value": highlight_text, "confidence": None})
    if result.recommendation:
        items.append({"label": "Recommendation", "value": result.recommendation, "confidence": None})
    if result.structured_result and result.structured_result.validation_error:
        items.append({"label": "Validation", "value": result.structured_result.validation_error, "confidence": None})
    if result.structured_result and result.structured_result.error and result.structured_result.error.message:
        items.append({"label": "Error", "value": result.structured_result.error.message, "confidence": None})
    return items[:6]


def _summarize_chat_sessions_for_payload(sessions: list[dict[str, Any]], *, limit: int = 12) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for session in sessions[:limit]:
        messages = session.get("messages") if isinstance(session.get("messages"), list) else []
        summaries.append(
            {
                "session_id": str(session.get("session_id") or ""),
                "title": str(session.get("title") or "AI LAB chat session"),
                "updated_at": _normalize_timestamp(session.get("updated_at")) or _normalize_timestamp(session.get("created_at")),
                "message_count": len(messages),
                "status": str(session.get("status") or "active"),
            }
        )
    return summaries



def _workflow_execution_from_run_record(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(run.get("run_id") or ""),
        "mode": str(run.get("execution_mode") or run.get("workflow_id") or "product_workflow"),
        "status": str(run.get("status") or "completed"),
        "confidence": round(_safe_float(run.get("confidence")), 3),
        "source_count": _safe_int(run.get("source_count")),
        "latency_s": round(_safe_float(run.get("latency_s")), 4) if run.get("latency_s") is not None else None,
        "provider": str(run.get("provider") or "").strip() or None,
        "model": str(run.get("model") or "").strip() or None,
        "needs_review": bool(run.get("needs_review")),
        "review_reason": str(run.get("review_reason") or "").strip() or None,
        "timestamp": _normalize_timestamp(run.get("updated_at") or run.get("created_at")),
    }



def _workflow_case_from_run_record(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(run.get("run_id") or ""),
        "task": _task_label(str(run.get("task_id") or run.get("workflow_id") or "document_review")),
        "document": ", ".join([str(name) for name in (run.get("document_names") if isinstance(run.get("document_names"), list) else []) if str(name).strip()][:2]) or "No current indexed source",
        "mode": str(run.get("execution_mode") or run.get("workflow_id") or "product_workflow"),
        "status": str(run.get("status") or "completed"),
        "needsReview": bool(run.get("needs_review")),
        "confidence": round(_safe_float(run.get("confidence")), 3),
        "sourceCount": _safe_int(run.get("source_count")),
        "timestamp": _normalize_timestamp(run.get("updated_at") or run.get("created_at")),
        "reviewReason": str(run.get("review_reason") or "").strip() or None,
    }



def _workflow_task_detail_from_run_record(run: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    base = dict(existing or {})
    result_payload = run.get("result") if isinstance(run.get("result"), dict) else {}
    raw_json = run.get("raw_json") if isinstance(run.get("raw_json"), dict) else (run.get("response_payload") if isinstance(run.get("response_payload"), dict) else {})
    trace = run.get("trace") if isinstance(run.get("trace"), dict) else {}
    result_items = [
        item
        for item in (result_payload.get("result_items") if isinstance(result_payload.get("result_items"), list) else [])
        if isinstance(item, dict)
    ]
    if not result_items:
        summary_text = str(result_payload.get("summary") or run.get("summary") or "").strip()
        if summary_text:
            result_items.append({"label": "Summary", "value": summary_text, "confidence": None})
        for highlight in (result_payload.get("highlights") if isinstance(result_payload.get("highlights"), list) else []):
            highlight_text = str(highlight or "").strip()
            if highlight_text:
                result_items.append({"label": "Highlight", "value": highlight_text, "confidence": None})
        recommendation = str(result_payload.get("recommendation") or "").strip()
        if recommendation:
            result_items.append({"label": "Recommendation", "value": recommendation, "confidence": None})
    trace_fields = [
        {"label": "Workflow", "value": str(run.get("workflow_id") or "document_review")},
        {"label": "Provider", "value": str(run.get("provider") or "—")},
        {"label": "Model", "value": str(run.get("model") or "—")},
        {"label": "Latency", "value": _format_duration_label(_safe_float(run.get("latency_s"))) if _safe_float(run.get("latency_s")) > 0 else "—"},
        {"label": "Sources", "value": str(_safe_int(run.get("source_count")))},
        {"label": "Needs Review", "value": "Yes" if bool(run.get("needs_review")) else "No"},
        {"label": "Review Reason", "value": str(run.get("review_reason") or "—")},
        {"label": "Execution Mode", "value": str(run.get("execution_mode") or trace.get("workflow_id") or "product_workflow")},
        {"label": "Artifact", "value": str(run.get("artifact_path") or "—")},
        {"label": "Updated", "value": _normalize_timestamp(run.get("updated_at") or run.get("created_at")) or "—"},
    ]
    executions = [
        _workflow_execution_from_run_record(run),
        *[item for item in (base.get("executions") if isinstance(base.get("executions"), list) else []) if isinstance(item, dict)],
    ]
    deduped_executions: list[dict[str, Any]] = []
    seen_execution_ids: set[str] = set()
    for execution in executions:
        execution_id = str(execution.get("id") or "")
        if execution_id and execution_id in seen_execution_ids:
            continue
        if execution_id:
            seen_execution_ids.add(execution_id)
        deduped_executions.append(execution)
    return {
        "id": str(run.get("task_id") or run.get("workflow_id") or base.get("id") or "document_review"),
        "label": _task_label(str(run.get("task_id") or run.get("workflow_id") or base.get("id") or "document_review")),
        "description": base.get("description") or _task_description(str(run.get("task_id") or run.get("workflow_id") or "document_review")),
        "document_names": [str(name) for name in (run.get("document_names") if isinstance(run.get("document_names"), list) else base.get("document_names") or []) if str(name).strip()],
        "result_title": str(run.get("result_title") or base.get("result_title") or f"Latest run · {_task_label(str(run.get('task_id') or run.get('workflow_id') or 'document_review'))}"),
        "result_items": result_items[:8],
        "trace_fields": trace_fields,
        "raw_json": raw_json,
        "executions": deduped_executions[:12],
    }



def _build_evidenceops_worklog_entry_from_workflow(*, run_record: dict[str, Any], result: ProductWorkflowResult) -> dict[str, Any]:
    structured = result.structured_result
    parsed_json = structured.parsed_json if structured is not None and isinstance(structured.parsed_json, dict) else {}
    validated_payload = structured.validated_output.model_dump(mode="json") if structured is not None and getattr(structured, "validated_output", None) is not None else {}
    payload = parsed_json or validated_payload
    findings = payload.get("findings") if isinstance(payload.get("findings"), list) else []
    action_items = payload.get("action_items") if isinstance(payload.get("action_items"), list) else []
    recommended_actions = payload.get("recommended_actions") if isinstance(payload.get("recommended_actions"), list) else []
    if not findings:
        findings = [{"finding_type": "highlight", "detail": str(item)} for item in result.highlights[:6] if str(item or "").strip()]
    if not recommended_actions and result.recommendation:
        recommended_actions = [result.recommendation]
    review_type = str((structured.task_type if structured is not None else None) or run_record.get("workflow_id") or run_record.get("task_id") or "workflow_review")
    return {
        "timestamp": _normalize_timestamp(run_record.get("updated_at") or run_record.get("created_at")) or _now_iso(),
        "task_type": str(run_record.get("task_id") or run_record.get("workflow_id") or "document_review"),
        "review_type": review_type,
        "tool_used": str(run_record.get("workflow_id") or run_record.get("task_id") or "workflow_inspector"),
        "query": str(run_record.get("input_text") or ""),
        "confidence": _safe_float(run_record.get("confidence")),
        "needs_review": bool(run_record.get("needs_review")),
        "needs_review_reason": str(run_record.get("review_reason") or "").strip() or None,
        "source_count": _safe_int(run_record.get("source_count")),
        "document_ids": [str(item) for item in (run_record.get("document_ids") if isinstance(run_record.get("document_ids"), list) else []) if str(item).strip()],
        "workflow_id": str(run_record.get("workflow_id") or "document_review"),
        "execution_strategy_used": str(run_record.get("execution_mode") or "product_workflow"),
        "findings": findings,
        "action_items": action_items,
        "recommended_actions": recommended_actions,
    }


def _apply_lab_runtime_request_overrides(
    request: ProductWorkflowRequest,
    *,
    workspace_root: Path,
    explicit_fields: set[str] | None = None,
) -> ProductWorkflowRequest:
    runtime_controls_state = _load_runtime_controls_state(workspace_root)
    profile = runtime_controls_state.get("profile") if isinstance(runtime_controls_state.get("profile"), dict) else {}
    generation = profile.get("generation") if isinstance(profile.get("generation"), dict) else {}
    explicit = {str(item) for item in (explicit_fields or set())}

    updates: dict[str, Any] = {}
    if "provider" not in explicit:
        provider_name = str(profile.get("primaryConnectionId") or request.provider).strip()
        if provider_name:
            updates["provider"] = provider_name
    if "model" not in explicit and str(profile.get("primaryModel") or "").strip():
        updates["model"] = str(profile.get("primaryModel") or request.model)
    if "prompt_profile" not in explicit and str(generation.get("promptProfile") or "").strip():
        updates["prompt_profile"] = str(generation.get("promptProfile") or request.prompt_profile)
    if "temperature" not in explicit and generation.get("temperature") is not None:
        updates["temperature"] = _safe_float(generation.get("temperature"), request.temperature)
    if "top_p" not in explicit and generation.get("topP") is not None:
        updates["top_p"] = _safe_float(generation.get("topP"), request.top_p if request.top_p is not None else 0.95)
    if "max_tokens" not in explicit and generation.get("maxOutputTokens") is not None:
        updates["max_tokens"] = _safe_int(generation.get("maxOutputTokens"), request.max_tokens if request.max_tokens is not None else 4096)
    if "context_window_mode" not in explicit and "context_window" not in explicit:
        configured_context = _context_window_from_label(str(generation.get("contextWindow") or "auto"))
        if configured_context is not None:
            updates["context_window_mode"] = "manual"
            updates["context_window"] = configured_context
        else:
            updates["context_window_mode"] = "auto"
            updates["context_window"] = None
    return request.model_copy(update=updates) if updates else request


def execute_lab_chat_turn(
    *,
    bootstrap: Any,
    session_id: str | None,
    content: str,
    document_ids: list[str] | None = None,
) -> dict[str, Any]:
    workspace_root = Path(bootstrap.workspace_root)
    normalized_content = str(content or "").strip()
    if not normalized_content:
        raise ValueError("Message content is required.")

    documents, document_lookup, _, _, _ = _build_document_catalog(workspace_root)
    available_document_ids = [str(item.get("document_id") or "") for item in documents]
    requested_document_ids = [str(document_id) for document_id in (document_ids or []) if str(document_id or "").strip()]

    sessions_path = get_lab_chat_sessions_path(workspace_root)
    session = get_lab_chat_session(sessions_path, session_id or "") if session_id else None
    if session is None:
        title = normalized_content[:72] + ("…" if len(normalized_content) > 72 else "")
        session = create_lab_chat_session(
            sessions_path,
            title=title,
            document_ids=requested_document_ids or available_document_ids[: min(3, len(available_document_ids))],
        )
    resolved_document_ids = requested_document_ids or [str(document_id) for document_id in (session.get("document_ids") or []) if str(document_id or "").strip()]
    if not resolved_document_ids:
        resolved_document_ids = available_document_ids[: min(3, len(available_document_ids))]

    user_message = append_lab_chat_message(
        sessions_path,
        session_id=str(session.get("session_id")),
        role="user",
        content=normalized_content,
    )
    _append_legacy_chat_history(
        workspace_root,
        role="user",
        content=normalized_content,
        metadata={"source_document_ids": resolved_document_ids},
    )

    runtime_controls_state = _load_runtime_controls_state(workspace_root)
    chat_provider_runtime = _resolve_live_provider_profile(runtime_controls_state, capability="chat")
    embedding_provider_runtime = _resolve_live_provider_profile(runtime_controls_state, capability="embeddings")
    if not chat_provider_runtime.get("available"):
        update_lab_chat_session_runtime(
            sessions_path,
            session_id=str(session.get("session_id")),
            status="error",
            last_error="No chat-capable provider is available in the current runtime configuration.",
            document_ids=resolved_document_ids,
        )
        raise RuntimeError("No chat-capable provider is available in the current runtime configuration.")

    rag_settings = build_effective_rag_settings(default_settings=bootstrap.rag_settings, workspace_root=workspace_root)
    rag_store = _load_rag_store(workspace_root)
    selected_document_names = _resolve_document_names(resolved_document_ids, document_lookup)
    retrieval_started_at = time.perf_counter()
    retrieval_error = None
    retrieval_details: dict[str, Any] = {}
    retrieved_chunks: list[dict[str, Any]] = []
    try:
        embedding_provider = embedding_provider_runtime.get("provider_instance")
        if embedding_provider is None:
            raise RuntimeError("Embedding provider unavailable")
        retrieval_details = retrieve_relevant_chunks_detailed(
            query=normalized_content,
            rag_index=rag_store,
            settings=rag_settings,
            embedding_provider=embedding_provider,
            document_ids=resolved_document_ids or None,
        )
        retrieved_chunks = [item for item in (retrieval_details.get("chunks") if isinstance(retrieval_details.get("chunks"), list) else []) if isinstance(item, dict)]
    except Exception as error:
        retrieval_error = str(error)
        retrieved_chunks = _fallback_chunks_from_catalog(
            rag_store=rag_store,
            query=normalized_content,
            document_ids=resolved_document_ids,
            limit=max(_safe_int(getattr(rag_settings, "top_k", 4), 4), 4),
        )
        retrieval_details = {
            "chunks": retrieved_chunks,
            "backend_used": "lexical_fallback",
            "backend_message": f"Fallback retrieval from stored chunks: {error}",
            "filtered_chunks_available": len(retrieved_chunks),
            "candidate_pool_size": len(retrieved_chunks),
            "reranking_applied": False,
            "retrieval_strategy_requested": "hybrid",
            "retrieval_strategy_used": "lexical_fallback",
            "retrieval_strategy_fallback_reason": retrieval_error,
        }
    retrieval_latency_s = round(time.perf_counter() - retrieval_started_at, 4)

    prompt_started_at = time.perf_counter()
    composed_prompt = _compose_chat_prompt(
        question=normalized_content,
        selected_document_names=selected_document_names,
        context_chunks=retrieved_chunks,
    )
    prompt_build_latency_s = round(time.perf_counter() - prompt_started_at, 4)

    current_session = get_lab_chat_session(sessions_path, str(session.get("session_id"))) or session
    prior_messages = [item for item in (current_session.get("messages") if isinstance(current_session.get("messages"), list) else []) if isinstance(item, dict)]
    model_messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": "You are the AI LAB assistant. Stay grounded in the provided evidence and say when evidence is insufficient.",
        }
    ]
    for message in prior_messages[-6:-1]:
        role = str(message.get("role") or "user").strip().lower()
        content_value = str(message.get("content") or "").strip()
        if role in {"user", "assistant"} and content_value:
            model_messages.append({"role": role, "content": content_value})
    model_messages.append({"role": "user", "content": composed_prompt})

    provider = chat_provider_runtime.get("provider_instance")
    generation_started_at = time.perf_counter()
    response_text = ""
    try:
        stream = provider.stream_chat_completion(
            messages=model_messages,
            model=str(chat_provider_runtime.get("model") or ""),
            temperature=_safe_float(chat_provider_runtime.get("temperature"), 0.2),
            context_window=chat_provider_runtime.get("context_window"),
            top_p=_safe_float(chat_provider_runtime.get("top_p"), 0.95),
            max_tokens=_safe_int(chat_provider_runtime.get("max_tokens"), 4096),
        )
        response_text = "".join(provider.iter_stream_text(stream)).strip()
    except Exception as error:
        update_lab_chat_session_runtime(
            sessions_path,
            session_id=str(session.get("session_id")),
            status="error",
            last_error=str(error),
            document_ids=resolved_document_ids,
        )
        append_runtime_execution_log_entry(
            get_runtime_execution_log_path(workspace_root),
            _build_runtime_execution_log_entry(
                flow_type="chat_rag",
                task_type="chat_rag",
                provider=str(chat_provider_runtime.get("effective_provider") or chat_provider_runtime.get("requested_provider") or "unknown"),
                model=str(chat_provider_runtime.get("model") or "unknown"),
                success=False,
                latency_s=time.perf_counter() - generation_started_at,
                retrieval_latency_s=retrieval_latency_s,
                prompt_build_latency_s=prompt_build_latency_s,
                context_window=chat_provider_runtime.get("context_window"),
                context_window_mode="manual" if chat_provider_runtime.get("context_window") else "auto",
                embedding_provider=str(embedding_provider_runtime.get("effective_provider") or embedding_provider_runtime.get("requested_provider") or "unknown"),
                embedding_model=str(embedding_provider_runtime.get("model") or "unknown"),
                retrieval_strategy_requested=str(retrieval_details.get("retrieval_strategy_requested") or rag_settings.retrieval_strategy),
                retrieval_strategy_used=str(retrieval_details.get("retrieval_strategy_used") or rag_settings.retrieval_strategy),
                retrieval_backend_used=str(retrieval_details.get("backend_used") or "unavailable"),
                rag_chunk_size=rag_settings.chunk_size,
                rag_chunk_overlap=rag_settings.chunk_overlap,
                rag_top_k=rag_settings.top_k,
                prompt_chars=count_message_chars(model_messages),
                output_chars=0,
                context_chars=len(composed_prompt),
                source_document_ids=resolved_document_ids,
                retrieved_chunks_count=len(retrieved_chunks),
                error_message=str(error),
                extra={
                    "retrieval_fallback_reason": retrieval_error,
                    "context_budget_chars": chat_provider_runtime.get("context_window"),
                },
            ),
        )
        raise
    generation_latency_s = round(time.perf_counter() - generation_started_at, 4)
    if not response_text:
        response_text = "No response text was returned by the configured runtime."

    native_usage = get_provider_native_usage_metrics(provider)
    usage_metrics = estimate_runtime_usage_metrics(
        prompt_chars=count_message_chars(model_messages),
        completion_chars=len(response_text),
        context_chars=sum(len(str(chunk.get("snippet") or chunk.get("text") or "")) for chunk in retrieved_chunks),
        provider=str(chat_provider_runtime.get("effective_provider") or chat_provider_runtime.get("requested_provider") or ""),
        native_usage=native_usage,
        chars_per_token=getattr(rag_settings, "context_chars_per_token", 4.0),
    )
    total_latency_s = round(retrieval_latency_s + prompt_build_latency_s + generation_latency_s, 4)
    context_budget_chars = _safe_int(chat_provider_runtime.get("context_window"), 0)
    context_chars = _safe_int(usage_metrics.get("context_chars"), 0)
    runtime_payload = {
        "provider": str(chat_provider_runtime.get("effective_provider") or chat_provider_runtime.get("requested_provider") or "unknown"),
        "model": str(chat_provider_runtime.get("model") or "unknown"),
        "latency_s": total_latency_s,
        "avg_latency_s": total_latency_s,
        "retrieval_latency_s": retrieval_latency_s,
        "prompt_build_latency_s": prompt_build_latency_s,
        "generation_latency_s": generation_latency_s,
        "retrieved_chunks_count": len(retrieved_chunks),
        "retrieval_strategy_requested": str(retrieval_details.get("retrieval_strategy_requested") or rag_settings.retrieval_strategy),
        "retrieval_strategy_used": str(retrieval_details.get("retrieval_strategy_used") or rag_settings.retrieval_strategy),
        "retrieval_backend_used": str(retrieval_details.get("backend_used") or "unavailable"),
        "rag_top_k": rag_settings.top_k,
        "top_k_effective": rag_settings.top_k,
        "total_tokens": _safe_int(usage_metrics.get("total_tokens")),
        "prompt_tokens": _safe_int(usage_metrics.get("prompt_tokens")),
        "completion_tokens": _safe_int(usage_metrics.get("completion_tokens")),
        "context_chars": context_chars,
        "context_budget_chars": context_budget_chars,
        "context_pressure_ratio": round(_safe_ratio(context_chars, context_budget_chars, 0.0), 3) if context_budget_chars else 0.0,
        "usage_source": usage_metrics.get("usage_source"),
        "cost_usd": usage_metrics.get("cost_usd"),
        "cost_source": usage_metrics.get("cost_source"),
        "source_document_ids": resolved_document_ids,
        "retrieval_fallback_reason": retrieval_error,
    }
    ui_sources = _format_chat_sources_for_ui(build_source_metadata(retrieved_chunks))
    assistant_message = append_lab_chat_message(
        sessions_path,
        session_id=str(session.get("session_id")),
        role="assistant",
        content=response_text,
        sources=ui_sources,
        diagnostics=runtime_payload,
    )
    updated_session = update_lab_chat_session_runtime(
        sessions_path,
        session_id=str(session.get("session_id")),
        runtime=runtime_payload,
        status="active",
        last_error=None,
        document_ids=resolved_document_ids,
    )
    _append_legacy_chat_history(
        workspace_root,
        role="assistant",
        content=response_text,
        metadata=runtime_payload,
    )
    artifact_path = _write_lab_execution_artifact(
        workspace_root,
        category="chat_sessions",
        identifier=f"{session.get('session_id')}-{assistant_message.get('id')}",
        payload={
            "session": updated_session,
            "request": {
                "content": normalized_content,
                "document_ids": resolved_document_ids,
            },
            "response": {
                "assistant_message": assistant_message,
                "sources": ui_sources,
            },
            "runtime": runtime_payload,
        },
    )
    runtime_payload["artifact_path"] = str(artifact_path)
    updated_session = update_lab_chat_session_runtime(
        sessions_path,
        session_id=str(session.get("session_id")),
        runtime=runtime_payload,
        status="active",
        last_error=None,
        document_ids=resolved_document_ids,
    )
    chat_worklog_entry = {
        "timestamp": _now_iso(),
        "task_type": "consult_documents",
        "review_type": "document_chat",
        "tool_used": "chat_rag",
        "query": normalized_content,
        "confidence": max(0.0, 1.0 - min(_safe_float(runtime_payload.get("context_pressure_ratio")), 0.95)),
        "needs_review": bool(retrieval_error),
        "needs_review_reason": retrieval_error or None,
        "source_count": len(resolved_document_ids),
        "document_ids": resolved_document_ids,
        "workflow_id": "document_review",
        "execution_strategy_used": str(runtime_payload.get("retrieval_strategy_used") or "chat_rag"),
        "findings": [{"finding_type": "assistant_response", "detail": response_text[:280]}],
        "action_items": [],
        "recommended_actions": [],
    }
    append_evidenceops_worklog_entry(get_phase95_evidenceops_worklog_path(workspace_root), chat_worklog_entry)
    append_evidenceops_actions_from_worklog_entry(get_phase95_evidenceops_action_store_path(workspace_root), chat_worklog_entry)
    append_runtime_execution_log_entry(
        get_runtime_execution_log_path(workspace_root),
        _build_runtime_execution_log_entry(
            flow_type="chat_rag",
            task_type="chat_rag",
            provider=str(chat_provider_runtime.get("effective_provider") or chat_provider_runtime.get("requested_provider") or "unknown"),
            model=str(chat_provider_runtime.get("model") or "unknown"),
            success=True,
            latency_s=total_latency_s,
            retrieval_latency_s=retrieval_latency_s,
            generation_latency_s=generation_latency_s,
            prompt_build_latency_s=prompt_build_latency_s,
            context_window=chat_provider_runtime.get("context_window"),
            context_window_mode="manual" if chat_provider_runtime.get("context_window") else "auto",
            embedding_provider=str(embedding_provider_runtime.get("effective_provider") or embedding_provider_runtime.get("requested_provider") or "unknown"),
            embedding_model=str(embedding_provider_runtime.get("model") or "unknown"),
            retrieval_strategy_requested=str(retrieval_details.get("retrieval_strategy_requested") or rag_settings.retrieval_strategy),
            retrieval_strategy_used=str(retrieval_details.get("retrieval_strategy_used") or rag_settings.retrieval_strategy),
            retrieval_backend_used=str(retrieval_details.get("backend_used") or "unavailable"),
            rag_chunk_size=rag_settings.chunk_size,
            rag_chunk_overlap=rag_settings.chunk_overlap,
            rag_top_k=rag_settings.top_k,
            prompt_chars=_safe_int(usage_metrics.get("prompt_chars")),
            output_chars=_safe_int(usage_metrics.get("output_chars")),
            context_chars=_safe_int(usage_metrics.get("context_chars")),
            prompt_tokens=_safe_int(usage_metrics.get("prompt_tokens")),
            completion_tokens=_safe_int(usage_metrics.get("completion_tokens")),
            total_tokens=_safe_int(usage_metrics.get("total_tokens")),
            usage_source=str(usage_metrics.get("usage_source") or "estimated_chars"),
            cost_usd=(_safe_float(usage_metrics.get("cost_usd")) if usage_metrics.get("cost_usd") is not None else None),
            cost_source=str(usage_metrics.get("cost_source") or "pricing_not_configured"),
            source_document_ids=resolved_document_ids,
            retrieved_chunks_count=len(retrieved_chunks),
            extra={
                "top_k_effective": rag_settings.top_k,
                "context_budget_chars": context_budget_chars,
                "context_pressure_ratio": runtime_payload.get("context_pressure_ratio"),
                "artifact_path": str(artifact_path),
                "retrieval_fallback_reason": retrieval_error,
            },
        ),
    )
    return {
        "ok": True,
        "session": updated_session,
        "assistant_message": assistant_message,
        "artifact_path": str(artifact_path),
    }


def execute_lab_workflow_inspector_run(
    *,
    bootstrap: Any,
    task_id: str,
    document_id: str | None = None,
    input_text: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    workspace_root = Path(bootstrap.workspace_root)
    task_id = str(task_id or "document_review").strip() or "document_review"
    workflow_id = _task_to_workflow_id(task_id)
    documents, document_lookup, _, _, _ = _build_document_catalog(workspace_root)
    available_document_ids = [str(item.get("document_id") or "") for item in documents if str(item.get("document_id") or "").strip()]
    selected_document_ids: list[str] = []
    if document_id and str(document_id).strip():
        selected_document_ids.append(str(document_id).strip())
    if workflow_id == "policy_contract_comparison":
        for candidate_document_id in available_document_ids:
            if candidate_document_id not in selected_document_ids:
                selected_document_ids.append(candidate_document_id)
            if len(selected_document_ids) >= 2:
                break
    elif workflow_id in {"document_review", "action_plan_evidence_review", "candidate_review"}:
        if not selected_document_ids and available_document_ids:
            selected_document_ids.append(available_document_ids[0])
    selected_document_names = _resolve_document_names(selected_document_ids, document_lookup)

    request_payload = {
        "workflow_id": workflow_id,
        "document_ids": selected_document_ids,
        "input_text": str(input_text or "").strip() or _default_workflow_prompt(task_id, selected_document_names),
    }
    if provider:
        request_payload["provider"] = str(provider)
    if model:
        request_payload["model"] = str(model)

    request = ProductWorkflowRequest.model_validate(request_payload)
    request = _apply_lab_runtime_request_overrides(
        request,
        workspace_root=workspace_root,
        explicit_fields=set(request_payload.keys()),
    )

    started_at = time.perf_counter()
    result = run_product_workflow(request)
    duration_s = round(time.perf_counter() - started_at, 4)
    structured_result = result.structured_result
    execution_metadata = structured_result.execution_metadata if structured_result is not None and isinstance(structured_result.execution_metadata, dict) else {}
    confidence = _safe_float(
        structured_result.overall_confidence if structured_result is not None and structured_result.overall_confidence is not None else execution_metadata.get("confidence"),
        _safe_float(structured_result.quality_score) if structured_result is not None and structured_result.quality_score is not None else 0.0,
    )
    needs_review = bool(execution_metadata.get("needs_review")) if execution_metadata else False
    review_reason = str(execution_metadata.get("needs_review_reason") or "").strip() if execution_metadata else ""
    source_count = len(structured_result.source_documents) if structured_result is not None else len(selected_document_ids)
    result_payload = result.model_dump(mode="json")
    result_items = _result_items_from_workflow_result(result)
    run_record = {
        "run_id": f"run_{_slugify(structured_result.execution_id if structured_result is not None else f'{task_id}-{time.time()}')}",
        "task_id": task_id,
        "workflow_id": workflow_id,
        "created_at": _normalize_timestamp(structured_result.executed_at.isoformat() if structured_result is not None else _now_iso()) or _now_iso(),
        "updated_at": _now_iso(),
        "status": result.status,
        "input_text": request.input_text,
        "document_ids": selected_document_ids,
        "document_names": selected_document_names,
        "provider": request.provider,
        "model": request.model,
        "latency_s": duration_s,
        "confidence": confidence,
        "needs_review": needs_review,
        "review_reason": review_reason or None,
        "source_count": source_count,
        "summary": result.summary,
        "result_title": f"Latest run · {_task_label(task_id)}",
        "execution_mode": str(execution_metadata.get("execution_strategy_used") or request.context_strategy or "product_workflow"),
        "result": {
            "summary": result.summary,
            "highlights": result.highlights,
            "recommendation": result.recommendation,
            "warnings": result.warnings,
            "result_items": result_items,
        },
        "raw_json": result_payload,
        "request_payload": request.model_dump(mode="json"),
        "response_payload": result_payload,
        "trace": {
            "provider": request.provider,
            "model": request.model,
            "workflow_id": workflow_id,
            "task_id": task_id,
            "duration_s": duration_s,
            "execution_metadata": execution_metadata,
        },
    }
    artifact_path = _write_lab_execution_artifact(
        workspace_root,
        category="workflow_runs",
        identifier=str(run_record["run_id"]),
        payload={
            "request": request.model_dump(mode="json"),
            "result": result_payload,
            "summary": {
                "task_id": task_id,
                "workflow_id": workflow_id,
                "duration_s": duration_s,
                "confidence": confidence,
                "needs_review": needs_review,
                "review_reason": review_reason or None,
            },
        },
    )
    run_record["artifact_path"] = str(artifact_path)
    persisted_run = append_lab_workflow_run(get_lab_workflow_runs_path(workspace_root), run_record)
    worklog_entry = _build_evidenceops_worklog_entry_from_workflow(run_record=persisted_run, result=result)
    append_evidenceops_worklog_entry(get_phase95_evidenceops_worklog_path(workspace_root), worklog_entry)
    append_evidenceops_actions_from_worklog_entry(get_phase95_evidenceops_action_store_path(workspace_root), worklog_entry)
    append_runtime_execution_log_entry(
        get_runtime_execution_log_path(workspace_root),
        _build_runtime_execution_log_entry(
            flow_type="structured",
            task_type=task_id,
            provider=request.provider,
            model=str(request.model or "unknown"),
            success=result.status in {"completed", "warning"},
            latency_s=duration_s,
            context_window=(request.context_window if request.context_window_mode == "manual" else None),
            context_window_mode=request.context_window_mode,
            embedding_provider=str(bootstrap.rag_settings.embedding_provider),
            embedding_model=str(bootstrap.rag_settings.embedding_model),
            rag_chunk_size=bootstrap.rag_settings.chunk_size,
            rag_chunk_overlap=bootstrap.rag_settings.chunk_overlap,
            rag_top_k=bootstrap.rag_settings.top_k,
            prompt_chars=len(request.input_text or ""),
            output_chars=len(result.summary or "") + sum(len(str(item or "")) for item in result.highlights),
            context_chars=_safe_int(execution_metadata.get("estimated_document_chars") or execution_metadata.get("context_chars")),
            total_tokens=_safe_int(execution_metadata.get("total_tokens") or execution_metadata.get("token_usage_total")),
            needs_review=needs_review,
            source_document_ids=selected_document_ids,
            error_message=(review_reason if result.status == "error" and review_reason else None),
            extra={
                "workflow_id": workflow_id,
                "execution_strategy_used": execution_metadata.get("execution_strategy_used"),
                "needs_review_reason": review_reason or None,
                "artifact_path": str(artifact_path),
            },
        ),
    )
    return {
        "ok": True,
        "request": request,
        "result": result,
        "run_record": persisted_run,
        "duration_s": duration_s,
    }


def _resolve_context_window_tokens(runtime_controls_state: dict[str, Any], latest_runtime_entry: dict[str, Any]) -> int:
    context_window = latest_runtime_entry.get("context_window")
    if isinstance(context_window, (int, float)) and int(context_window) > 0:
        return int(context_window)
    profile = runtime_controls_state.get("profile") if isinstance(runtime_controls_state.get("profile"), dict) else {}
    generation = profile.get("generation") if isinstance(profile.get("generation"), dict) else {}
    label = str(generation.get("contextWindow") or "auto").strip().lower()
    mapping = {
        "4k": 4096,
        "8k": 8192,
        "16k": 16384,
        "24k": 24576,
        "32k": 32768,
        "48k": 49152,
        "64k": 65536,
        "128k": 131072,
    }
    if label in mapping:
        return mapping[label]
    return 32768


def _build_runtime_snapshot(workspace_root: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    runtime_controls_state = _load_runtime_controls_state(workspace_root)
    profile = runtime_controls_state.get("profile") if isinstance(runtime_controls_state.get("profile"), dict) else {}
    generation = profile.get("generation") if isinstance(profile.get("generation"), dict) else {}
    retrieval = profile.get("retrieval") if isinstance(profile.get("retrieval"), dict) else {}
    doc_processing = profile.get("docProcessing") if isinstance(profile.get("docProcessing"), dict) else {}

    documents, document_lookup, total_chunks, vector_backend, vector_status = _build_document_catalog(workspace_root)
    runtime_log_entries = load_runtime_execution_log(get_runtime_execution_log_path(workspace_root))
    runtime_summary = summarize_runtime_execution_log(runtime_log_entries)
    latest_runtime_entry = runtime_log_entries[-1] if runtime_log_entries else {}
    document_agent_entries = load_document_agent_log(get_phase6_document_agent_log_path(workspace_root))
    document_agent_summary = summarize_document_agent_log(document_agent_entries)

    resolved_context = _resolve_context_window_tokens(runtime_controls_state, latest_runtime_entry)
    budget_total = _safe_int(latest_runtime_entry.get("context_budget_chars"))
    if budget_total <= 0:
        budget_total = resolved_context
    budget_used = _safe_int(latest_runtime_entry.get("context_chars"))
    if budget_used <= 0:
        budget_used = _safe_int(latest_runtime_entry.get("estimated_context_chars"))
    context_pressure = _safe_float(latest_runtime_entry.get("context_pressure_ratio"))
    if context_pressure <= 0 and budget_total > 0 and budget_used > 0:
        context_pressure = min(round(budget_used / budget_total, 4), 1.0)
    if context_pressure <= 0:
        context_pressure = min(_safe_float(runtime_summary.get("avg_context_pressure_ratio"), 0.18), 1.0)
    context_pressure = min(max(context_pressure, 0.0), 1.0)

    statuses = {str(item.get("status") or "pending") for item in documents}
    warnings_present = any(item.get("warnings") for item in documents)
    ingestion_health = "healthy"
    if "error" in statuses:
        ingestion_health = "error"
    elif "warning" in statuses or warnings_present or not documents:
        ingestion_health = "warning"

    runtime_snapshot = {
        "generationProvider": str(profile.get("primaryConnectionId") or latest_runtime_entry.get("provider") or "unknown"),
        "generationModel": str(profile.get("primaryModel") or latest_runtime_entry.get("model") or "unknown"),
        "promptProfile": str(generation.get("promptProfile") or "neutro"),
        "contextWindowMode": str(generation.get("contextWindow") or latest_runtime_entry.get("context_window_mode") or "auto"),
        "resolvedContext": resolved_context,
        "embeddingProvider": str(profile.get("embeddingConnectionId") or latest_runtime_entry.get("embedding_provider") or "unknown"),
        "embeddingModel": str(profile.get("embeddingModel") or latest_runtime_entry.get("embedding_model") or "unknown"),
        "retrievalStrategy": str(profile.get("retrievalStrategy") or latest_runtime_entry.get("retrieval_strategy_used") or "hybrid"),
        "chunkSize": _safe_int(retrieval.get("chunkSize"), _safe_int(latest_runtime_entry.get("rag_chunk_size"), 1200)),
        "chunkOverlap": _safe_int(retrieval.get("chunkOverlap"), _safe_int(latest_runtime_entry.get("rag_chunk_overlap"), 80)),
        "topK": _safe_int(retrieval.get("topK"), _safe_int(latest_runtime_entry.get("top_k_effective") or latest_runtime_entry.get("rag_top_k"), 4)),
        "rerankPoolSize": _safe_int(retrieval.get("rerankPoolSize"), _safe_int(latest_runtime_entry.get("rerank_pool_size_effective"), 8)),
        "rerankLexicalWeight": round(_safe_float(retrieval.get("rerankLexicalWeight"), 0.35), 2),
        "vectorBackend": vector_backend,
        "vectorBackendStatus": vector_status,
        "indexedDocumentCount": len(documents),
        "ingestionHealth": ingestion_health,
        "contextPressure": round(context_pressure, 3),
        "contextBudgetUsed": budget_used,
        "contextBudgetTotal": budget_total,
    }

    return (
        runtime_snapshot,
        runtime_controls_state,
        runtime_log_entries,
        runtime_summary,
        document_agent_entries,
        document_agent_summary,
        documents,
        document_lookup,
    )


def _top_document_agent_examples(entries: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for entry in reversed(entries):
        if not isinstance(entry, dict):
            continue
        if not entry.get("needs_review"):
            continue
        examples.append(
            {
                "timestamp": _normalize_timestamp(entry.get("timestamp")),
                "query": str(entry.get("query") or "").strip(),
                "tool_used": str(entry.get("tool_used") or "").strip(),
                "confidence": round(_safe_float(entry.get("confidence")), 2) if entry.get("confidence") is not None else None,
                "needs_review_reason": str(entry.get("needs_review_reason") or "").strip() or None,
                "source_count": _safe_int(entry.get("source_count")),
            }
        )
        if len(examples) >= limit:
            break
    return examples


def _workflow_mix(history_entries: list[dict[str, Any]], document_agent_entries: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]], int]:
    if history_entries:
        counter = Counter(str(item.get("workflow_label") or item.get("workflow_id") or "Workflow") for item in history_entries)
        mix = [{"name": name, "value": count} for name, count in counter.most_common(6)]
        review_rate = round(
            100 * sum(1 for item in history_entries if str(item.get("status") or "").strip().lower() == "warning") / max(len(history_entries), 1)
        )
        return "Workflow Mix", mix, review_rate

    tool_counter = Counter(str(item.get("tool_used") or "unknown") for item in document_agent_entries if isinstance(item, dict))
    mix = [
        {
            "name": TOOL_LABELS.get(name, _labelize_slug(name)),
            "value": count,
        }
        for name, count in tool_counter.most_common(6)
    ]
    review_rate = round(
        100 * sum(1 for item in document_agent_entries if bool(item.get("needs_review"))) / max(len(document_agent_entries), 1)
    )
    return "Observed Task Mix", mix, review_rate


def _severity_from_fail_rate(fail_rate: float) -> str:
    if fail_rate >= 0.5:
        return "critical"
    if fail_rate >= 0.2:
        return "warning"
    return "info"


def _build_overview_alerts(
    *,
    eval_diagnosis: dict[str, Any],
    document_agent_entries: list[dict[str, Any]],
    runtime_summary: dict[str, Any],
    action_summary: dict[str, Any],
    drift_summary: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    for candidate in (eval_diagnosis.get("next_eval_priorities") or [])[:2]:
        if not isinstance(candidate, dict):
            continue
        fail_rate = _safe_float(candidate.get("fail_rate"))
        reason = str(candidate.get("recommended_action") or "Iteration required.").replace("_", " ")
        alerts.append(
            {
                "id": f"eval-{_slugify(candidate.get('task_type'))}",
                "severity": _severity_from_fail_rate(fail_rate),
                "title": f"Eval attention required: {candidate.get('task_type')}",
                "detail": f"Fail rate {round(fail_rate * 100)}% · {reason}.",
                "source": "Evals",
                "timestamp": None,
            }
        )

    for example in _top_document_agent_examples(document_agent_entries, limit=2):
        query_preview = str(example.get("query") or "recent document-agent run").strip()
        if len(query_preview) > 90:
            query_preview = f"{query_preview[:87]}..."
        alerts.append(
            {
                "id": f"trace-{_slugify(example.get('timestamp') or query_preview)}",
                "severity": "warning",
                "title": f"Manual review triggered in {TOOL_LABELS.get(str(example.get('tool_used') or ''), 'document agent')}",
                "detail": f"{example.get('needs_review_reason') or 'review requested'} · {query_preview}",
                "source": "Runtime Trace",
                "timestamp": example.get("timestamp"),
            }
        )

    error_rate = _safe_float(runtime_summary.get("error_rate"))
    avg_latency_s = _safe_float(runtime_summary.get("avg_latency_s"))
    if error_rate > 0 or avg_latency_s > 60:
        alerts.append(
            {
                "id": "runtime-health",
                "severity": "warning" if error_rate <= 0.2 else "critical",
                "title": "Runtime executions show degraded stability",
                "detail": f"Error rate {round(error_rate * 100)}% · average latency {_format_duration_label(avg_latency_s)}.",
                "source": "Runtime",
                "timestamp": _normalize_timestamp(runtime_summary.get("latest_timestamp")),
            }
        )

    if _safe_int(action_summary.get("unassigned_open_actions")) > 0:
        alerts.append(
            {
                "id": "evidenceops-unassigned",
                "severity": "warning",
                "title": "EvidenceOps has unassigned open actions",
                "detail": f"{action_summary.get('unassigned_open_actions')} action(s) still lack an owner.",
                "source": "EvidenceOps",
                "timestamp": _normalize_timestamp(action_summary.get("latest_created_at")),
            }
        )

    if drift_summary and (
        _safe_int(drift_summary.get("new_documents_count")) > 0
        or _safe_int(drift_summary.get("changed_documents_count")) > 0
        or _safe_int(drift_summary.get("removed_documents_count")) > 0
    ):
        alerts.append(
            {
                "id": "evidenceops-drift",
                "severity": "info" if _safe_int(drift_summary.get("removed_documents_count")) == 0 else "warning",
                "title": "EvidenceOps repository drift detected",
                "detail": (
                    f"New: {drift_summary.get('new_documents_count', 0)} · "
                    f"Changed: {drift_summary.get('changed_documents_count', 0)} · "
                    f"Removed: {drift_summary.get('removed_documents_count', 0)}."
                ),
                "source": "EvidenceOps",
                "timestamp": _now_iso(),
            }
        )

    if not alerts:
        alerts.append(
            {
                "id": "no-alerts",
                "severity": "info",
                "title": "No blocking AI LAB alerts detected",
                "detail": "The dashboard is backed by current runtime logs, eval history and repository state.",
                "source": "AI Lab",
                "timestamp": _now_iso(),
            }
        )

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda item: (severity_order.get(str(item.get("severity")), 99), str(item.get("timestamp") or "")), reverse=False)
    return alerts[:6]


def _resolve_evidenceops_root(workspace_root: Path) -> Path:
    settings = get_evidenceops_external_settings()
    if settings.corpus_primary_root.exists():
        return settings.corpus_primary_root
    if settings.corpus_public_root.exists():
        return settings.corpus_public_root
    fallback = workspace_root / "data" / "corpus_revisado"
    return fallback if fallback.exists() else settings.corpus_primary_root


def _compute_repository_drift(workspace_root: Path, repository_root: Path) -> dict[str, Any] | None:
    if not repository_root.exists() or not repository_root.is_dir():
        return None
    snapshot_path = get_phase95_evidenceops_repository_snapshot_path(workspace_root)
    previous_snapshot = load_evidenceops_repository_snapshot(snapshot_path)
    current_snapshot = build_evidenceops_repository_snapshot(repository_root)
    drift = diff_evidenceops_repository_snapshots(previous_snapshot, current_snapshot)
    return drift if isinstance(drift, dict) else None


def build_lab_overview_payload(workspace_root: str | Path) -> dict[str, Any]:
    resolved_root = Path(workspace_root)
    (
        runtime_snapshot,
        runtime_controls_state,
        runtime_log_entries,
        runtime_summary,
        document_agent_entries,
        document_agent_summary,
        documents,
        _,
    ) = _build_runtime_snapshot(resolved_root)
    history_entries = _load_workflow_history(resolved_root)
    eval_entries = load_eval_runs(get_phase8_eval_db_path(resolved_root), limit=250)
    eval_summary = summarize_eval_runs(eval_entries)
    eval_diagnosis = build_eval_diagnosis(eval_entries)
    action_entries = load_evidenceops_actions(get_phase95_evidenceops_action_store_path(resolved_root))
    action_summary = summarize_evidenceops_actions(action_entries)
    repository_root = _resolve_evidenceops_root(resolved_root)
    drift_summary = _compute_repository_drift(resolved_root, repository_root)
    mix_label, workflow_mix, review_rate = _workflow_mix(history_entries, document_agent_entries)

    pass_rate = round(_safe_float(eval_summary.get("pass_rate")) * 100)
    avg_latency = _safe_float(runtime_summary.get("avg_latency_s"))
    total_chunks = sum(_safe_int(item.get("chunk_count")) for item in documents)
    kpis = [
        {
            "label": "Indexed Documents",
            "value": runtime_snapshot.get("indexedDocumentCount", 0),
            "status": "healthy" if runtime_snapshot.get("indexedDocumentCount", 0) else "warning",
        },
        {
            "label": "Total Chunks",
            "value": f"{total_chunks:,}",
            "status": "healthy" if total_chunks else "warning",
        },
        {
            "label": "Workflow Runs",
            "value": len(history_entries) or _safe_int(runtime_summary.get("total_runs")),
            "status": "neutral",
        },
        {
            "label": "Open Actions",
            "value": _safe_int(action_summary.get("open_actions")) or _safe_int(action_summary.get("recommended_actions")),
            "status": "warning" if _safe_int(action_summary.get("total_actions")) > 0 else "healthy",
        },
        {
            "label": "Eval Pass Rate",
            "value": f"{pass_rate}%",
            "status": "healthy" if pass_rate >= 80 else "warning" if pass_rate >= 60 else "error",
        },
        {
            "label": "Avg Latency",
            "value": _format_duration_label(avg_latency),
            "status": "healthy" if avg_latency <= 30 else "warning" if avg_latency <= 90 else "error",
        },
    ]

    alerts = _build_overview_alerts(
        eval_diagnosis=eval_diagnosis,
        document_agent_entries=document_agent_entries,
        runtime_summary=runtime_summary,
        action_summary=action_summary,
        drift_summary=drift_summary,
    )

    notes: list[str] = []
    if not history_entries:
        notes.append("Workflow mix falls back to document-agent traces because product workflow history is empty.")
    if not runtime_log_entries:
        notes.append("Runtime latency and context pressure will update when new executions are recorded.")

    return {
        "ok": True,
        "meta": _build_meta(
            source="derived",
            updated_at=_normalize_timestamp(runtime_controls_state.get("updated_at")) or _normalize_timestamp(runtime_summary.get("latest_timestamp")) or _now_iso(),
            notes=notes,
        ),
        "runtime": runtime_snapshot,
        "kpis": kpis,
        "alerts": alerts,
        "workflow_mix_label": mix_label,
        "workflow_mix": workflow_mix,
        "review_rate": review_rate,
    }


def build_lab_runtime_payload(workspace_root: str | Path) -> dict[str, Any]:
    resolved_root = Path(workspace_root)
    (
        runtime_snapshot,
        runtime_controls_state,
        runtime_log_entries,
        runtime_summary,
        _,
        document_agent_summary,
        documents,
        _,
    ) = _build_runtime_snapshot(resolved_root)

    profile = runtime_controls_state.get("profile") if isinstance(runtime_controls_state.get("profile"), dict) else {}
    generation = profile.get("generation") if isinstance(profile.get("generation"), dict) else {}
    retrieval = profile.get("retrieval") if isinstance(profile.get("retrieval"), dict) else {}
    doc_processing = profile.get("docProcessing") if isinstance(profile.get("docProcessing"), dict) else {}
    total_chunks = sum(_safe_int(item.get("chunk_count")) for item in documents)

    generation_rows = [
        {"label": "Provider", "value": runtime_snapshot.get("generationProvider")},
        {"label": "Model", "value": runtime_snapshot.get("generationModel")},
        {"label": "Prompt Profile", "value": runtime_snapshot.get("promptProfile")},
        {"label": "Context Window", "value": runtime_snapshot.get("contextWindowMode")},
        {"label": "Resolved Context", "value": f"{_safe_int(runtime_snapshot.get('resolvedContext')):,} tokens"},
    ]
    retrieval_rows = [
        {"label": "Embedding Provider", "value": runtime_snapshot.get("embeddingProvider")},
        {"label": "Embedding Model", "value": runtime_snapshot.get("embeddingModel")},
        {"label": "Strategy", "value": runtime_snapshot.get("retrievalStrategy")},
        {"label": "Chunk Size / Overlap", "value": f"{runtime_snapshot.get('chunkSize')} / {runtime_snapshot.get('chunkOverlap')}"},
        {"label": "Top-K", "value": str(runtime_snapshot.get("topK"))},
        {"label": "Rerank Pool", "value": str(runtime_snapshot.get("rerankPoolSize"))},
        {"label": "Lexical Weight", "value": str(runtime_snapshot.get("rerankLexicalWeight"))},
    ]
    vector_rows = [
        {"label": "Backend", "value": runtime_snapshot.get("vectorBackend")},
        {"label": "Status", "value": runtime_snapshot.get("vectorBackendStatus")},
        {"label": "Indexed Documents", "value": str(runtime_snapshot.get("indexedDocumentCount"))},
        {"label": "Total Chunks", "value": f"{total_chunks:,}"},
    ]
    diagnostics_rows = [
        {"label": "OCR Backend", "value": str(doc_processing.get("ocrBackend") or "not configured")},
        {"label": "PDF Extraction", "value": str(doc_processing.get("pdfExtractionMode") or "default")},
        {"label": "VLM Enhancement", "value": "Enabled" if bool(doc_processing.get("vlmEnhancement")) else "Standby"},
        {"label": "Execution Policy", "value": str(profile.get("executionPolicy") or "balanced")},
        {"label": "Recent Traces", "value": str(len(runtime_log_entries))},
        {"label": "Needs Review Rate", "value": f"{round(_safe_float(document_agent_summary.get('needs_review_rate')) * 100)}%"},
    ]

    notes: list[str] = []
    if not runtime_log_entries:
        notes.append("No runtime execution traces were found, so diagnostic rows come only from the persisted runtime profile.")
    if _safe_float(runtime_summary.get("avg_context_pressure_ratio")) == 0 and runtime_snapshot.get("contextPressure", 0) == 0:
        notes.append("Context pressure is derived from the latest trace that recorded context budget fields.")
    if not documents:
        notes.append("The vector backend is present, but no indexed documents are currently available in the RAG store.")

    return {
        "ok": True,
        "meta": _build_meta(
            source="derived",
            updated_at=_normalize_timestamp(runtime_controls_state.get("updated_at")) or _normalize_timestamp(runtime_summary.get("latest_timestamp")) or _now_iso(),
            notes=notes,
        ),
        "runtime": runtime_snapshot,
        "generation_rows": generation_rows,
        "retrieval_rows": retrieval_rows,
        "vector_rows": vector_rows,
        "diagnostics_rows": diagnostics_rows,
    }


def _build_chat_messages(
    *,
    chat_history: list[dict[str, Any]],
    chat_runs: list[dict[str, Any]],
    document_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    recent_user_messages = [item for item in chat_history if str(item.get("role") or "").strip().lower() == "user"][-4:]
    recent_chat_runs = [item for item in chat_runs if isinstance(item, dict)][-4:]

    for index, item in enumerate(recent_user_messages):
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        document_names = _resolve_document_names(metadata.get("source_document_ids") if isinstance(metadata.get("source_document_ids"), list) else [], document_lookup)
        messages.append(
            {
                "id": f"chat-user-{index}",
                "role": "user",
                "content": str(item.get("content") or "").strip(),
                "timestamp": None,
                "sources": [
                    {
                        "label": name,
                        "detail": "captured source selection",
                    }
                    for name in document_names[:4]
                ],
            }
        )

    for index, run in enumerate(recent_chat_runs):
        source_names = _resolve_document_names(run.get("source_document_ids") if isinstance(run.get("source_document_ids"), list) else [], document_lookup)
        context_budget = _safe_int(run.get("context_budget_chars"))
        context_chars = _safe_int(run.get("context_chars") or run.get("estimated_context_chars"))
        usage_label = "—"
        total_tokens = _safe_int(run.get("total_tokens"))
        if total_tokens > 0:
            usage_label = f"{total_tokens:,} tokens"
        elif context_chars > 0 and context_budget > 0:
            usage_label = f"{context_chars:,} / {context_budget:,} context chars"
        message_lines = [
            "Assistant response text is not persisted in the current chat runtime history.",
            "This card shows the live execution trace that replaced the former mock reply playback.",
            "",
            f"Model: {run.get('provider')} · {run.get('model')}",
            f"Latency: {_format_duration_label(_safe_float(run.get('latency_s')))}",
            f"Retrieved chunks: {_safe_int(run.get('retrieved_chunks_count'))}",
            f"Usage: {usage_label}",
        ]
        if source_names:
            message_lines.append(f"Documents: {', '.join(source_names[:3])}")
        messages.append(
            {
                "id": f"chat-trace-{index}",
                "role": "assistant",
                "content": "\n".join(message_lines).strip(),
                "timestamp": _normalize_timestamp(run.get("timestamp")),
                "sources": [
                    {
                        "label": name,
                        "detail": f"{_safe_int(run.get('retrieved_chunks_count'))} chunk(s) observed",
                        "score": round(_safe_float(run.get("context_pressure_ratio")) * 100, 1) if run.get("context_pressure_ratio") is not None else None,
                    }
                    for name in source_names[:4]
                ],
            }
        )

    return messages


def build_lab_chat_payload(workspace_root: str | Path, *, session_id: str | None = None) -> dict[str, Any]:
    resolved_root = Path(workspace_root)
    (
        runtime_snapshot,
        runtime_controls_state,
        runtime_log_entries,
        runtime_summary,
        _,
        _,
        documents,
        document_lookup,
    ) = _build_runtime_snapshot(resolved_root)
    sessions = load_lab_chat_sessions(get_lab_chat_sessions_path(resolved_root))
    provider_runtime = _resolve_live_provider_profile(runtime_controls_state, capability="chat")
    can_send = bool(provider_runtime.get("available"))
    capability_reason = None
    if not can_send:
        capability_reason = "No chat-capable provider is available in the current runtime configuration."

    active_session = None
    if session_id:
        active_session = get_lab_chat_session(get_lab_chat_sessions_path(resolved_root), session_id)
    if active_session is None and sessions:
        active_session = sessions[0]

    if active_session is not None:
        payload = _build_chat_payload_from_session(
            session=active_session,
            documents=documents,
            document_lookup=document_lookup,
            runtime_snapshot=runtime_snapshot,
            runtime_controls_state=runtime_controls_state,
            can_send=can_send,
            capability_reason=capability_reason,
            provider_runtime=provider_runtime,
        )
        payload["sessions"] = _summarize_chat_sessions_for_payload(sessions)
        payload.setdefault("capabilities", {})["reason"] = capability_reason
        return payload

    chat_history = _load_chat_history(resolved_root)
    chat_runs = [entry for entry in runtime_log_entries if str(entry.get("flow_type") or "") == "chat_rag"]
    latest_chat_run = chat_runs[-1] if chat_runs else {}
    messages = _build_chat_messages(chat_history=chat_history, chat_runs=chat_runs, document_lookup=document_lookup)

    selected_document_names = _resolve_document_names(latest_chat_run.get("source_document_ids") if isinstance(latest_chat_run.get("source_document_ids"), list) else [], document_lookup)
    selected_documents = [
        (document_lookup.get(str(document_id)) or {})
        for document_id in (latest_chat_run.get("source_document_ids") if isinstance(latest_chat_run.get("source_document_ids"), list) else [])
        if document_lookup.get(str(document_id or ""))
    ]
    if not selected_documents:
        selected_documents = documents[:4]

    avg_chat_latency = 0.0
    if chat_runs:
        avg_chat_latency = round(sum(_safe_float(item.get("latency_s")) for item in chat_runs) / max(len(chat_runs), 1), 2)
    total_tokens = _safe_int(latest_chat_run.get("total_tokens"))
    context_budget = _safe_int(latest_chat_run.get("context_budget_chars"))
    context_used = _safe_int(latest_chat_run.get("context_chars") or latest_chat_run.get("estimated_context_chars"))
    session_diagnostics = [
        {"label": "Messages", "value": str(len(messages))},
        {"label": "Tokens used", "value": f"{total_tokens:,}" if total_tokens else "—"},
        {"label": "Avg latency", "value": _format_duration_label(avg_chat_latency) if avg_chat_latency else "—"},
        {"label": "Model", "value": str(latest_chat_run.get("model") or provider_runtime.get("model") or runtime_snapshot.get("generationModel"))},
        {"label": "Top-K", "value": str(latest_chat_run.get("top_k_effective") or latest_chat_run.get("rag_top_k") or runtime_snapshot.get("topK"))},
        {"label": "Context used", "value": f"{context_used:,} / {context_budget:,}" if context_used and context_budget else "—"},
    ]
    retrieval_quality = [
        {"label": "Strategy", "value": str(latest_chat_run.get("retrieval_strategy_used") or runtime_snapshot.get("retrievalStrategy"))},
        {"label": "Backend", "value": str(latest_chat_run.get("retrieval_backend_used") or runtime_snapshot.get("vectorBackend"))},
        {"label": "Retrieved chunks", "value": str(_safe_int(latest_chat_run.get("retrieved_chunks_count")))},
        {"label": "Rerank pool", "value": str(runtime_snapshot.get("rerankPoolSize"))},
        {"label": "Context pressure", "value": f"{round(_safe_float(latest_chat_run.get('context_pressure_ratio') or runtime_snapshot.get('contextPressure')) * 100)}%"},
    ]

    notes = [
        "This page now prefers persisted AI LAB chat sessions and live execution. When no session exists yet, it falls back to observed chat traces and runtime history.",
    ]
    if not chat_runs:
        notes.append("No historical chat_rag traces were found yet; diagnostics currently reflect the active runtime profile.")
    if can_send:
        notes.append("Live chat execution is enabled for this workspace.")
    elif capability_reason:
        notes.append(capability_reason)

    suggested_prompts: list[str] = []
    for item in reversed(chat_history):
        content = str(item.get("content") or "").strip()
        if content and content not in suggested_prompts:
            suggested_prompts.append(content)
        if len(suggested_prompts) >= 3:
            break
    if len(suggested_prompts) < 3:
        for name in selected_document_names[:3]:
            prompt = f"Summarize the main operational takeaways in {name}."
            if prompt not in suggested_prompts:
                suggested_prompts.append(prompt)
            if len(suggested_prompts) >= 3:
                break
    if len(suggested_prompts) < 3:
        for prompt in [
            "Summarize the highest-priority findings in the selected documents.",
            "What evidence supports the main conclusion?",
            "List the missing evidence and next validation steps.",
        ]:
            if prompt not in suggested_prompts:
                suggested_prompts.append(prompt)
            if len(suggested_prompts) >= 3:
                break

    return {
        "ok": True,
        "meta": _build_meta(
            source="live" if can_send else "derived",
            updated_at=_normalize_timestamp(runtime_controls_state.get("updated_at")) or _normalize_timestamp(latest_chat_run.get("timestamp")) or _now_iso(),
            notes=notes,
        ),
        "capabilities": {
            "can_send": can_send,
            "reason": capability_reason,
        },
        "active_session_id": None,
        "sessions": _summarize_chat_sessions_for_payload(sessions),
        "messages": messages,
        "suggested_prompts": suggested_prompts[:3],
        "selected_documents": selected_documents,
        "session_diagnostics": session_diagnostics,
        "retrieval_quality": retrieval_quality,
    }


def _task_label(task_id: str) -> str:
    return TOOL_LABELS.get(task_id, WORKFLOW_LABELS.get(task_id, _labelize_slug(task_id)))


def _task_description(task_id: str) -> str:
    return TOOL_DESCRIPTIONS.get(task_id, f"Observed execution traces for { _task_label(task_id).lower() }.")


def _match_runtime_entry(trace_entry: dict[str, Any], runtime_entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    trace_timestamp = _parse_timestamp(trace_entry.get("timestamp"))
    trace_provider = str(trace_entry.get("provider") or "").strip()
    trace_model = str(trace_entry.get("model") or "").strip()
    if trace_timestamp is None:
        return None
    candidates: list[tuple[float, dict[str, Any]]] = []
    for runtime_entry in runtime_entries:
        runtime_timestamp = _parse_timestamp(runtime_entry.get("timestamp"))
        if runtime_timestamp is None:
            continue
        provider = str(runtime_entry.get("provider") or "").strip()
        model = str(runtime_entry.get("model") or "").strip()
        if trace_provider and provider and provider != trace_provider:
            continue
        if trace_model and model and model != trace_model:
            continue
        delta = abs((runtime_timestamp - trace_timestamp).total_seconds())
        if delta <= 10:
            candidates.append((delta, runtime_entry))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _build_task_details(
    *,
    document_agent_entries: list[dict[str, Any]],
    runtime_entries: list[dict[str, Any]],
    action_entries: list[dict[str, Any]],
    document_lookup: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in document_agent_entries:
        task_id = str(entry.get("tool_used") or entry.get("task_type") or "document_agent").strip() or "document_agent"
        grouped[task_id].append(entry)

    task_options: list[dict[str, Any]] = []
    task_details: dict[str, dict[str, Any]] = {}
    recent_cases: list[dict[str, Any]] = []

    sorted_groups = sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True)
    for task_id, entries in sorted_groups:
        ordered_entries = sorted(
            entries,
            key=lambda item: _parse_timestamp(item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        latest = ordered_entries[0]
        latest_runtime = _match_runtime_entry(latest, runtime_entries)
        document_names = _resolve_document_names(latest.get("document_ids") if isinstance(latest.get("document_ids"), list) else [], document_lookup)
        latest_actions = [item for item in action_entries if str(item.get("tool_used") or "").strip() == task_id][:3]

        result_items: list[dict[str, Any]] = []
        for action in latest_actions:
            result_items.append(
                {
                    "label": _labelize_slug(action.get("action_type") or "action"),
                    "value": str(action.get("description") or "").strip(),
                    "confidence": round(_safe_float(action.get("confidence")), 2) if action.get("confidence") is not None else None,
                }
            )
        if not result_items:
            result_items = [
                {"label": "Query", "value": str(latest.get("query") or "").strip() or "—", "confidence": None},
                {"label": "Answer mode", "value": str(latest.get("answer_mode") or "—"), "confidence": None},
                {"label": "Review reason", "value": str(latest.get("needs_review_reason") or "No review requested"), "confidence": None},
                {"label": "Documents", "value": ", ".join(document_names[:3]) if document_names else "No persisted source ids", "confidence": None},
            ]

        trace_fields = [
            {"label": "Tool", "value": task_id},
            {"label": "Intent", "value": str(latest.get("user_intent") or latest.get("review_type") or "—")},
            {"label": "Confidence", "value": f"{round(_safe_float(latest.get('confidence')) * 100)}%" if latest.get("confidence") is not None else "—"},
            {"label": "Source Count", "value": str(_safe_int(latest.get("source_count")))},
            {"label": "Available Tools", "value": str(_safe_int(latest.get("available_tools_count")))},
            {"label": "Needs Review", "value": "Yes" if latest.get("needs_review") else "No"},
            {"label": "Review Reason", "value": str(latest.get("needs_review_reason") or "—")},
            {"label": "Timestamp", "value": _normalize_timestamp(latest.get("timestamp")) or "—"},
        ]
        if latest_runtime is not None:
            trace_fields.extend(
                [
                    {"label": "Provider", "value": str(latest_runtime.get("provider") or "—")},
                    {"label": "Model", "value": str(latest_runtime.get("model") or "—")},
                    {"label": "Latency", "value": _format_duration_label(_safe_float(latest_runtime.get("latency_s")))},
                    {"label": "Context Window", "value": str(latest_runtime.get("context_window") or "—")},
                ]
            )

        executions: list[dict[str, Any]] = []
        for index, entry in enumerate(ordered_entries[:4]):
            matched_runtime = _match_runtime_entry(entry, runtime_entries)
            executions.append(
                {
                    "id": f"{task_id}-{index}",
                    "mode": str(entry.get("execution_strategy_used") or matched_runtime.get("flow_type") if isinstance(matched_runtime, dict) else "observed_trace") or "observed_trace",
                    "status": "failed" if not entry.get("success") else ("warning" if entry.get("needs_review") else "completed"),
                    "confidence": round(_safe_float(entry.get("confidence")), 3) if entry.get("confidence") is not None else 0.0,
                    "source_count": _safe_int(entry.get("source_count")),
                    "latency_s": round(_safe_float(matched_runtime.get("latency_s")), 3) if isinstance(matched_runtime, dict) and matched_runtime.get("latency_s") is not None else None,
                    "provider": str((matched_runtime or {}).get("provider") or entry.get("provider") or "").strip() or None,
                    "model": str((matched_runtime or {}).get("model") or entry.get("model") or "").strip() or None,
                    "needs_review": bool(entry.get("needs_review")),
                    "review_reason": str(entry.get("needs_review_reason") or "").strip() or None,
                    "timestamp": _normalize_timestamp(entry.get("timestamp")),
                }
            )

        task_options.append(
            {
                "id": task_id,
                "label": _task_label(task_id),
                "description": _task_description(task_id),
                "recent_count": len(entries),
            }
        )
        task_details[task_id] = {
            "id": task_id,
            "label": _task_label(task_id),
            "description": _task_description(task_id),
            "document_names": document_names,
            "result_title": "Latest persisted trace",
            "result_items": result_items,
            "trace_fields": trace_fields,
            "raw_json": latest,
            "executions": executions,
        }

        for entry in ordered_entries[:8]:
            source_names = _resolve_document_names(entry.get("document_ids") if isinstance(entry.get("document_ids"), list) else [], document_lookup)
            recent_cases.append(
                {
                    "id": f"{task_id}-{_slugify(entry.get('timestamp') or entry.get('query') or len(recent_cases))}",
                    "task": _task_label(task_id),
                    "document": ", ".join(source_names[:2]) if source_names else "No current indexed source",
                    "mode": str(entry.get("execution_strategy_used") or "observed_trace"),
                    "status": "failed" if not entry.get("success") else ("warning" if entry.get("needs_review") else "completed"),
                    "needsReview": bool(entry.get("needs_review")),
                    "confidence": round(_safe_float(entry.get("confidence")), 3) if entry.get("confidence") is not None else 0.0,
                    "sourceCount": _safe_int(entry.get("source_count")),
                    "timestamp": _normalize_timestamp(entry.get("timestamp")),
                    "reviewReason": str(entry.get("needs_review_reason") or "").strip() or None,
                }
            )

    recent_cases.sort(
        key=lambda item: _parse_timestamp(item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return task_options, task_details, recent_cases[:24]


def build_lab_workflow_inspector_payload(workspace_root: str | Path, *, task_id: str | None = None) -> dict[str, Any]:
    resolved_root = Path(workspace_root)
    (
        _,
        runtime_controls_state,
        runtime_entries,
        runtime_summary,
        document_agent_entries,
        document_agent_summary,
        documents,
        document_lookup,
    ) = _build_runtime_snapshot(resolved_root)
    action_entries = load_evidenceops_actions(get_phase95_evidenceops_action_store_path(resolved_root))
    task_options, task_details, recent_cases = _build_task_details(
        document_agent_entries=document_agent_entries,
        runtime_entries=runtime_entries,
        action_entries=action_entries,
        document_lookup=document_lookup,
    )
    workflow_runs = load_lab_workflow_runs(get_lab_workflow_runs_path(resolved_root))
    task_option_by_id = {str(item.get("id") or ""): item for item in task_options}

    for run in workflow_runs:
        run_task_id = str(run.get("task_id") or run.get("workflow_id") or "document_review")
        task_option = task_option_by_id.get(run_task_id)
        if task_option is None:
            task_option = {
                "id": run_task_id,
                "label": _task_label(run_task_id),
                "description": _task_description(run_task_id),
                "recent_count": 0,
            }
            task_option_by_id[run_task_id] = task_option
            task_options.append(task_option)
        task_option["recent_count"] = _safe_int(task_option.get("recent_count")) + 1
        existing_detail = task_details.get(run_task_id) if isinstance(task_details.get(run_task_id), dict) else None
        task_details[run_task_id] = _workflow_task_detail_from_run_record(run, existing=existing_detail)
        recent_cases.append(_workflow_case_from_run_record(run))

    recent_cases.sort(
        key=lambda item: _parse_timestamp(item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    task_options.sort(key=lambda item: (-_safe_int(item.get("recent_count")), str(item.get("label") or "").lower()))

    avg_confidence = 0
    if recent_cases:
        confidence_values = [_safe_float(item.get("confidence")) for item in recent_cases if item.get("confidence") is not None]
        if confidence_values:
            avg_confidence = round((sum(confidence_values) / max(len(confidence_values), 1)) * 100)
    elif _safe_float(document_agent_summary.get("avg_confidence")) > 0:
        avg_confidence = round(_safe_float(document_agent_summary.get("avg_confidence")) * 100)

    summary = {
        "total_cases": len(recent_cases),
        "needs_review": sum(1 for item in recent_cases if bool(item.get("needsReview"))),
        "avg_confidence": avg_confidence,
        "review_blockers": len(document_agent_summary.get("review_reasons") or {}),
        "failed": sum(1 for item in recent_cases if str(item.get("status") or "") == "failed"),
    }

    provider_runtime = _resolve_live_provider_profile(runtime_controls_state, capability="chat")
    can_execute = bool(provider_runtime.get("available")) and bool(documents)
    capability_reason = None
    if not documents:
        capability_reason = "At least one indexed document is required to execute a live workflow run from AI LAB."
    elif not provider_runtime.get("available"):
        capability_reason = "No chat-capable provider is available in the current runtime configuration."

    selected_task_id = str(task_id or "").strip() or (workflow_runs[0].get("task_id") if workflow_runs else None) or (task_options[0].get("id") if task_options else None)
    notes = [
        "This page now combines persisted workflow traces with live AI LAB executions triggered through the Product API.",
    ]
    if workflow_runs:
        notes.append(f"{len(workflow_runs)} persisted AI LAB workflow run(s) are available for replay and inspection.")
    if can_execute:
        notes.append("Live execution is enabled for this workspace.")
    elif capability_reason:
        notes.append(capability_reason)

    return {
        "ok": True,
        "meta": _build_meta(
            source="live" if can_execute else "derived",
            updated_at=_normalize_timestamp(runtime_controls_state.get("updated_at")) or _normalize_timestamp(runtime_summary.get("latest_timestamp")) or _now_iso(),
            notes=notes,
        ),
        "capabilities": {
            "can_execute": can_execute,
            "reason": capability_reason,
        },
        "summary": summary,
        "document_options": [
            {
                "id": item.get("document_id"),
                "name": item.get("name"),
                "status": item.get("status"),
            }
            for item in documents
        ],
        "task_options": task_options,
        "selected_task_id": selected_task_id,
        "task_details": task_details,
        "recent_cases": recent_cases[:24],
    }


def _load_phase7_comparison_log(workspace_root: Path) -> list[dict[str, Any]]:
    payload = _read_json_file(get_phase7_model_comparison_log_path(workspace_root), [])
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _derive_runtime_bucket(provider: str, model_name: str) -> str:
    if provider == "huggingface_inference":
        return "cloud_api"
    if provider == "huggingface_server":
        return "local_service"
    if provider == "ollama" and "cloud" in model_name.lower():
        return "ollama_remote"
    if provider == "ollama":
        return "local_runtime"
    return provider or "unknown"


def _profile_tag_for_model(*, rank: int, provider: str, latency: float, model_name: str) -> str:
    if rank == 0:
        return "Recommended production"
    if provider == "huggingface_inference":
        return "External reference"
    if latency <= 1.0:
        return "Fastest observed"
    if "cloud" in model_name.lower():
        return "Hosted candidate"
    return "Benchmark candidate"


def _build_benchmark_models(workspace_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    comparison_runs = _load_phase7_comparison_log(workspace_root)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    preset_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    retrieval_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    notes: list[str] = []

    for run in comparison_runs:
        retrieval_strategy = str(run.get("retrieval_strategy") or "observed_runtime").strip() or "observed_runtime"
        prompt_profile = str(run.get("prompt_profile") or "neutro").strip() or "neutro"
        response_format = str(run.get("response_format") or "plain_text").strip() or "plain_text"
        candidates = run.get("candidate_results") if isinstance(run.get("candidate_results"), list) else []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            provider = str(candidate.get("provider_effective") or candidate.get("provider_requested") or "unknown").strip() or "unknown"
            model_name = str(candidate.get("model_effective") or candidate.get("model_requested") or "unknown").strip() or "unknown"
            normalized = {
                "provider": provider,
                "model": model_name,
                "latency_s": _safe_float(candidate.get("latency_s")),
                "output_chars": _safe_int(candidate.get("output_chars")),
                "format_adherence": min(max(_safe_float(candidate.get("format_adherence"), 0.0), 0.0), 1.0),
                "context_injected": bool(candidate.get("context_injected")),
                "used_chunks": _safe_int(candidate.get("used_chunks")),
                "dropped_chunks": _safe_int(candidate.get("dropped_chunks")),
                "success": bool(candidate.get("success")),
                "prompt_profile": prompt_profile,
                "response_format": response_format,
                "retrieval_strategy": retrieval_strategy,
                "timestamp": _normalize_timestamp(run.get("timestamp")),
            }
            grouped[(provider, model_name)].append(normalized)
            preset_groups[(retrieval_strategy, prompt_profile, response_format)].append(normalized)
            retrieval_groups[retrieval_strategy].append(normalized)

    if not grouped:
        notes.append("No phase7 model comparison log was found. Benchmarks will populate when comparison runs are recorded.")
        return [], [], [], notes

    min_latency = min(_safe_float(item.get("latency_s"), 1.0) for values in grouped.values() for item in values if _safe_float(item.get("latency_s"), 0.0) > 0)
    max_used_chunks = max(_safe_int(item.get("used_chunks"), 1) for values in grouped.values() for item in values) or 1

    models: list[dict[str, Any]] = []
    for (provider, model_name), values in grouped.items():
        runs = len(values)
        success_rate = round(sum(1 for item in values if item.get("success")) / max(runs, 1), 3)
        avg_latency = round(sum(_safe_float(item.get("latency_s")) for item in values) / max(runs, 1), 3)
        avg_output_chars = round(sum(_safe_int(item.get("output_chars")) for item in values) / max(runs, 1))
        adherence = round(sum(_safe_float(item.get("format_adherence")) for item in values) / max(runs, 1), 3)
        grounding_coverage = round(
            sum(
                0.7 * (1.0 if item.get("context_injected") else 0.0)
                + 0.3 * _safe_ratio(_safe_int(item.get("used_chunks")), max_used_chunks, 0.0)
                for item in values
            )
            / max(runs, 1),
            3,
        )
        latency_score = min(1.0, _safe_ratio(min_latency, avg_latency, 0.0)) if avg_latency > 0 else 0.0
        use_case_fit = round((adherence * 0.5) + (grounding_coverage * 0.3) + (latency_score * 0.2), 3)
        models.append(
            {
                "id": f"{provider}-{_slugify(model_name)}",
                "provider": provider,
                "model": model_name,
                "family": _titleize_model_family(model_name),
                "quantization": _quantization_label(model_name),
                "latency": avg_latency,
                "outputChars": avg_output_chars,
                "adherence": adherence,
                "groundedness": grounding_coverage,
                "useCaseFit": use_case_fit,
                "runtimeBucket": _derive_runtime_bucket(provider, model_name),
                "runs": runs,
                "successRate": success_rate,
                "source": "phase7_model_comparison_log",
            }
        )

    models.sort(key=lambda item: (-_safe_float(item.get("useCaseFit")), _safe_float(item.get("latency")), str(item.get("model"))))
    for index, model in enumerate(models):
        model["profileTag"] = _profile_tag_for_model(
            rank=index,
            provider=str(model.get("provider") or ""),
            latency=_safe_float(model.get("latency")),
            model_name=str(model.get("model") or ""),
        )

    presets: list[dict[str, Any]] = []
    for (retrieval_strategy, prompt_profile, response_format), values in sorted(
        preset_groups.items(),
        key=lambda item: (-len(item[1]), item[0]),
    ):
        involved_models = []
        for item in values:
            model_name = str(item.get("model") or "").strip()
            if model_name and model_name not in involved_models:
                involved_models.append(model_name)
        presets.append(
            {
                "id": f"preset-{_slugify(f'{retrieval_strategy}-{prompt_profile}-{response_format}')}",
                "name": f"{retrieval_strategy} · {response_format}",
                "description": f"Observed comparison runs using prompt profile {prompt_profile} across {len(values)} candidate result(s).",
                "metrics": ["latency", "format_adherence", "output_chars"],
                "models": involved_models[:4],
            }
        )

    retrieval_observations: list[dict[str, Any]] = []
    for strategy, values in sorted(retrieval_groups.items(), key=lambda item: (-len(item[1]), item[0])):
        if not values:
            continue
        output_discipline = round(sum(_safe_float(item.get("format_adherence")) for item in values) / max(len(values), 1), 3)
        context_retention = round(
            sum(_safe_ratio(_safe_int(item.get("used_chunks")), _safe_int(item.get("used_chunks")) + _safe_int(item.get("dropped_chunks")), 1.0) for item in values)
            / max(len(values), 1),
            3,
        )
        composite = round((output_discipline + context_retention) / 2, 3)
        avg_latency = round(sum(_safe_float(item.get("latency_s")) for item in values) / max(len(values), 1), 3)
        retrieval_observations.append(
            {
                "strategy": strategy,
                "outputDiscipline": output_discipline,
                "contextRetention": context_retention,
                "composite": composite,
                "latency": avg_latency,
                "description": "Derived from recorded comparison runs. Composite blends response-format discipline with retained retrieved context.",
                "coverage": len(values),
            }
        )

    return models, presets, retrieval_observations, notes


def build_lab_benchmarks_payload(workspace_root: str | Path) -> dict[str, Any]:
    resolved_root = Path(workspace_root)
    models, presets, retrieval_observations, notes = _build_benchmark_models(resolved_root)
    recommended = models[0] if models else None
    best_groundedness = round(max((_safe_float(item.get("groundedness")) for item in models), default=0.0) * 100)
    fastest_latency = min((_safe_float(item.get("latency")) for item in models), default=0.0)
    return {
        "ok": True,
        "meta": _build_meta(
            source="derived",
            updated_at=_now_iso(),
            notes=notes or ["Benchmarks are derived from the recorded model comparison log and do not invent missing runs."],
        ),
        "summary": {
            "modelCount": len(models),
            "recommendedModel": recommended.get("family") if isinstance(recommended, dict) else None,
            "bestGroundedness": best_groundedness,
            "fastestLatency": round(fastest_latency, 2) if fastest_latency else 0.0,
        },
        "models": models,
        "presets": presets,
        "retrievalObservations": retrieval_observations,
    }


def build_lab_evals_payload(workspace_root: str | Path) -> dict[str, Any]:
    resolved_root = Path(workspace_root)
    eval_entries = load_eval_runs(get_phase8_eval_db_path(resolved_root), limit=250)
    eval_summary = summarize_eval_runs(eval_entries)
    diagnosis = build_eval_diagnosis(eval_entries)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in eval_entries:
        grouped[str(entry.get("suite_name") or "eval")].append(entry)

    suites: list[dict[str, Any]] = []
    for suite_name, entries in grouped.items():
        ordered_entries = sorted(
            entries,
            key=lambda item: _parse_timestamp(item.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        total = len(entries)
        pass_count = sum(1 for item in entries if str(item.get("status") or "").upper() == "PASS")
        warn_count = sum(1 for item in entries if str(item.get("status") or "").upper() == "WARN")
        fail_count = sum(1 for item in entries if str(item.get("status") or "").upper() == "FAIL")
        review_count = sum(1 for item in entries if bool(item.get("needs_review")))
        suites.append(
            {
                "name": suite_name,
                "total": total,
                "pass": pass_count,
                "warn": warn_count,
                "fail": fail_count,
                "needsReview": review_count,
                "lastRun": _normalize_timestamp(ordered_entries[0].get("created_at")) if ordered_entries else None,
            }
        )

    suites.sort(key=lambda item: (-_safe_int(item.get("total")), str(item.get("name"))))
    cases: list[dict[str, Any]] = []
    for entry in eval_entries[:50]:
        max_score = _safe_float(entry.get("max_score"), 0.0)
        score = _safe_float(entry.get("score"), 0.0)
        score_ratio = round(score / max_score, 3) if max_score > 0 else 0.0
        reasons = entry.get("reasons") if isinstance(entry.get("reasons"), list) else []
        cases.append(
            {
                "id": f"eval-{entry.get('id')}",
                "task": str(entry.get("task_type") or entry.get("case_name") or "unknown"),
                "suite": str(entry.get("suite_name") or "eval"),
                "verdict": str(entry.get("status") or "UNKNOWN").upper(),
                "score": score_ratio,
                "needsReview": bool(entry.get("needs_review")),
                "model": str(entry.get("model") or entry.get("provider") or "unknown"),
                "latency": round(_safe_float(entry.get("latency_s")), 2),
                "timestamp": _normalize_timestamp(entry.get("created_at")),
                "errorDetail": "; ".join(str(item) for item in reasons[:3]) if reasons else None,
            }
        )

    totals = {
        "total": len(eval_entries),
        "pass": sum(1 for item in eval_entries if str(item.get("status") or "").upper() == "PASS"),
        "warn": sum(1 for item in eval_entries if str(item.get("status") or "").upper() == "WARN"),
        "fail": sum(1 for item in eval_entries if str(item.get("status") or "").upper() == "FAIL"),
        "review": sum(1 for item in eval_entries if bool(item.get("needs_review"))),
    }

    return {
        "ok": True,
        "meta": _build_meta(
            source="live",
            updated_at=_normalize_timestamp(eval_summary.get("latest_created_at")) or _now_iso(),
            notes=["Evals are loaded directly from the persisted phase8 SQLite store."],
        ),
        "passRate": round(_safe_float(eval_summary.get("pass_rate")) * 100),
        "totals": totals,
        "suites": suites,
        "cases": cases,
        "diagnosis": {
            "topFailureReasons": diagnosis.get("top_failure_reasons") or [],
            "adaptationCandidates": diagnosis.get("adaptation_candidates") or [],
            "nextEvalPriorities": (diagnosis.get("decision_summary") or {}).get("next_eval_priorities") or [],
            "globalRecommendation": (diagnosis.get("decision_summary") or {}).get("global_recommendation"),
        },
    }


def _parse_export_created_at(export_id: str | None, metadata_path: Path) -> str:
    normalized = str(export_id or "").strip()
    match = re.match(r"deckexp_(\d{8})_(\d{6})_", normalized)
    if match:
        raw = f"{match.group(1)}{match.group(2)}"
        try:
            return datetime.strptime(raw, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    return datetime.fromtimestamp(metadata_path.stat().st_mtime, tz=timezone.utc).isoformat()


def _classify_artifact_from_path(path: Path) -> tuple[str, str, str]:
    name = path.name.lower()
    if "benchmark" in name:
        return "benchmark", "Benchmarks", "Benchmark artifact derived from recorded export assets."
    if "eval" in name or "review" in name:
        return "eval", "Evals", "Eval or review artifact derived from recorded export assets."
    if "embedding" in name:
        return "embedding_experiment", "Retrieval", "Embedding experiment artifact captured in the repository."
    if "ocr" in name:
        return "ocr_diagnostic", "Diagnostics", "OCR diagnostic artifact captured in the repository."
    return "report", "Diagnostics", "Supporting artifact captured in the repository."


def _build_artifact_entries(workspace_root: Path) -> list[dict[str, Any]]:
    artifact_root = get_artifact_root(workspace_root) / "presentation_exports"
    entries: list[dict[str, Any]] = []
    if not artifact_root.exists() or not artifact_root.is_dir():
        return entries

    seen_paths: set[str] = set()
    for metadata_path in sorted(artifact_root.glob("**/metadata.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        payload = _read_json_file(metadata_path, {})
        if not isinstance(payload, dict):
            continue
        export_id = str(payload.get("export_id") or metadata_path.parent.name).strip() or metadata_path.parent.name
        export_kind = str(payload.get("export_kind") or payload.get("requested_export_kind") or "report").strip()
        artifact_type, category = ARTIFACT_TYPE_BY_EXPORT_KIND.get(export_kind, ("report", "Workflow Decks"))
        pptx_path_raw = str(payload.get("local_pptx_path") or "").strip()
        pptx_path = Path(pptx_path_raw) if pptx_path_raw else None
        size_bytes = None
        if pptx_path is not None and pptx_path.exists() and pptx_path.is_file():
            size_bytes = pptx_path.stat().st_size
            seen_paths.add(str(pptx_path.resolve(strict=False)))
        entries.append(
            {
                "id": export_id,
                "name": str(payload.get("export_kind_label") or export_kind.replace("_", " ").title()).strip() or export_id,
                "type": artifact_type,
                "category": category,
                "version": export_id.split("_")[-1][:8],
                "createdAt": _parse_export_created_at(export_id, metadata_path),
                "size": _format_size_label(size_bytes),
                "status": "ready" if str(payload.get("status") or "completed").strip().lower() == "completed" else "error",
                "description": f"{str(payload.get('export_kind_label') or export_kind).replace('_', ' ').strip()} PowerPoint export.",
                "artifactPath": str(pptx_path) if pptx_path is not None else None,
            }
        )

    for candidate in sorted(artifact_root.glob("**/*"), key=lambda item: item.stat().st_mtime, reverse=True):
        if not candidate.is_file():
            continue
        if candidate.name.startswith("."):
            continue
        if candidate.suffix.lower() not in {".json", ".pptx"}:
            continue
        resolved_path = str(candidate.resolve(strict=False))
        if resolved_path in seen_paths:
            continue
        if candidate.name == "metadata.json":
            continue
        artifact_type, category, description = _classify_artifact_from_path(candidate)
        entries.append(
            {
                "id": _slugify(candidate.relative_to(artifact_root)),
                "name": candidate.stem.replace("_", " ").replace("-", " ").strip() or candidate.name,
                "type": artifact_type,
                "category": category,
                "version": datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc).strftime("v%Y%m%d"),
                "createdAt": datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc).isoformat(),
                "size": _format_size_label(candidate.stat().st_size),
                "status": "ready",
                "description": description,
                "artifactPath": str(candidate),
            }
        )
        seen_paths.add(resolved_path)

    entries.sort(
        key=lambda item: _parse_timestamp(item.get("createdAt")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return entries[:40]


def build_lab_artifacts_payload(workspace_root: str | Path) -> dict[str, Any]:
    resolved_root = Path(workspace_root)
    (
        runtime_snapshot,
        runtime_controls_state,
        _,
        runtime_summary,
        document_agent_entries,
        _,
        documents,
        _,
    ) = _build_runtime_snapshot(resolved_root)
    profile = runtime_controls_state.get("profile") if isinstance(runtime_controls_state.get("profile"), dict) else {}
    doc_processing = profile.get("docProcessing") if isinstance(profile.get("docProcessing"), dict) else {}
    artifacts = _build_artifact_entries(resolved_root)
    chat_sessions = load_lab_chat_sessions(get_lab_chat_sessions_path(resolved_root))
    workflow_runs = load_lab_workflow_runs(get_lab_workflow_runs_path(resolved_root))
    total_chunks = sum(_safe_int(item.get("chunk_count")) for item in documents)
    diagnostics = [
        {
            "label": "OCR Quality",
            "detail": f"OCR backend: {doc_processing.get('ocrBackend') or 'not configured'}",
            "status": f"{round(_safe_float(runtime_summary.get('ocr_involved_runs')))} OCR-involved runtime traces" if _safe_float(runtime_summary.get("ocr_involved_runs")) > 0 else "No OCR-involved runtime traces recorded",
            "health": "healthy" if _safe_float(runtime_summary.get("ocr_involved_runs")) > 0 or documents else "warning",
        },
        {
            "label": "PDF Extraction",
            "detail": f"Extraction mode: {doc_processing.get('pdfExtractionMode') or 'default'}",
            "status": f"{len(documents)} indexed document(s) currently visible in the RAG store",
            "health": "healthy" if documents else "warning",
        },
        {
            "label": "VLM Processing",
            "detail": "Vision-enhanced parsing posture exposed by runtime controls.",
            "status": "Enabled" if bool(doc_processing.get("vlmEnhancement")) else "Standby",
            "health": "healthy" if bool(doc_processing.get("vlmEnhancement")) else "neutral",
        },
        {
            "label": "Embedding Store",
            "detail": f"{runtime_snapshot.get('embeddingModel')} via {runtime_snapshot.get('embeddingProvider')}",
            "status": f"{total_chunks:,} chunk(s) across {len(documents)} current document(s)",
            "health": "healthy" if total_chunks > 0 else "warning",
        },
        {
            "label": "AI LAB Chat Sessions",
            "detail": "Persisted session registry used by the live chat tab.",
            "status": f"{len(chat_sessions)} session(s) stored",
            "health": "healthy" if chat_sessions else "neutral",
        },
        {
            "label": "Workflow Run Registry",
            "detail": "Persisted execution runs written by Workflow Inspector.",
            "status": f"{len(workflow_runs)} run(s) stored",
            "health": "healthy" if workflow_runs else "neutral",
        },
    ]

    return {
        "ok": True,
        "meta": _build_meta(
            source="live",
            updated_at=_normalize_timestamp(runtime_controls_state.get("updated_at")) or _normalize_timestamp(runtime_summary.get("latest_timestamp")) or _now_iso(),
            notes=["Artifacts are backed by the actual artifact directory and the persisted AI LAB run/session registries."],
        ),
        "artifacts": artifacts,
        "summary": {
            "totalArtifacts": len(artifacts),
            "readyArtifacts": sum(1 for item in artifacts if str(item.get("status") or "") == "ready"),
            "errorArtifacts": sum(1 for item in artifacts if str(item.get("status") or "") == "error"),
        },
        "diagnostics": diagnostics,
    }


def _tool_status(active: bool, *, configured: bool = True) -> str:
    if not configured:
        return "not_configured"
    return "active" if active else "degraded"


def _map_action_status(raw_status: str) -> str:
    normalized = str(raw_status or "").strip().lower()
    if normalized in {"done", "closed", "approved", "resolved"}:
        return "done"
    if normalized in {"blocked", "pending_approval"}:
        return "blocked"
    if normalized in {"in_progress", "working", "assigned"}:
        return "in_progress"
    return "open"


def _derive_action_priority(action: dict[str, Any]) -> str:
    due_date = str(action.get("due_date") or "").strip()
    status = str(action.get("status") or "").strip().lower()
    if bool(action.get("needs_review")) or status in {"blocked", "pending_approval"}:
        return "high"
    if due_date:
        return "medium"
    return "low"


def _readiness_status(*, available: bool, configured: bool = True) -> str:
    if not configured:
        return "degraded"
    return "ready" if available else "degraded"


def build_lab_evidenceops_payload(workspace_root: str | Path) -> dict[str, Any]:
    resolved_root = Path(workspace_root)
    settings = get_evidenceops_external_settings()
    repository_root = _resolve_evidenceops_root(resolved_root)
    repository_documents = list_evidenceops_repository_documents(repository_root) if repository_root.exists() else []
    repository_summary = summarize_evidenceops_repository_documents(repository_documents)
    drift_summary = _compute_repository_drift(resolved_root, repository_root) or {}
    action_entries = load_evidenceops_actions(get_phase95_evidenceops_action_store_path(resolved_root))
    action_summary = summarize_evidenceops_actions(action_entries)
    worklog_entries = load_evidenceops_worklog(get_phase95_evidenceops_worklog_path(resolved_root))
    worklog_summary = summarize_evidenceops_worklog(worklog_entries)
    chat_sessions = load_lab_chat_sessions(get_lab_chat_sessions_path(resolved_root))
    workflow_runs = load_lab_workflow_runs(get_lab_workflow_runs_path(resolved_root))
    last_action_timestamp = _normalize_timestamp(action_summary.get("latest_created_at"))
    now_ts = _now_iso()

    tools = [
        {
            "name": "local_repository_scan",
            "description": "Enumerates EvidenceOps corpus files from the configured repository root.",
            "status": _tool_status(repository_root.exists() and repository_root.is_dir()),
            "lastCall": now_ts,
        },
        {
            "name": "local_repository_search",
            "description": "Searches repository documents by path, title and category over the live corpus root.",
            "status": _tool_status(repository_root.exists() and repository_documents != []),
            "lastCall": now_ts,
        },
        {
            "name": "action_store",
            "description": "Reads persisted EvidenceOps actions from the local SQLite store.",
            "status": _tool_status(bool(action_entries)),
            "lastCall": last_action_timestamp,
        },
        {
            "name": "worklog",
            "description": "Reads the EvidenceOps worklog trail when present.",
            "status": _tool_status(bool(worklog_entries or chat_sessions or workflow_runs)),
            "lastCall": _normalize_timestamp(worklog_summary.get("latest_timestamp")) or (workflow_runs[0].get("updated_at") if workflow_runs else None) or (chat_sessions[0].get("updated_at") if chat_sessions else None),
        },
        {
            "name": "lab_chat_sessions",
            "description": "Reads persisted AI LAB chat sessions and diagnostics.",
            "status": _tool_status(bool(chat_sessions)),
            "lastCall": _normalize_timestamp(chat_sessions[0].get("updated_at")) if chat_sessions else None,
        },
        {
            "name": "lab_workflow_runs",
            "description": "Reads persisted AI LAB workflow inspector runs.",
            "status": _tool_status(bool(workflow_runs)),
            "lastCall": _normalize_timestamp(workflow_runs[0].get("updated_at")) if workflow_runs else None,
        },
        {
            "name": "nextcloud_webdav",
            "description": "External repository connector surfaced from current EvidenceOps settings.",
            "status": _tool_status(
                settings.external_sync_enabled and bool(settings.nextcloud.base_url and settings.nextcloud.username and settings.nextcloud.app_password),
                configured=bool(settings.nextcloud.base_url and settings.nextcloud.username and settings.nextcloud.app_password),
            ),
            "lastCall": None,
        },
    ]

    actions = [
        {
            "id": f"action-{item.get('id')}",
            "title": str(item.get("description") or "EvidenceOps action").strip(),
            "status": _map_action_status(str(item.get("status") or "")),
            "owner": str(item.get("owner") or "Unassigned").strip() or "Unassigned",
            "dueDate": str(item.get("due_date") or "—").strip() or "—",
            "target": _task_label(str(item.get("tool_used") or item.get("review_type") or item.get("task_type") or "evidenceops")),
            "priority": _derive_action_priority(item),
            "rawStatus": str(item.get("status") or ""),
            "evidence": str(item.get("evidence") or "").strip() or None,
            "sourceCount": _safe_int(item.get("source_count")),
        }
        for item in action_entries[:25]
    ]

    operations: list[dict[str, Any]] = []
    if worklog_entries:
        for index, entry in enumerate(worklog_entries[:20]):
            operations.append(
                {
                    "id": f"worklog-{index}",
                    "operation": str(entry.get("review_type") or entry.get("task_type") or "worklog_entry"),
                    "tool": str(entry.get("tool_used") or "evidenceops"),
                    "status": "error" if str(entry.get("status") or "").strip().lower() in {"error", "failed"} else ("warning" if bool(entry.get("needs_review")) else "success"),
                    "timestamp": _normalize_timestamp(entry.get("timestamp")) or now_ts,
                    "durationMs": 0,
                    "detail": f"{_safe_int(entry.get('source_count'))} source(s) · {len(entry.get('findings') or []) if isinstance(entry.get('findings'), list) else 0} finding(s)",
                }
            )
    for session in chat_sessions[:8]:
        messages = session.get("messages") if isinstance(session.get("messages"), list) else []
        operations.append(
            {
                "id": f"chat-{session.get('session_id')}",
                "operation": "lab_chat_session",
                "tool": "lab_chat_sessions",
                "status": "warning" if str(session.get("last_error") or "").strip() else "success",
                "timestamp": _normalize_timestamp(session.get("updated_at")) or now_ts,
                "durationMs": int(round(_safe_float((session.get("runtime") if isinstance(session.get("runtime"), dict) else {}).get("latency_s")) * 1000)),
                "detail": f"{len(messages)} message(s) · {len(session.get('document_ids') if isinstance(session.get('document_ids'), list) else [])} document(s)",
            }
        )
    for run in workflow_runs[:8]:
        operations.append(
            {
                "id": f"workflow-{run.get('run_id')}",
                "operation": str(run.get("workflow_id") or run.get("task_id") or "workflow_inspector"),
                "tool": "lab_workflow_runs",
                "status": "error" if str(run.get("status") or "").strip().lower() in {"error", "failed"} else ("warning" if bool(run.get("needs_review")) else "success"),
                "timestamp": _normalize_timestamp(run.get("updated_at") or run.get("created_at")) or now_ts,
                "durationMs": int(round(_safe_float(run.get("latency_s")) * 1000)),
                "detail": f"{_safe_int(run.get('source_count'))} source(s) · {str(run.get('provider') or 'provider')} / {str(run.get('model') or 'model')}",
            }
        )
    if not operations:
        operations = [
            {
                "id": "repository-scan",
                "operation": "repository_scan",
                "tool": "local_repository_scan",
                "status": "success" if repository_documents else "warning",
                "timestamp": now_ts,
                "durationMs": 0,
                "detail": f"{repository_summary.get('total_documents', 0)} document(s) visible in the active repository root.",
            },
            {
                "id": "drift-check",
                "operation": "drift_check",
                "tool": "repository_snapshot",
                "status": "warning" if _safe_int(drift_summary.get("changed_documents_count")) or _safe_int(drift_summary.get("removed_documents_count")) else "success",
                "timestamp": now_ts,
                "durationMs": 0,
                "detail": (
                    f"New {drift_summary.get('new_documents_count', 0)} · "
                    f"Changed {drift_summary.get('changed_documents_count', 0)} · "
                    f"Removed {drift_summary.get('removed_documents_count', 0)}"
                ),
            },
        ]
    operations.sort(key=lambda item: _parse_timestamp(item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    operations = operations[:20]

    telemetry = [
        {
            "event": str(item.get("operation") or "event"),
            "tool": str(item.get("tool") or "evidenceops"),
            "status": "ok" if str(item.get("status") or "") == "success" else ("warning" if str(item.get("status") or "") == "warning" else "skipped"),
            "latency": _format_duration_label(_safe_float(item.get("durationMs"), 0.0) / 1000) if _safe_int(item.get("durationMs")) > 0 else "derived",
            "ts": item.get("timestamp"),
        }
        for item in operations[:20]
    ]

    readiness = [
        {
            "target": "Local repository",
            "status": _readiness_status(available=repository_root.exists() and bool(repository_documents)),
            "detail": str(repository_root),
        },
        {
            "target": "Action store",
            "status": _readiness_status(available=bool(action_entries)),
            "detail": f"{action_summary.get('total_actions', 0)} persisted action(s)",
        },
        {
            "target": "Worklog",
            "status": _readiness_status(available=bool(worklog_entries or chat_sessions or workflow_runs)),
            "detail": f"{worklog_summary.get('total_runs', 0)} worklog run(s) · {len(chat_sessions)} chat session(s) · {len(workflow_runs)} workflow run(s)",
        },
        {
            "target": "Nextcloud sync",
            "status": _readiness_status(
                available=settings.external_sync_enabled and bool(settings.nextcloud.base_url and settings.nextcloud.username and settings.nextcloud.app_password),
                configured=bool(settings.nextcloud.base_url and settings.nextcloud.username and settings.nextcloud.app_password),
            ),
            "detail": settings.nextcloud.base_url or "Not configured",
        },
    ]

    notes = []
    if not worklog_entries and (chat_sessions or workflow_runs):
        notes.append("EvidenceOps operations are currently populated from the persisted AI LAB session/run registries plus repository and action-store state.")
    if not worklog_entries and not chat_sessions and not workflow_runs:
        notes.append("No persisted EvidenceOps worklog exists in this workspace yet, so operations and telemetry currently derive from repository and action-store state.")
    if not repository_documents:
        notes.append("The active EvidenceOps repository root is empty or unavailable.")

    updated_at = _normalize_timestamp(worklog_summary.get("latest_timestamp"))
    if not updated_at and workflow_runs:
        updated_at = _normalize_timestamp(workflow_runs[0].get("updated_at"))
    if not updated_at and chat_sessions:
        updated_at = _normalize_timestamp(chat_sessions[0].get("updated_at"))
    if not updated_at:
        updated_at = last_action_timestamp or now_ts

    return {
        "ok": True,
        "meta": _build_meta(
            source="live" if (worklog_entries or chat_sessions or workflow_runs or action_entries or repository_documents) else "derived",
            updated_at=updated_at,
            notes=notes,
        ),
        "summary": {
            "toolsTotal": len(tools),
            "activeTools": sum(1 for item in tools if str(item.get("status") or "") in {"active", "connected"}),
            "openActions": sum(1 for item in actions if str(item.get("status") or "") != "done"),
            "operationsCount": len(operations),
            "lastSyncAt": last_action_timestamp or now_ts,
            "repositoryRoot": str(repository_root),
            "repositoryDocumentCount": _safe_int(repository_summary.get("total_documents")),
        },
        "tools": tools,
        "actions": actions,
        "operations": operations,
        "telemetry": telemetry,
        "readiness": readiness,
    }


def build_lab_evidenceops_search_payload(workspace_root: str | Path, *, query: str) -> dict[str, Any]:
    resolved_root = Path(workspace_root)
    repository_root = _resolve_evidenceops_root(resolved_root)
    normalized_query = str(query or "").strip()
    results = []
    if normalized_query and repository_root.exists():
        for item in list_evidenceops_repository_documents(repository_root, query=normalized_query, limit=20):
            results.append(
                {
                    "documentId": item.get("document_id"),
                    "title": item.get("title"),
                    "category": item.get("category"),
                    "relativePath": item.get("relative_path"),
                    "suffix": item.get("suffix"),
                    "sizeKb": round(_safe_int(item.get("size_bytes")) / 1024, 2),
                    "matchScore": round(_safe_float(item.get("match_score")), 3) if item.get("match_score") is not None else None,
                    "modifiedAt": datetime.fromtimestamp(_safe_int(item.get("modified_at")), tz=timezone.utc).isoformat() if _safe_int(item.get("modified_at")) > 0 else None,
                }
            )
    return {
        "ok": True,
        "meta": _build_meta(source="live", updated_at=_now_iso()),
        "query": normalized_query,
        "repositoryRoot": str(repository_root),
        "results": results,
    }
