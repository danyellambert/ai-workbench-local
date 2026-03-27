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
    default_rag_chunking_strategy: str,
    default_rag_retrieval_strategy: str,
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
) -> tuple[str, str, str, float, str, int, int, int, int, str, int, str, str, str, bool, bool]:
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
        provider_state_key = "phase5_sidebar_provider"
        provider_current = st.session_state.get(provider_state_key, default_provider)
        if provider_current not in provider_keys:
            provider_current = provider_keys[default_provider_index] if provider_keys else default_provider
        selected_provider = st.selectbox(
            "Provider",
            provider_keys,
            index=provider_keys.index(provider_current) if provider_current in provider_keys else default_provider_index,
            key=provider_state_key,
            format_func=lambda key: provider_options[key],
        )

        provider_models = models_by_provider.get(selected_provider, [])
        default_model = default_model_by_provider.get(selected_provider, provider_models[0] if provider_models else "")
        default_model_index = provider_models.index(default_model) if default_model in provider_models else 0
        model_state_key = "phase5_sidebar_model"
        model_current = st.session_state.get(model_state_key, default_model)
        if model_current not in provider_models:
            model_current = default_model if default_model in provider_models else (provider_models[0] if provider_models else "")

        selected_model = st.selectbox(
            "Modelo",
            provider_models,
            index=provider_models.index(model_current) if model_current in provider_models else default_model_index,
            key=model_state_key,
        )

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
            key="phase5_sidebar_prompt_profile",
            format_func=lambda key: prompt_profiles[key]["label"],
        )

        context_window = default_context_window_by_provider.get(selected_provider, 8192)
        context_window_mode = "manual"
        if selected_provider == "ollama":
            context_window_mode = st.radio(
                "Modo da janela de contexto",
                options=["auto", "manual"],
                index=0,
                key="phase5_sidebar_context_window_mode",
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
                        key="phase5_sidebar_context_window_value",
                        help="Controla o tamanho de contexto enviado ao Ollama nesta execução.",
                    )
                )

        temperature = st.slider(
            "Temperatura",
            min_value=0.0,
            max_value=1.5,
            value=min(max(default_temperature, 0.0), 1.5),
            step=0.1,
            key="phase5_sidebar_temperature",
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
            key="phase5_sidebar_embedding_model",
            help="Trocar o modelo de embedding exige reindexar para manter o espaço vetorial consistente.",
        )
        selected_embedding_context_window = int(
            st.slider(
                "Janela de contexto do embedding",
                min_value=256,
                max_value=65536,
                value=max(int(default_embedding_context_window), 256),
                step=256,
                key="phase5_sidebar_embedding_context_window",
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
                key="phase5_sidebar_rag_chunk_size",
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
                key="phase5_sidebar_rag_chunk_overlap",
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
                key="phase5_sidebar_rag_top_k",
                help="Quantidade de chunks recuperados a cada pergunta.",
            )
        )
        chunking_strategy_options = ["manual", "langchain_recursive"]
        chunking_strategy_labels = {
            "manual": "Manual local",
            "langchain_recursive": "LangChain Recursive (experimental)",
        }
        default_chunking_strategy = (
            default_rag_chunking_strategy
            if default_rag_chunking_strategy in chunking_strategy_options
            else "manual"
        )
        selected_chunking_strategy = st.selectbox(
            "Estratégia de chunking",
            chunking_strategy_options,
            index=chunking_strategy_options.index(default_chunking_strategy),
            key="phase5_sidebar_chunking_strategy",
            format_func=lambda key: chunking_strategy_labels[key],
            help="Primeiro slice da Fase 5.5: permite testar chunking manual vs splitter compatível com LangChain quando o pacote opcional estiver disponível.",
        )
        retrieval_strategy_options = ["manual_hybrid", "langchain_chroma"]
        retrieval_strategy_labels = {
            "manual_hybrid": "Manual híbrido",
            "langchain_chroma": "LangChain + Chroma (experimental)",
        }
        default_retrieval_strategy = (
            default_rag_retrieval_strategy
            if default_rag_retrieval_strategy in retrieval_strategy_options
            else "manual_hybrid"
        )
        selected_retrieval_strategy = st.selectbox(
            "Estratégia de retrieval",
            retrieval_strategy_options,
            index=retrieval_strategy_options.index(default_retrieval_strategy),
            key="phase5_sidebar_retrieval_strategy",
            format_func=lambda key: retrieval_strategy_labels[key],
            help="Segundo slice da Fase 5.5: permite comparar o retrieval manual atual com um caminho experimental via LangChain + Chroma.",
        )
        selected_pdf_extraction_mode = st.selectbox(
            "Extração de PDFs",
            pdf_mode_options,
            index=pdf_mode_options.index(default_pdf_mode),
            key="phase5_sidebar_pdf_extraction_mode",
            format_func=lambda key: pdf_mode_labels[key],
            help="Básico = pypdf. Híbrido = rápido com enriquecimento seletivo. Completo = Docling/OCR página a página com cobertura máxima e custo maior.",
        )
        debug_retrieval = st.checkbox(
            "Mostrar debug de retrieval",
            value=False,
            key="phase5_sidebar_debug_retrieval",
            help="Exibe detalhes dos chunks recuperados, scores, parâmetros ativos do RAG e uma comparação shadow com a estratégia alternativa de retrieval.",
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
        st.caption(f"Chunking ativo: {chunking_strategy_labels[selected_chunking_strategy]}")
        st.caption(f"Retrieval ativo: {retrieval_strategy_labels[selected_retrieval_strategy]}")
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
        selected_chunking_strategy,
        selected_retrieval_strategy,
        selected_pdf_extraction_mode,
        clear_requested,
        debug_retrieval,
    )


