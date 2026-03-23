import streamlit as st


def render_chat_sidebar(
    provider_options: dict[str, str],
    default_provider: str,
    models_by_provider: dict[str, list[str]],
    default_model_by_provider: dict[str, str],
    prompt_profiles: dict[str, dict[str, str]],
    default_prompt_profile: str,
    default_temperature: float,
    default_context_window_by_provider: dict[str, int],
    default_rag_chunk_size: int,
    default_rag_chunk_overlap: int,
    default_rag_top_k: int,
    default_pdf_extraction_mode: str,
    embedding_model_options: list[str],
    default_embedding_model: str,
    default_embedding_context_window: int,
    indexed_documents_count: int,
    indexed_chunks_count: int,
    provider_details: dict[str, str],
    history_filename: str,
    messages_count: int,
    last_latency: float | None,
) -> tuple[str, str, str, float, str, int, int, int, int, str, int, str, bool, bool]:
    provider_keys = list(provider_options.keys())
    default_provider_index = provider_keys.index(default_provider) if default_provider in provider_keys else 0
    pdf_mode_options = ["basic", "hybrid", "complete"]
    pdf_mode_labels = {
        "basic": "Básico · pypdf apenas · mais rápido",
        "hybrid": "Híbrido inteligente · melhor equilíbrio",
        "complete": "Completo por página · máxima cobertura",
    }
    default_pdf_mode = default_pdf_extraction_mode if default_pdf_extraction_mode in pdf_mode_options else "hybrid"

    with st.sidebar:
        st.header("Configurações")
        selected_provider = st.selectbox(
            "Provider",
            provider_keys,
            index=default_provider_index,
            format_func=lambda key: provider_options[key],
        )

        provider_models = models_by_provider.get(selected_provider, [])
        default_model = default_model_by_provider.get(selected_provider, provider_models[0] if provider_models else "")
        default_model_index = provider_models.index(default_model) if default_model in provider_models else 0

        selected_model = st.selectbox("Modelo", provider_models, index=default_model_index)

        prompt_profile_keys = list(prompt_profiles.keys())
        default_profile_index = (
            prompt_profile_keys.index(default_prompt_profile)
            if default_prompt_profile in prompt_profile_keys
            else 0
        )
        selected_prompt_profile = st.selectbox(
            "Perfil de prompt",
            prompt_profile_keys,
            index=default_profile_index,
            format_func=lambda key: prompt_profiles[key]["label"],
        )

        context_window = default_context_window_by_provider.get(selected_provider, 8192)
        context_window_mode = "manual"
        if selected_provider == "ollama":
            context_window_mode = st.radio(
                "Modo da janela de contexto",
                options=["auto", "manual"],
                index=0,
                format_func=lambda value: "Automático" if value == "auto" else "Manual",
                help="No modo automático, o app escolhe o `num_ctx` conforme a task e o tamanho do documento. No manual, usa o valor do slider.",
            )
            if context_window_mode == "manual":
                context_window = int(
                    st.slider(
                        "Janela de contexto (num_ctx)",
                        min_value=1000,
                        max_value=256000,
                        value=max(int(context_window), 1024),
                        step=100,
                        help="Controla o tamanho de contexto enviado ao Ollama nesta execução.",
                    )
                )

        temperature = st.slider(
            "Temperatura",
            min_value=0.0,
            max_value=1.5,
            value=min(max(default_temperature, 0.0), 1.5),
            step=0.1,
        )

        st.divider()
        st.subheader("Embedding")
        embedding_options = embedding_model_options or [default_embedding_model]
        if default_embedding_model in embedding_options:
            default_embedding_index = embedding_options.index(default_embedding_model)
        else:
            default_embedding_index = 0
        selected_embedding_model = st.selectbox(
            "Modelo de embedding",
            embedding_options,
            index=default_embedding_index,
            help="Trocar o modelo de embedding exige reindexar para manter o espaço vetorial consistente.",
        )
        selected_embedding_context_window = int(
            st.slider(
                "Janela de contexto do embedding",
                min_value=256,
                max_value=65536,
                value=max(int(default_embedding_context_window), 256),
                step=256,
                help="Valor enviado ao endpoint nativo de embeddings do Ollama via `options.num_ctx`. Se mudar, reindexe para manter o índice consistente.",
            )
        )

        st.divider()
        st.subheader("RAG / Testes")
        rag_chunk_size = int(
            st.slider(
                "Chunk size",
                min_value=300,
                max_value=4000,
                value=max(int(default_rag_chunk_size), 300),
                step=100,
                help="Controla o tamanho dos chunks na próxima indexação.",
            )
        )
        rag_chunk_overlap = int(
            st.slider(
                "Chunk overlap",
                min_value=0,
                max_value=max(0, rag_chunk_size // 2),
                value=min(int(default_rag_chunk_overlap), max(0, rag_chunk_size // 2)),
                step=50,
                help="Controla a sobreposição entre chunks na próxima indexação.",
            )
        )
        rag_top_k = int(
            st.slider(
                "Top-k da recuperação",
                min_value=1,
                max_value=12,
                value=max(int(default_rag_top_k), 1),
                step=1,
                help="Quantidade de chunks recuperados a cada pergunta.",
            )
        )
        selected_pdf_extraction_mode = st.selectbox(
            "Extração de PDFs",
            pdf_mode_options,
            index=pdf_mode_options.index(default_pdf_mode),
            format_func=lambda key: pdf_mode_labels[key],
            help="Básico = pypdf. Híbrido = rápido com enriquecimento seletivo. Completo = Docling/OCR página a página com cobertura máxima e custo maior.",
        )
        debug_retrieval = st.checkbox(
            "Mostrar debug de retrieval",
            value=False,
            help="Exibe detalhes dos chunks recuperados, scores e parâmetros ativos do RAG.",
        )

        clear_requested = st.button("🧹 Limpar conversa", width="stretch")

        st.divider()
        st.metric("Mensagens na conversa", messages_count)
        if last_latency is not None:
            st.metric("Última resposta", f"{last_latency:.2f}s")

        detail = provider_details.get(selected_provider)
        if detail:
            st.caption(detail)
        if selected_provider == "ollama":
            if context_window_mode == "auto":
                st.caption("Contexto ativo no Ollama: `auto`")
            else:
                st.caption(f"Contexto ativo no Ollama: `{context_window}`")
        st.caption(f"Embedding ativo: {selected_embedding_model} · num_ctx={selected_embedding_context_window}")
        st.caption(
            f"RAG atual: {indexed_documents_count} documento(s) · {indexed_chunks_count} chunks · top-k={rag_top_k} · overlap={rag_chunk_overlap}"
        )
        st.caption(f"Extração PDF ativa: {pdf_mode_labels[selected_pdf_extraction_mode]}")
        st.caption("Pipeline ativo: retrieval vetorial + reranking híbrido + budget de contexto no prompt.")
        st.caption(f"Histórico local: `{history_filename}`")
        st.caption(prompt_profiles[selected_prompt_profile]["description"])
        st.info("RAG Avançado (Base Documental): Fase 4.5 ativa.")

    return (
        selected_provider,
        selected_model,
        selected_prompt_profile,
        temperature,
        context_window_mode,
        int(context_window),
        rag_chunk_size,
        rag_chunk_overlap,
        rag_top_k,
        selected_embedding_model,
        selected_embedding_context_window,
        selected_pdf_extraction_mode,
        clear_requested,
        debug_retrieval,
    )
