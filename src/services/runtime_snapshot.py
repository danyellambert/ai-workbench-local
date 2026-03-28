from __future__ import annotations

from typing import Any

from ..structured.envelope import StructuredResult


def extract_last_assistant_metadata(messages: list[dict[str, object]]) -> dict[str, object]:
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        metadata = message.get("metadata")
        if isinstance(metadata, dict):
            return metadata
    return {}


def summarize_provider_path(provider: str, provider_label: str, ollama_base_url: str | None) -> tuple[str, str]:
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
    if provider == "huggingface_local":
        return f"{provider_label} -> runtime local Transformers", "Dependência local: app + inferência local via ecossistema Hugging Face na sua máquina."
    return provider_label, "Dependência local não classificada."


def build_document_runtime_rows(
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
                "loader": loader_metadata.get("loader_strategy_label") or loader_metadata.get("loader_strategy_used"),
                "extração_pdf": loader_metadata.get("strategy_label") or loader_metadata.get("strategy"),
                "source_type": loader_metadata.get("source_type"),
                "ocr_backend": loader_metadata.get("ocr_backend") or default_ocr_backend,
                "evidence_pipeline": bool(loader_metadata.get("evidence_pipeline_used")),
                "vl_model": vl_runtime.get("model") or default_vl_model,
            }
        )
    return rows


def build_runtime_snapshot(
    *,
    selected_provider: str,
    selected_provider_label: str,
    selected_model: str,
    selected_embedding_provider: str,
    selected_embedding_model: str,
    selected_loader_strategy: str,
    selected_chunking_strategy: str,
    selected_retrieval_strategy: str,
    selected_pdf_extraction_mode: str,
    chat_selected_document_ids: list[str],
    structured_selected_document_ids: list[str],
    selected_structured_task: str,
    selected_structured_execution_strategy: str,
    messages: list[dict[str, object]],
    structured_result: StructuredResult | None,
    structured_task_registry: Any,
    document_preview_map: dict[str, dict[str, object]],
    indexed_documents_count: int,
    ollama_base_url: str,
    default_vl_model: str,
    default_ocr_backend: str,
) -> dict[str, object]:
    provider_path, local_dependency = summarize_provider_path(
        selected_provider,
        selected_provider_label,
        ollama_base_url,
    )
    last_chat_metadata = extract_last_assistant_metadata(messages)
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
            "embedding_provider": selected_embedding_provider,
            "embedding_model": selected_embedding_model,
            "selected_documents": len(chat_selected_document_ids),
            "retrieval_backend": last_chat_metadata.get("vector_backend_used"),
            "retrieval_strategy": last_chat_metadata.get("retrieval_strategy_used") or last_chat_metadata.get("retrieval_strategy_requested"),
            "retrieval_shadow_summary": last_chat_metadata.get("retrieval_shadow_summary"),
            "last_total_s": last_chat_metadata.get("latency_s"),
            "last_generation_s": last_chat_metadata.get("generation_latency_s"),
            "last_retrieval_s": last_chat_metadata.get("retrieval_latency_s"),
            "last_prompt_build_s": last_chat_metadata.get("prompt_build_latency_s"),
        },
        "structured": {
            "current_task": selected_structured_task,
            "execution_strategy": structured_metadata.get("execution_strategy_used") or selected_structured_execution_strategy,
            "provider": structured_metadata.get("provider") or selected_provider,
            "model": structured_metadata.get("model") or selected_model,
            "selected_documents": len(structured_selected_document_ids),
            "workflow_attempts": structured_metadata.get("workflow_attempts"),
            "workflow_context_strategies": structured_metadata.get("workflow_context_strategies"),
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
            "loader_strategy": selected_loader_strategy,
            "chunking_strategy": selected_chunking_strategy,
            "retrieval_strategy": selected_retrieval_strategy,
            "pdf_extraction_mode": selected_pdf_extraction_mode,
            "ocr_backend_default": default_ocr_backend,
            "vl_model_default": default_vl_model,
            "indexed_documents": indexed_documents_count,
            "chat_selected_docs": build_document_runtime_rows(
                chat_selected_document_ids,
                document_preview_map,
                default_vl_model=default_vl_model,
                default_ocr_backend=default_ocr_backend,
            ),
            "structured_selected_docs": build_document_runtime_rows(
                structured_selected_document_ids,
                document_preview_map,
                default_vl_model=default_vl_model,
                default_ocr_backend=default_ocr_backend,
            ),
        },
    }