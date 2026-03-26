import time
from dataclasses import replace

import streamlit as st
from src.config import get_ollama_settings, get_rag_settings
from src.evidence_cv.config import build_evidence_config_from_rag_settings
from src.prompt_profiles import build_prompt_messages, get_prompt_profiles
from src.providers.registry import build_provider_registry
from src.rag.loaders import load_document
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
from src.storage.chat_history import clear_chat_history, load_chat_history, save_chat_history
from src.storage.rag_store import clear_rag_store, load_rag_store, save_rag_store
from src.services.document_context import build_structured_document_context
from src.services.rag_state import clear_rag_state, get_rag_index, initialize_rag_state, set_rag_index
from src.structured.envelope import StructuredResult, TaskExecutionRequest
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
from src.ui.sidebar import render_chat_sidebar, render_runtime_sidebar_panel
from src.ui.structured_outputs import render_structured_result


settings = get_ollama_settings()
rag_settings = get_rag_settings()
evidence_config = build_evidence_config_from_rag_settings(rag_settings)
provider_registry = build_provider_registry()
prompt_profiles = get_prompt_profiles()
structured_task_registry = build_structured_task_registry()
embedding_provider = provider_registry["ollama"]["instance"]
embedding_model_options = embedding_provider.list_available_embedding_models()

STRUCTURED_RESULT_STATE_KEY = "phase5_structured_result"
STRUCTURED_RENDER_MODE_STATE_KEY = "phase5_structured_render_mode"
CHAT_DOCUMENT_SELECTION_STATE_KEY = "phase5_chat_document_ids"
STRUCTURED_DOCUMENT_SELECTION_STATE_KEY = "phase5_structured_document_ids"

AUTO_CONTEXT_WINDOW_CAP_BY_PROVIDER = {
    "ollama": 256000,
    "openai": 128000,
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

    if task_type in coverage_first_tasks:
        if has_meaningful_query and task_type == "code_analysis":
            return "retrieval", "Estratégia automática: retrieval, porque há instrução textual específica para análise de código."
        return "document_scan", "Estratégia automática: document_scan, porque esta task prioriza cobertura estrutural do documento."

    if task_type in mixed_tasks:
        if has_meaningful_query:
            return "retrieval", "Estratégia automática: retrieval, porque há texto suficiente para orientar a busca dos trechos mais relevantes."
        return "document_scan", "Estratégia automática: document_scan, porque não há consulta forte no campo de texto e a task precisa cobrir melhor o documento."

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
    }

    return labels_by_task.get(task_type, {}).get(step, step.replace("_", " ").capitalize())


def _extract_last_assistant_metadata(messages: list[dict[str, object]]) -> dict[str, object]:
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        metadata = message.get("metadata")
        if isinstance(metadata, dict):
            return metadata
    return {}


def _summarize_provider_path(provider: str, provider_label: str, ollama_base_url: str | None) -> tuple[str, str]:
    if provider == "ollama":
        base_url = str(ollama_base_url or "").strip()
        route = f"{provider_label} -> {base_url or 'endpoint não configurado'}"
        if any(token in base_url.lower() for token in ["localhost", "127.0.0.1"]):
            dependency = "Dependência local: app + servidor Ollama rodam na sua máquina."
        else:
            dependency = "Dependência local parcial: app local, inferência via endpoint remoto compatível com Ollama."
        return route, dependency
    if provider == "openai":
        return f"{provider_label} -> API cloud direta", "Dependência local: app local; inferência remota."
    return provider_label, "Dependência local não classificada."