def render_runtime_sidebar_panel(snapshot: dict[str, object] | None) -> None:
    if not isinstance(snapshot, dict) or not snapshot:
        return

    with st.sidebar:
        st.divider()
        st.subheader("Mapa operacional")

        provider_path = snapshot.get("provider_path")
        local_dependency = snapshot.get("local_dependency")
        if provider_path:
            st.caption(f"Rota ativa: {provider_path}")
        if local_dependency:
            st.caption(str(local_dependency))

        chat = snapshot.get("chat")
        if isinstance(chat, dict):
            with st.expander("Chat com RAG", expanded=False):
                st.write(
                    {
                        "provider": chat.get("provider"),
                        "model": chat.get("model"),
                        "embedding_model": chat.get("embedding_model"),
                        "selected_documents": chat.get("selected_documents"),
                        "retrieval_backend": chat.get("retrieval_backend"),
                        "retrieval_strategy": chat.get("retrieval_strategy"),
                        "retrieval_shadow_summary": chat.get("retrieval_shadow_summary"),
                        "last_total_s": chat.get("last_total_s"),
                        "last_generation_s": chat.get("last_generation_s"),
                        "last_retrieval_s": chat.get("last_retrieval_s"),
                        "last_prompt_build_s": chat.get("last_prompt_build_s"),
                    }
                )

        structured = snapshot.get("structured")
        if isinstance(structured, dict):
            with st.expander("Tasks estruturadas", expanded=False):
                st.write(
                    {
                        "current_task": structured.get("current_task"),
                        "provider": structured.get("provider"),
                        "model": structured.get("model"),
                        "selected_documents": structured.get("selected_documents"),
                        "last_total_s": structured.get("last_total_s"),
                        "last_provider_s": structured.get("last_provider_s"),
                        "last_pre_model_prep_s": structured.get("last_pre_model_prep_s"),
                        "last_document_load_s": structured.get("last_document_load_s"),
                        "last_sanitize_s": structured.get("last_sanitize_s"),
                        "last_context_s": structured.get("last_context_s"),
                        "last_parsing_s": structured.get("last_parsing_s"),
                    }
                )
                task_model_map = structured.get("task_model_map")
                if isinstance(task_model_map, dict) and task_model_map:
                    st.caption("Modelo efetivo por task")
                    st.dataframe(
                        [
                            {"task": task_name, "model": model_name}
                            for task_name, model_name in task_model_map.items()
                        ],
                        width="stretch",
                    )

        documents = snapshot.get("documents")
        if isinstance(documents, dict):
            with st.expander("Documentos / PDF / OCR / VL", expanded=False):
                st.write(
                    {
                        "chunking_strategy": documents.get("chunking_strategy"),
                        "retrieval_strategy": documents.get("retrieval_strategy"),
                        "pdf_extraction_mode": documents.get("pdf_extraction_mode"),
                        "ocr_backend_default": documents.get("ocr_backend_default"),
                        "vl_model_default": documents.get("vl_model_default"),
                        "indexed_documents": documents.get("indexed_documents"),
                    }
                )
                for label in ["chat_selected_docs", "structured_selected_docs"]:
                    rows = documents.get(label)
                    if isinstance(rows, list) and rows:
                        st.caption(label.replace("_", " "))
                        st.dataframe(rows, width="stretch")
