import time

import streamlit as st
from src.config import get_ollama_settings, get_rag_settings
from src.prompt_profiles import build_prompt_messages, get_prompt_profiles
from src.providers.registry import build_provider_registry
from src.rag.loaders import load_document
from src.rag.prompting import inject_rag_context
from src.rag.service import build_rag_index, build_source_metadata, retrieve_relevant_chunks
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
from src.services.rag_state import clear_rag_state, get_rag_index, initialize_rag_state, set_rag_index
from src.ui.chat import render_chat_message
from src.ui.sidebar import render_chat_sidebar


settings = get_ollama_settings()
rag_settings = get_rag_settings()
provider_registry = build_provider_registry()
prompt_profiles = get_prompt_profiles()
embedding_provider = provider_registry["ollama"]["instance"]

initialize_chat_state(load_chat_history(settings.history_path))
initialize_rag_state(load_rag_store(rag_settings.store_path))

messages = get_chat_messages()
last_latency = get_last_latency()
rag_index = get_rag_index()

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

selected_provider, selected_model, selected_prompt_profile, temperature, clear_requested = render_chat_sidebar(
    provider_options=provider_options,
    default_provider="ollama",
    models_by_provider=models_by_provider,
    default_model_by_provider=default_model_by_provider,
    prompt_profiles=prompt_profiles,
    default_prompt_profile=settings.default_prompt_profile,
    default_temperature=settings.default_temperature,
    provider_details=provider_details,
    history_filename=settings.history_path.name,
    messages_count=len(messages),
    last_latency=last_latency,
)

selected_provider_instance = provider_registry[selected_provider]["instance"]
selected_provider_label = provider_registry[selected_provider]["label"]
selected_prompt_profile_label = prompt_profiles[selected_prompt_profile]["label"]

if clear_requested:
    clear_chat_state()
    clear_chat_history(settings.history_path)
    st.rerun()

st.write(f"# {settings.project_name}")
st.caption(
    f"Provider: `{selected_provider}` · Modelo: `{selected_model}` · Perfil: `{selected_prompt_profile}` · Temperatura: `{temperature:.1f}`"
)

st.divider()
st.subheader("Documentos (Fase 4 — RAG)")
uploaded_file = st.file_uploader(
    "Envie um documento para indexar",
    type=["pdf", "txt", "csv", "md", "py"],
    help="Formatos suportados: PDF, TXT, CSV, MD e PY.",
)

coluna_indexar, coluna_limpar = st.columns(2)
with coluna_indexar:
    index_requested = st.button(
        "📚 Indexar documento",
        use_container_width=True,
        disabled=uploaded_file is None,
    )
with coluna_limpar:
    clear_rag_requested = st.button(
        "🗑️ Limpar índice",
        use_container_width=True,
        disabled=rag_index is None,
    )

if index_requested and uploaded_file is not None:
    try:
        with st.spinner("Extraindo texto, criando chunks e gerando embeddings..."):
            loaded_document = load_document(uploaded_file)
            built_rag_index = build_rag_index(
                document=loaded_document,
                settings=rag_settings,
                embedding_provider=embedding_provider,
            )
            set_rag_index(built_rag_index)
            save_rag_store(rag_settings.store_path, built_rag_index)
        st.success(f"Documento indexado com sucesso: {loaded_document.name}")
        st.rerun()
    except Exception as error:
        st.error(f"Erro ao indexar documento: {error}")

if clear_rag_requested:
    clear_rag_state()
    clear_rag_store(rag_settings.store_path)
    st.success("Índice RAG removido com sucesso.")
    st.rerun()

rag_index = get_rag_index()
if rag_index:
    document_info = rag_index.get("document", {}) if isinstance(rag_index, dict) else {}
    chunks = rag_index.get("chunks", []) if isinstance(rag_index, dict) else []
    rag_info = rag_index.get("settings", {}) if isinstance(rag_index, dict) else {}

    st.success(
        f"Documento indexado: {document_info.get('name', 'documento')} · {len(chunks)} chunks"
    )
    with st.expander("Detalhes do índice RAG"):
        st.write(
            {
                "arquivo": document_info.get("name"),
                "tipo": document_info.get("file_type"),
                "caracteres": document_info.get("char_count"),
                "embedding_model": rag_info.get("embedding_model"),
                "chunk_size": rag_info.get("chunk_size"),
                "chunk_overlap": rag_info.get("chunk_overlap"),
                "top_k": rag_info.get("top_k"),
                "criado_em": rag_index.get("created_at"),
            }
        )
else:
    st.info("Nenhum documento indexado ainda. Faça upload e clique em 'Indexar documento'.")

if selected_provider == "openai":
    st.info("Provider cloud habilitado por configuração local. Benchmark real com cloud continua sendo foco principal da Fase 7.")

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
    }
    append_chat_message("user", texto_usuario, metadata=user_metadata)
    save_chat_history(settings.history_path, get_chat_messages())

    texto_resposta_ia = ""
    retrieved_chunks = []

    if rag_index:
        try:
            retrieved_chunks = retrieve_relevant_chunks(
                query=texto_usuario,
                rag_index=rag_index,
                settings=rag_settings,
                embedding_provider=embedding_provider,
            )
        except Exception as error:
            st.warning(f"Não foi possível recuperar contexto do documento. A resposta seguirá sem RAG. Detalhes: {error}")
            retrieved_chunks = []

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            inicio = time.perf_counter()
            model_messages = inject_rag_context(
                build_prompt_messages(selected_prompt_profile, get_chat_messages()),
                retrieved_chunks,
            )
            stream = selected_provider_instance.stream_chat_completion(
                messages=model_messages,
                model=selected_model,
                temperature=temperature,
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
        except Exception as erro:
            set_last_latency(None)
            texto_resposta_ia = selected_provider_instance.format_error(selected_model, erro)
            placeholder.empty()
            st.error(texto_resposta_ia)

    assistant_metadata = {
        **user_metadata,
        "latency_s": round(get_last_latency(), 2) if get_last_latency() is not None else None,
        "sources": build_source_metadata(retrieved_chunks),
    }
    append_chat_message("assistant", texto_resposta_ia, metadata=assistant_metadata)
    save_chat_history(settings.history_path, get_chat_messages())