def _build_document_runtime_rows(
    document_ids: list[str],
    document_preview_map: dict[str, dict[str, object]],
    *,
    default_vl_model: str,
    default_ocr_backend: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for document_id in document_ids:
        preview = document_preview_map.get(str(document_id)) or {}
        document = preview.get("document") if isinstance(preview, dict) else {}
        if not isinstance(document, dict):
            continue
        loader_metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
        vl_runtime = loader_metadata.get("vl_runtime") if isinstance(loader_metadata.get("vl_runtime"), dict) else {}
        rows.append(
            {
                "documento": document.get("name"),
                "tipo": document.get("file_type"),
                "chunks": preview.get("chunks_count"),
                "extração_pdf": loader_metadata.get("strategy_label") or loader_metadata.get("strategy"),
                "source_type": loader_metadata.get("source_type"),
                "ocr_backend": loader_metadata.get("ocr_backend") or default_ocr_backend,
                "evidence_pipeline": bool(loader_metadata.get("evidence_pipeline_used")),
                "vl_model": vl_runtime.get("model") or default_vl_model,
            }
        )
    return rows


def _build_runtime_snapshot(
    *,
    selected_provider: str,
    selected_provider_label: str,
    selected_model: str,
    selected_embedding_model: str,
    selected_pdf_extraction_mode: str,
    chat_selected_document_ids: list[str],
    structured_selected_document_ids: list[str],
    selected_structured_task: str,
    messages: list[dict[str, object]],
    structured_result: StructuredResult | None,
    structured_task_registry,
    document_preview_map: dict[str, dict[str, object]],
    indexed_documents_count: int,
    ollama_base_url: str,
    default_vl_model: str,
    default_ocr_backend: str,
) -> dict[str, object]:
    provider_path, local_dependency = _summarize_provider_path(
        selected_provider,
        selected_provider_label,
        ollama_base_url,
    )
    last_chat_metadata = _extract_last_assistant_metadata(messages)
    structured_metadata = structured_result.execution_metadata if structured_result and isinstance(structured_result.execution_metadata, dict) else {}
    structured_telemetry = structured_metadata.get("telemetry") if isinstance(structured_metadata.get("telemetry"), dict) else {}
    structured_timings = structured_telemetry.get("timings_s") if isinstance(structured_telemetry.get("timings_s"), dict) else {}
    last_pre_model_prep_s = None
    if isinstance(structured_timings, dict):
        component_values = [
            structured_timings.get("document_load_s"),
            structured_timings.get("sanitize_s"),
            structured_timings.get("context_build_s"),
        ]
        numeric_values = [float(value) for value in component_values if isinstance(value, (int, float))]
        if numeric_values:
            last_pre_model_prep_s = round(sum(numeric_values), 4)

    task_model_map = {
        task_name: (task_definition.default_model or selected_model)
        for task_name, task_definition in structured_task_registry.list_tasks().items()
    }

    return {
        "provider_path": provider_path,
        "local_dependency": local_dependency,
        "chat": {
            "provider": last_chat_metadata.get("provider") or selected_provider,
            "model": last_chat_metadata.get("model") or selected_model,
            "embedding_model": selected_embedding_model,
            "selected_documents": len(chat_selected_document_ids),
            "retrieval_backend": last_chat_metadata.get("vector_backend_used"),
            "last_total_s": last_chat_metadata.get("latency_s"),
            "last_generation_s": last_chat_metadata.get("generation_latency_s"),
            "last_retrieval_s": last_chat_metadata.get("retrieval_latency_s"),
            "last_prompt_build_s": last_chat_metadata.get("prompt_build_latency_s"),
        },
        "structured": {
            "current_task": selected_structured_task,
            "provider": structured_metadata.get("provider") or selected_provider,
            "model": structured_metadata.get("model") or selected_model,
            "selected_documents": len(structured_selected_document_ids),
            "last_total_s": (structured_timings.get("total_s") if isinstance(structured_timings, dict) else None),
            "last_provider_s": (structured_timings.get("provider_total_s") if isinstance(structured_timings, dict) else None),
            "last_pre_model_prep_s": last_pre_model_prep_s,
            "last_document_load_s": (structured_timings.get("document_load_s") if isinstance(structured_timings, dict) else None),
            "last_sanitize_s": (structured_timings.get("sanitize_s") if isinstance(structured_timings, dict) else None),
            "last_context_s": (structured_timings.get("context_build_s") if isinstance(structured_timings, dict) else None),
            "last_parsing_s": (structured_timings.get("parsing_s") if isinstance(structured_timings, dict) else None),
            "task_model_map": task_model_map,
        },
        "documents": {
            "pdf_extraction_mode": selected_pdf_extraction_mode,
            "ocr_backend_default": default_ocr_backend,
            "vl_model_default": default_vl_model,
            "indexed_documents": indexed_documents_count,
            "chat_selected_docs": _build_document_runtime_rows(
                chat_selected_document_ids,
                document_preview_map,
                default_vl_model=default_vl_model,
                default_ocr_backend=default_ocr_backend,
            ),
            "structured_selected_docs": _build_document_runtime_rows(
                structured_selected_document_ids,
                document_preview_map,
                default_vl_model=default_vl_model,
                default_ocr_backend=default_ocr_backend,
            ),
        },
    }

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

messages = get_chat_messages()
last_latency = get_last_latency()
rag_index = get_rag_index()
indexed_documents_preview = get_indexed_documents(rag_index, rag_settings)
indexed_chunks_preview = len(rag_index.get("chunks", [])) if isinstance(rag_index, dict) else 0
vector_backend_status_preview = inspect_vector_backend_status(rag_index, rag_settings)

provider_options = {
    provider_key: provider_data["label"]
    for provider_key, provider_data in provider_registry.items()
}
models_by_provider = {
    provider_key: provider_data["instance"].list_available_models()
    for provider_key, provider_data in provider_registry.items()
}
default_model_by_provider = {
    "ollama": settings.default_model,
    "openai": provider_registry["openai"]["instance"].settings.model if "openai" in provider_registry else "",
}
provider_details = {
    provider_key: provider_data.get("detail", "")
    for provider_key, provider_data in provider_registry.items()
}
default_context_window_by_provider = {
    "ollama": settings.default_context_window,
    "openai": provider_registry["openai"]["instance"].settings.default_context_window if "openai" in provider_registry else 128000,
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
    selected_embedding_model,
    selected_embedding_context_window,
    selected_pdf_extraction_mode,
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
    default_pdf_extraction_mode=normalize_pdf_extraction_mode(rag_settings.pdf_extraction_mode),
    embedding_model_options=embedding_model_options,
    default_embedding_model=rag_settings.embedding_model,
    default_embedding_context_window=rag_settings.embedding_context_window,
    indexed_documents_count=len(indexed_documents_preview),
    indexed_chunks_count=indexed_chunks_preview,
    provider_details=provider_details,
    history_filename=settings.history_path.name,
    messages_count=len(messages),
    last_latency=last_latency,
)

effective_rag_settings = replace(
    rag_settings,
    embedding_model=selected_embedding_model,
    embedding_context_window=selected_embedding_context_window,
    chunk_size=rag_chunk_size,
    chunk_overlap=min(rag_chunk_overlap, rag_chunk_size // 2),
    top_k=rag_top_k,
    pdf_extraction_mode=normalize_pdf_extraction_mode(selected_pdf_extraction_mode),
)

selected_provider_instance = provider_registry[selected_provider]["instance"]
selected_provider_label = provider_registry[selected_provider]["label"]
selected_prompt_profile_label = prompt_profiles[selected_prompt_profile]["label"]
selected_file_types_count = 0
estimated_rag_context_chars = effective_rag_settings.chunk_size * max(effective_rag_settings.top_k, 1)
rag_context_budget_chars = estimate_rag_context_budget_chars(context_window, effective_rag_settings)
context_usage_ratio = estimated_rag_context_chars / max(rag_context_budget_chars, 1)

if clear_requested:
    clear_chat_state()
    clear_chat_history(settings.history_path)
    st.rerun()

st.write(f"# {settings.project_name}")
st.caption(
    f"Provider: `{selected_provider}` · Modelo: `{selected_model}` · Perfil: `{selected_prompt_profile}` · Temperatura: `{temperature:.1f}` · Contexto ({context_window_mode}): `{context_window}`"
)
st.caption(
    f"Embedding: {effective_rag_settings.embedding_model} · embedding_num_ctx={effective_rag_settings.embedding_context_window} · truncate={effective_rag_settings.embedding_truncate}"
)
st.caption(
    f"RAG de teste: chunk_size={effective_rag_settings.chunk_size} · overlap={effective_rag_settings.chunk_overlap} · top_k={effective_rag_settings.top_k} · rerank_pool={effective_rag_settings.rerank_pool_size}"
)
st.caption(f"Extração PDF nesta execução: {describe_pdf_extraction_mode(effective_rag_settings.pdf_extraction_mode)}")
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

if selected_provider == "ollama" and hasattr(selected_provider_instance, "inspect_context_window"):
    with st.expander("Validação de contexto do Ollama", expanded=False):
        context_validation = selected_provider_instance.inspect_context_window(
            model=selected_model,
            requested_context_window=context_window,
        )
        st.write(context_validation)
        st.caption(
            "Esta validação combina rota nativa `/api/chat`, leitura de `/api/show` e `ollama ps`. "
            "Use `ollama ps` apenas como sinal auxiliar, não como prova isolada."
        )
    with st.expander("Validação de contexto do embedding (Ollama)", expanded=False):
        embedding_context_validation = embedding_provider.inspect_embedding_context_window(
            model=effective_rag_settings.embedding_model,
            requested_context_window=effective_rag_settings.embedding_context_window,
        )
        st.write(embedding_context_validation)
        st.caption(
            "O app envia `options.num_ctx` ao endpoint nativo `/api/embed`. Trate isso como controle operacional do pipeline de embedding; a aplicação efetiva ainda depende do modelo e do runtime."
        )

st.divider()
documents_tab, chat_tab, structured_tab = st.tabs(["📚 Documentos", "💬 Chat com RAG", "🧱 Documento estruturado"])

with documents_tab:
    st.caption("1. Carga, indexação e manutenção da base documental compartilhada entre Chat com RAG e Documento estruturado.")
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
            st.error(f"Erro ao indexar documento: {error}")

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
    st.caption("2. Converse com o RAG usando um ou mais documentos do repositório já indexado na etapa anterior.")
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

    st.caption("Modo conversacional com RAG. Use para perguntas abertas, exploração e follow-up sobre os documentos selecionados.")
    for mensagem in messages:
        render_chat_message(mensagem)

    texto_usuario = st.chat_input("Digite sua mensagem")

    if texto_usuario:
        chat_total_started_at = time.perf_counter()
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
        prompt_context_details = {
            "budget_chars": rag_context_budget_chars,
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

        if rag_index and chat_selected_document_ids and embedding_compatibility.get("compatible", True):
            try:
                retrieval_started_at = time.perf_counter()
                retrieval_details = retrieve_relevant_chunks_detailed(
                    query=texto_usuario,
                    rag_index=rag_index,
                    settings=effective_rag_settings,
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
            except Exception as error:
                st.warning(f"Não foi possível recuperar contexto do documento. A resposta seguirá sem RAG. Detalhes: {error}")
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
                    settings=effective_rag_settings,
                )
                prompt_build_latency = time.perf_counter() - prompt_build_started_at
                generation_started_at = time.perf_counter()
                stream = selected_provider_instance.stream_chat_completion(
                    messages=model_messages,
                    model=selected_model,
                    temperature=temperature,
                    context_window=chat_effective_context_window,
                )

                partes = []
                for token in selected_provider_instance.iter_stream_text(stream):
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
            except Exception as erro:
                set_last_latency(None)
                texto_resposta_ia = selected_provider_instance.format_error(selected_model, erro)
                placeholder.empty()
                st.error(texto_resposta_ia)

        assistant_metadata = {
            **user_metadata,
            "latency_s": round(get_last_latency(), 2) if get_last_latency() is not None else None,
            "retrieval_latency_s": round(retrieval_latency, 2) if retrieval_latency is not None else None,
            "prompt_build_latency_s": round(prompt_build_latency, 2) if prompt_build_latency is not None else None,
            "generation_latency_s": round(generation_latency, 2) if generation_latency is not None else None,
            "retrieved_chunks_count": len(retrieved_chunks),
            "vector_backend_used": retrieval_backend_used,
            "vector_backend_message": retrieval_backend_message,
            "vector_backend_status": retrieval_vector_status,
            "filtered_chunks_available": filtered_chunks_available,
            "rag_chunk_size": effective_rag_settings.chunk_size,
            "rag_chunk_overlap": effective_rag_settings.chunk_overlap,
            "rag_top_k": effective_rag_settings.top_k,
            "debug_retrieval": debug_retrieval,
            "rerank_strategy": retrieval_rerank_strategy,
            "retrieval_candidate_pool_size": retrieval_candidate_pool_size,
            "prompt_context": {
                "budget_chars": prompt_context_details.get("budget_chars"),
                "used_chars": prompt_context_details.get("used_chars"),
                "used_chunks": prompt_context_details.get("used_chunks"),
                "dropped_chunks": prompt_context_details.get("dropped_chunks"),
                "truncated": prompt_context_details.get("truncated"),
            },
            "sources": build_source_metadata(prompt_context_details.get("context_chunks") or retrieved_chunks),
        }
        append_chat_message("assistant", texto_resposta_ia, metadata=assistant_metadata)
        save_chat_history(settings.history_path, get_chat_messages())


with structured_tab:
    st.caption("3. Gere saídas estruturadas usando um ou mais documentos do repertório já indexado na etapa 1.")
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
        "cv_analysis": "Analisa um currículo com base no documento selecionado. Melhor usar 1 CV por vez.",
        "code_analysis": "Analisa código ou texto técnico com foco em propósito, problemas e plano de refatoração.",
    }

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
                provider=selected_provider,
                model=selected_model,
                temperature=temperature,
                context_window=None if context_window_mode == "auto" else structured_context_window_cap,
                progress_callback=_structured_progress_callback,
                telemetry={"current_stage": "structured_request_initialized"},
            )
            structured_result = structured_service.execute_task(structured_request)
            if displayed_progress["value"] < 100:
                for next_progress in range(displayed_progress["value"] + 1, 101):
                    displayed_progress["value"] = next_progress
                    progress_placeholder.markdown(f"**{next_progress}%** · Finalizando")
                    progress_bar.progress(next_progress)
                    time.sleep(STRUCTURED_PROGRESS_FINALIZE_DELAY_S)
            progress_bar.progress(100)
            progress_placeholder.markdown("**100%** · Finalizado")
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

runtime_snapshot = _build_runtime_snapshot(
    selected_provider=selected_provider,
    selected_provider_label=selected_provider_label,
    selected_model=selected_model,
    selected_embedding_model=selected_embedding_model,
    selected_pdf_extraction_mode=selected_pdf_extraction_mode,
    chat_selected_document_ids=chat_selected_document_ids if 'chat_selected_document_ids' in locals() else [],
    structured_selected_document_ids=active_structured_document_ids if 'active_structured_document_ids' in locals() else [],
    selected_structured_task=selected_structured_task if 'selected_structured_task' in locals() else "",
    messages=get_chat_messages(),
    structured_result=structured_result if 'structured_result' in locals() else None,
    structured_task_registry=structured_task_registry,
    document_preview_map=document_preview_map,
    indexed_documents_count=len(indexed_documents),
    ollama_base_url=settings.base_url,
    default_vl_model=evidence_config.vl_model,
    default_ocr_backend=evidence_config.ocr_backend,
)
render_runtime_sidebar_panel(runtime_snapshot)