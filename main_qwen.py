import time
from dataclasses import replace

import streamlit as st
from src.config import get_ollama_settings, get_rag_settings
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
from src.ui.chat import render_chat_message
from src.ui.sidebar import render_chat_sidebar
from src.ui.structured_outputs import render_structured_result


settings = get_ollama_settings()
rag_settings = get_rag_settings()
provider_registry = build_provider_registry()
prompt_profiles = get_prompt_profiles()
structured_task_registry = build_structured_task_registry()
embedding_provider = provider_registry["ollama"]["instance"]
embedding_model_options = embedding_provider.list_available_embedding_models()

STRUCTURED_RESULT_STATE_KEY = "phase5_structured_result"
STRUCTURED_RENDER_MODE_STATE_KEY = "phase5_structured_render_mode"
CHAT_DOCUMENT_SELECTION_STATE_KEY = "phase5_chat_document_ids"
STRUCTURED_DOCUMENT_SELECTION_STATE_KEY = "phase5_structured_document_ids"


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
    f"Provider: `{selected_provider}` · Modelo: `{selected_model}` · Perfil: `{selected_prompt_profile}` · Temperatura: `{temperature:.1f}` · Contexto: `{context_window}`"
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
            with st.spinner("Extraindo texto, criando chunks e gerando embeddings..."):
                loaded_documents = [load_document(uploaded_file, effective_rag_settings) for uploaded_file in selected_uploaded_files]
                base_rag_index = rag_index if embedding_compatibility.get("compatible", True) else None
                built_rag_index, sync_status = upsert_documents_in_rag_index(
                    documents=loaded_documents,
                    settings=effective_rag_settings,
                    embedding_provider=embedding_provider,
                    rag_index=base_rag_index,
                )
                set_rag_index(built_rag_index)
                save_rag_store(effective_rag_settings.store_path, built_rag_index)
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
        st.chat_message("user").write(texto_usuario)
        user_metadata = {
            "provider": selected_provider,
            "provider_label": selected_provider_label,
            "model": selected_model,
            "prompt_profile": selected_prompt_profile,
            "prompt_profile_label": selected_prompt_profile_label,
            "temperature": round(temperature, 1),
            "context_window": context_window,
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
                inicio = time.perf_counter()
                model_messages, prompt_context_details = inject_rag_context(
                    build_prompt_messages(selected_prompt_profile, get_chat_messages()),
                    retrieved_chunks,
                    context_window=context_window,
                    settings=effective_rag_settings,
                )
                stream = selected_provider_instance.stream_chat_completion(
                    messages=model_messages,
                    model=selected_model,
                    temperature=temperature,
                    context_window=context_window,
                )

                partes = []
                for token in selected_provider_instance.iter_stream_text(stream):
                    partes.append(token)
                    placeholder.markdown("".join(partes) + "▌")

                texto_resposta_ia = "".join(partes).strip() or "A resposta veio vazia."
                placeholder.markdown(texto_resposta_ia)

                latencia = time.perf_counter() - inicio
                set_last_latency(latencia)
                st.caption(f"Resposta em {latencia:.2f}s")

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
                                "provider": selected_provider,
                                "model": selected_model,
                                "context_window": context_window,
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

    recommended_strategy = "document_scan" if selected_structured_task in {"cv_analysis", "extraction", "checklist", "code_analysis"} else "retrieval"
    strategy_options = ["document_scan", "retrieval"]
    if structured_use_documents:
        structured_context_strategy = st.radio(
            "Estratégia de contexto",
            options=strategy_options,
            index=strategy_options.index(recommended_strategy),
            horizontal=False,
            help="document_scan lê os documentos do índice em ordem; retrieval busca trechos por query dentro da pipeline estruturada. Nenhuma das estratégias reabre o PDF bruto em tempo real.",
            key="phase5_structured_context_strategy",
        )
        if selected_structured_task in {"cv_analysis", "extraction", "code_analysis"}:
            st.caption("Recomendado: document_scan")
        if selected_structured_task == "cv_analysis" and len(active_structured_document_ids) > 1:
            st.warning("Para `cv_analysis`, o ideal é selecionar 1 currículo por vez para evitar mistura de perfis.")
    else:
        structured_context_strategy = recommended_strategy
        st.caption("Estratégia oculta porque nenhum documento será usado nesta execução.")

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

    can_run_structured = bool(structured_input_text.strip()) or bool(structured_use_documents and active_structured_document_ids)

    # Show context preview outside the form
    with st.container(border=True):
        st.markdown("### Contexto final enviado para a IA")
        if active_structured_document_ids:
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
            with st.spinner("Generating structured output..."):
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
                    context_window=context_window,
                )
                structured_result = structured_service.execute_task(structured_request)
                st.session_state[STRUCTURED_RESULT_STATE_KEY] = structured_result.model_dump(mode="json")
                default_mode = structured_result.primary_render_mode or "json"
                st.session_state[STRUCTURED_RENDER_MODE_STATE_KEY] = default_mode

    if structured_submit:
        st.session_state["phase5_structured_input"] = structured_input_text
        with st.spinner("Generating structured output..."):
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
                context_window=context_window,
            )
            structured_result = structured_service.execute_task(structured_request)
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