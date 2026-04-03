import streamlit as st


def _format_ratio(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.0%}"
    return "n/d"


def _humanize_eval_recommendation(value: object) -> str:
    normalized = str(value or "").strip().lower()
    mapping = {
        "consider_targeted_adaptation_only_for_specific_tasks": "Considere adaptação direcionada só para tasks específicas.",
        "prompt_rag_schema_iteration_still_sufficient_globally": "Prompt + RAG + schema ainda parecem suficientes globalmente.",
        "prompt_rag_stack_currently_sufficient": "Prompt + RAG atuais parecem suficientes para esta task.",
        "improve_checklist_decomposition_and_source_alignment": "Melhorar decomposição do checklist e alinhamento com o texto-fonte.",
        "improve_ocr_router_contact_postprocessing_before_model_adaptation": "Melhorar OCR/router/pós-processamento de contatos antes de adaptar modelo.",
        "improve_grounding_and_field_resolution_before_model_adaptation": "Melhorar grounding e resolução de campos antes de adaptar modelo.",
        "consider_task_specific_model_adaptation_after_more_eval_cases": "Considere adaptação específica da task após ampliar os casos de eval.",
        "continue_prompt_grounding_and_schema_iteration": "Continue iterando prompt, grounding e schema.",
        "expand_eval_cases_and_iterate_prompt_rag_schema": "Expanda os evals e continue iterando prompt + RAG + schema.",
        "insufficient_eval_data": "Ainda não há dados de eval suficientes.",
    }
    return mapping.get(normalized, str(value or ""))


def _humanize_adaptation_priority(value: object) -> str:
    normalized = str(value or "").strip().lower()
    mapping = {
        "high": "Alta",
        "medium": "Média",
        "low": "Baixa",
    }
    return mapping.get(normalized, str(value or ""))


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
    default_rag_loader_strategy: str,
    default_rag_chunking_strategy: str,
    default_rag_retrieval_strategy: str,
    default_pdf_extraction_mode: str,
    embedding_provider_options: dict[str, str],
    default_embedding_provider: str,
    embedding_models_by_provider: dict[str, list[str]],
    default_embedding_model_by_provider: dict[str, str],
    default_embedding_context_window: int,
    default_embedding_truncate: bool,
    indexed_documents_count: int,
    indexed_chunks_count: int,
    default_rerank_pool_size: int,
    default_rerank_lexical_weight: float,
    default_vl_model: str,
    default_ocr_backend: str,
    embedding_provider_unavailable_items: list[dict[str, str]],
    provider_details: dict[str, str],
    history_filename: str,
    messages_count: int,
    last_latency: float | None,
) -> tuple[object, ...]:
    provider_keys = list(provider_options.keys())
    default_provider_index = provider_keys.index(default_provider) if default_provider in provider_keys else 0
    context_window_supported_providers = {"ollama", "huggingface_server"}
    pdf_mode_options = ["basic", "hybrid", "complete"]
    pdf_mode_labels = {
        "basic": "Básico · pypdf apenas · mais rápido",
        "hybrid": "Híbrido inteligente · melhor equilíbrio",
        "complete": "Completo por página · máxima cobertura",
    }
    default_pdf_mode = default_pdf_extraction_mode if default_pdf_extraction_mode in pdf_mode_options else "hybrid"

    with st.sidebar:
        st.header("Configurações operacionais")
        st.subheader("Geração")
        provider_state_key = "phase5_sidebar_provider"
        provider_current = st.session_state.get(provider_state_key, default_provider)
        if provider_current not in provider_keys:
            provider_current = provider_keys[default_provider_index] if provider_keys else default_provider
        selected_provider = st.selectbox(
            "Provider de geração",
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
            "Modelo de geração",
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
        if selected_provider in context_window_supported_providers:
            context_window_mode = st.radio(
                "Modo da janela de contexto",
                options=["auto", "manual"],
                index=0,
                key="phase5_sidebar_context_window_mode",
                format_func=lambda value: "Automático" if value == "auto" else "Manual",
                help="No modo automático, o app escolhe um budget operacional de contexto conforme a task e o tamanho do documento. No manual, usa o valor do slider.",
            )
            if context_window_mode == "manual":
                context_window = int(
                    st.slider(
                        "Janela de contexto da geração",
                        min_value=1000,
                        max_value=256000,
                        value=max(int(context_window), 1024),
                        step=100,
                        key="phase5_sidebar_context_window_value",
                        help="Controla o budget operacional de contexto usado nesta execução.",
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
        st.subheader("Embeddings")
        embedding_provider_keys = list(embedding_provider_options.keys())
        default_embedding_provider_index = (
            embedding_provider_keys.index(default_embedding_provider)
            if default_embedding_provider in embedding_provider_keys
            else 0
        )
        embedding_provider_state_key = "phase5_sidebar_embedding_provider"
        embedding_provider_current = st.session_state.get(embedding_provider_state_key, default_embedding_provider)
        if embedding_provider_current not in embedding_provider_keys:
            embedding_provider_current = (
                embedding_provider_keys[default_embedding_provider_index]
                if embedding_provider_keys
                else default_embedding_provider
            )
        selected_embedding_provider = st.selectbox(
            "Provider de embeddings",
            embedding_provider_keys,
            index=(
                embedding_provider_keys.index(embedding_provider_current)
                if embedding_provider_current in embedding_provider_keys
                else default_embedding_provider_index
            ),
            key=embedding_provider_state_key,
            format_func=lambda key: embedding_provider_options[key],
            help="Permite separar o provider de geração do provider usado para embeddings e retrieval.",
        )

        embedding_options = embedding_models_by_provider.get(selected_embedding_provider, [])
        default_embedding_model = default_embedding_model_by_provider.get(
            selected_embedding_provider,
            embedding_options[0] if embedding_options else "",
        )
        default_embedding_index = embedding_options.index(default_embedding_model) if default_embedding_model in embedding_options else 0
        embedding_model_state_key = "phase5_sidebar_embedding_model"
        embedding_model_current = st.session_state.get(embedding_model_state_key, default_embedding_model)
        if embedding_model_current not in embedding_options:
            embedding_model_current = default_embedding_model if default_embedding_model in embedding_options else (embedding_options[0] if embedding_options else "")
        selected_embedding_model = st.selectbox(
            "Modelo de embeddings",
            embedding_options,
            index=embedding_options.index(embedding_model_current) if embedding_model_current in embedding_options else default_embedding_index,
            key=embedding_model_state_key,
            help="Trocar o modelo de embedding exige reindexar para manter o espaço vetorial consistente.",
        )
        selected_embedding_context_window = int(
            st.slider(
                "Janela de contexto dos embeddings",
                min_value=256,
                max_value=65536,
                value=max(int(default_embedding_context_window), 256),
                step=256,
                key="phase5_sidebar_embedding_context_window",
                help="Valor enviado ao endpoint nativo de embeddings do Ollama via `options.num_ctx`. Se mudar, reindexe para manter o índice consistente.",
            )
        )
        selected_embedding_truncate = st.checkbox(
            "Permitir truncate nos embeddings",
            value=bool(default_embedding_truncate),
            key="phase5_sidebar_embedding_truncate",
            help="Quando ativo, o provider de embeddings pode truncar entradas longas conforme o backend permitir.",
        )
        if embedding_provider_unavailable_items:
            with st.expander("Providers de embedding indisponíveis agora", expanded=False):
                for item in embedding_provider_unavailable_items:
                    provider_label = str(item.get("label") or item.get("provider_key") or "provider")
                    reason = str(item.get("reason") or "indisponível")
                    st.caption(f"- **{provider_label}** · desabilitado: {reason}")

        st.divider()
        st.subheader("Retrieval / RAG")
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
        selected_rerank_pool_size = int(
            st.slider(
                "Pool de reranking",
                min_value=max(2, rag_top_k),
                max_value=32,
                value=max(int(default_rerank_pool_size), rag_top_k),
                step=1,
                key="phase5_sidebar_rerank_pool_size",
                help="Quantidade de candidatos considerados antes do corte final do top-k após o reranking híbrido.",
            )
        )
        selected_rerank_lexical_weight = float(
            st.slider(
                "Peso lexical no reranking",
                min_value=0.0,
                max_value=0.9,
                value=min(max(float(default_rerank_lexical_weight), 0.0), 0.9),
                step=0.05,
                key="phase5_sidebar_rerank_lexical_weight",
                help="Mistura entre score vetorial e score lexical no reranking híbrido. Valores maiores dão mais peso ao matching textual.",
            )
        )
        loader_strategy_options = ["manual", "langchain_basic"]
        loader_strategy_labels = {
            "manual": "Manual local",
            "langchain_basic": "LangChain loaders (experimental)",
        }
        default_loader_strategy = (
            default_rag_loader_strategy
            if default_rag_loader_strategy in loader_strategy_options
            else "manual"
        )
        selected_loader_strategy = st.selectbox(
            "Estratégia de loader",
            loader_strategy_options,
            index=loader_strategy_options.index(default_loader_strategy),
            key="phase5_sidebar_loader_strategy",
            format_func=lambda key: loader_strategy_labels[key],
            help="Micro-slice da Fase 5.5: usa loaders básicos do ecossistema LangChain para TXT/CSV/MD/PY quando o pacote opcional estiver disponível. PDFs continuam no pipeline customizado do projeto.",
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

        st.divider()
        st.subheader("PDF / OCR / Vision")
        selected_pdf_extraction_mode = st.selectbox(
            "Extração de PDFs",
            pdf_mode_options,
            index=pdf_mode_options.index(default_pdf_mode),
            key="phase5_sidebar_pdf_extraction_mode",
            format_func=lambda key: pdf_mode_labels[key],
            help="Básico = pypdf. Híbrido = rápido com enriquecimento seletivo. Completo = Docling/OCR página a página com cobertura máxima e custo maior.",
        )
        ocr_backend_options = ["ocrmypdf", "docling"]
        ocr_backend_labels = {
            "ocrmypdf": "OCRMyPDF",
            "docling": "Docling",
        }
        selected_ocr_backend = st.selectbox(
            "Backend OCR documental",
            ocr_backend_options,
            index=ocr_backend_options.index(default_ocr_backend) if default_ocr_backend in ocr_backend_options else 0,
            key="phase5_sidebar_ocr_backend",
            format_func=lambda key: ocr_backend_labels.get(key, key),
            help="Backend preferido para a trilha documental/evidence quando OCR for necessário.",
        )
        selected_vl_model = (
            st.text_input(
                "Modelo VLM documental",
                value=default_vl_model,
                key="phase5_sidebar_vlm_model",
                help="Modelo de visão usado pela trilha documental em casos que exigem leitura visual/regional do documento.",
            ).strip()
            or default_vl_model
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
        if selected_provider == "huggingface_server":
            st.caption(
                "Os modelos exibidos neste provider são aliases publicados pelo serviço. O backend real pode ser Ollama, MLX, GGUF, OpenAI ou outro runtime suportado pelo hub."
            )
        if selected_provider in context_window_supported_providers:
            if context_window_mode == "auto":
                st.caption(f"Contexto ativo em {provider_options.get(selected_provider, selected_provider)}: `auto`")
            else:
                st.caption(f"Contexto ativo em {provider_options.get(selected_provider, selected_provider)}: `{context_window}`")
        st.caption(
            f"Embeddings ativos: {embedding_provider_options.get(selected_embedding_provider, selected_embedding_provider)} · {selected_embedding_model} · num_ctx={selected_embedding_context_window} · truncate={selected_embedding_truncate}"
        )
        st.caption(
            f"RAG atual: {indexed_documents_count} documento(s) · {indexed_chunks_count} chunks · top-k={rag_top_k} · overlap={rag_chunk_overlap} · rerank_pool={selected_rerank_pool_size} · lexical_weight={selected_rerank_lexical_weight:.2f}"
        )
        st.caption(f"Loader ativo: {loader_strategy_labels[selected_loader_strategy]}")
        st.caption(f"Chunking ativo: {chunking_strategy_labels[selected_chunking_strategy]}")
        st.caption(f"Retrieval ativo: {retrieval_strategy_labels[selected_retrieval_strategy]}")
        st.caption(f"Extração PDF ativa: {pdf_mode_labels[selected_pdf_extraction_mode]}")
        st.caption(f"OCR documental: {ocr_backend_labels.get(selected_ocr_backend, selected_ocr_backend)}")
        st.caption(f"VLM documental: {selected_vl_model}")
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
                        "embedding_provider": chat.get("embedding_provider"),
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
                        "execution_strategy": structured.get("execution_strategy"),
                        "provider": structured.get("provider"),
                        "model": structured.get("model"),
                        "selected_documents": structured.get("selected_documents"),
                        "agent_intent": structured.get("agent_intent"),
                        "agent_tool": structured.get("agent_tool"),
                        "agent_answer_mode": structured.get("agent_answer_mode"),
                        "agent_available_tools": structured.get("agent_available_tools"),
                        "needs_review": structured.get("needs_review"),
                        "needs_review_reason": structured.get("needs_review_reason"),
                        "agent_limitations": structured.get("agent_limitations"),
                        "agent_recommended_actions": structured.get("agent_recommended_actions"),
                        "agent_guardrails_applied": structured.get("agent_guardrails_applied"),
                        "workflow_attempts": structured.get("workflow_attempts"),
                        "workflow_context_strategies": structured.get("workflow_context_strategies"),
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
                        "loader_strategy": documents.get("loader_strategy"),
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

        document_agent = snapshot.get("document_agent")
        if isinstance(document_agent, dict) and document_agent:
            with st.expander("Document Operations Copilot · histórico agregado", expanded=False):
                st.write(
                    {
                        "log_path": document_agent.get("log_path"),
                        "log_exists": document_agent.get("log_exists"),
                        "entries_considered": document_agent.get("entries_considered"),
                        "latest_timestamp": document_agent.get("latest_timestamp"),
                    }
                )

                if document_agent.get("log_exists") and int(document_agent.get("total_runs") or 0) > 0:
                    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
                    metric_col_1.metric("Runs", int(document_agent.get("total_runs") or 0))
                    metric_col_2.metric("Sucesso", _format_ratio(document_agent.get("success_rate")))
                    metric_col_3.metric("Needs review", _format_ratio(document_agent.get("needs_review_rate")))
                    metric_col_4.metric("Confiança média", _format_ratio(document_agent.get("avg_confidence")))
                    st.caption(
                        "Esse bloco resume o comportamento agregado do copiloto documental: intenções, tools, guardrails e casos recentes que pediram revisão humana."
                    )

                    runs_with_tool_errors = int(document_agent.get("runs_with_tool_errors") or 0)
                    if runs_with_tool_errors:
                        st.warning(f"Execuções com erro de tool: {runs_with_tool_errors}")

                    for label, field_name, key_name in [
                        ("Distribuição por intenção", "intent_counts", "intent"),
                        ("Distribuição por tool", "tool_counts", "tool"),
                        ("Decision counts · route", "workflow_route_decision_counts", "route_decision"),
                        ("Decision counts · guardrail", "workflow_guardrail_decision_counts", "guardrail_decision"),
                    ]:
                        rows = document_agent.get(field_name)
                        if isinstance(rows, dict) and rows:
                            st.caption(label)
                            st.dataframe(
                                [
                                    {key_name: name, "count": count}
                                    for name, count in rows.items()
                                ],
                                width="stretch",
                            )

                    needs_review_examples = document_agent.get("needs_review_examples")
                    if isinstance(needs_review_examples, list) and needs_review_examples:
                        st.caption("Exemplos recentes que pediram revisão humana")
                        st.dataframe(needs_review_examples, width="stretch")

                    recent_entries = document_agent.get("recent_entries")
                    if isinstance(recent_entries, list) and recent_entries:
                        st.caption("Execuções recentes do copiloto")
                        st.dataframe(
                            [
                                {
                                    "timestamp": entry.get("timestamp"),
                                    "intent": entry.get("user_intent"),
                                    "tool": entry.get("tool_used"),
                                    "confidence": entry.get("confidence"),
                                    "needs_review": entry.get("needs_review"),
                                    "needs_review_reason": entry.get("needs_review_reason"),
                                    "query": entry.get("query"),
                                }
                                for entry in recent_entries[:10]
                                if isinstance(entry, dict)
                            ],
                            width="stretch",
                        )

        runtime_execution = snapshot.get("runtime_execution")
        if isinstance(runtime_execution, dict) and runtime_execution:
            with st.expander("Observabilidade · histórico agregado de execuções", expanded=False):
                st.write(
                    {
                        "log_path": runtime_execution.get("log_path"),
                        "log_exists": runtime_execution.get("log_exists"),
                        "entries_considered": runtime_execution.get("entries_considered"),
                        "latest_timestamp": runtime_execution.get("latest_timestamp"),
                    }
                )

                if runtime_execution.get("log_exists") and int(runtime_execution.get("total_runs") or 0) > 0:
                    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
                    metric_col_1.metric("Runs", int(runtime_execution.get("total_runs") or 0))
                    metric_col_2.metric("Sucesso", _format_ratio(runtime_execution.get("success_rate")))
                    metric_col_3.metric("Erro", _format_ratio(runtime_execution.get("error_rate")))
                    metric_col_4.metric("Needs review", _format_ratio(runtime_execution.get("needs_review_rate")))

                    st.caption(
                        f"Latência média total: {float(runtime_execution.get('avg_latency_s', 0.0)):.2f}s · "
                        f"retrieval: {float(runtime_execution.get('avg_retrieval_latency_s', 0.0)):.2f}s · "
                        f"geração: {float(runtime_execution.get('avg_generation_latency_s', 0.0)):.2f}s"
                    )
                    st.caption(
                        f"Tokens médios: prompt={float(runtime_execution.get('avg_prompt_tokens', 0.0)):.1f} · "
                        f"completion={float(runtime_execution.get('avg_completion_tokens', 0.0)):.1f} · "
                        f"total={float(runtime_execution.get('avg_total_tokens', 0.0)):.1f}"
                    )
                    costed_runs = int(runtime_execution.get("costed_runs") or 0)
                    if costed_runs > 0:
                        st.caption(
                            f"Custo direto estimado: total=${float(runtime_execution.get('total_cost_usd', 0.0)):.6f} · "
                            f"média/run=${float(runtime_execution.get('avg_cost_usd', 0.0)):.6f} · runs com pricing={costed_runs}"
                        )

                    for label, field_name, key_name in [
                        ("Distribuição por fluxo", "flow_counts", "flow_type"),
                        ("Distribuição por task", "task_counts", "task_type"),
                        ("Distribuição por provider", "provider_counts", "provider"),
                        ("Distribuição por model", "model_counts", "model"),
                        ("Distribuição por fonte de usage", "usage_source_counts", "usage_source"),
                    ]:
                        rows = runtime_execution.get(field_name)
                        if isinstance(rows, dict) and rows:
                            st.caption(label)
                            st.dataframe(
                                [
                                    {key_name: name, "count": count}
                                    for name, count in rows.items()
                                ],
                                width="stretch",
                            )

                    recent_entries = runtime_execution.get("recent_entries")
                    if isinstance(recent_entries, list) and recent_entries:
                        st.caption("Execuções recentes")
                        st.dataframe(
                            [
                                {
                                    "timestamp": entry.get("timestamp"),
                                    "flow": entry.get("flow_type"),
                                    "task": entry.get("task_type"),
                                    "success": entry.get("success"),
                                    "provider": entry.get("provider"),
                                    "model": entry.get("model"),
                                    "latency_s": entry.get("latency_s"),
                                    "tokens": entry.get("total_tokens"),
                                    "cost_usd": entry.get("cost_usd"),
                                    "usage_source": entry.get("usage_source"),
                                    "needs_review": entry.get("needs_review"),
                                    "error_message": entry.get("error_message"),
                                }
                                for entry in recent_entries[:10]
                                if isinstance(entry, dict)
                            ],
                            width="stretch",
                        )

        evals = snapshot.get("evals")
        if isinstance(evals, dict) and evals:
            with st.expander("Evals / readiness da Fase 8.5", expanded=False):
                global_recommendation = _humanize_eval_recommendation(evals.get("global_recommendation"))
                st.write(
                    {
                        "db_path": evals.get("db_path"),
                        "db_exists": evals.get("db_exists"),
                        "entries_considered": evals.get("entries_considered"),
                        "latest_created_at": evals.get("latest_created_at"),
                        "global_recommendation": global_recommendation,
                    }
                )

                if evals.get("db_exists") and int(evals.get("total_runs") or 0) > 0:
                    metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
                    metric_col_1.metric("Runs", int(evals.get("total_runs") or 0))
                    metric_col_2.metric("Pass rate", _format_ratio(evals.get("pass_rate")))
                    metric_col_3.metric("Fail rate", _format_ratio(evals.get("fail_rate")))
                    st.caption(
                        "Esses sinais ajudam a decidir onde continuar em prompt/RAG e onde a Fase 8.5 pode focar em embedding, reranker ou adaptação leve."
                    )
                    if global_recommendation:
                        st.info(global_recommendation)

                    suite_counts = evals.get("suite_counts")
                    if isinstance(suite_counts, dict) and suite_counts:
                        st.caption("Cobertura por suite")
                        st.dataframe(
                            [
                                {"suite_name": name, "runs": count}
                                for name, count in suite_counts.items()
                            ],
                            width="stretch",
                        )

                    task_counts = evals.get("task_counts")
                    if isinstance(task_counts, dict) and task_counts:
                        st.caption("Cobertura por task")
                        st.dataframe(
                            [
                                {"task_type": name, "runs": count}
                                for name, count in task_counts.items()
                            ],
                            width="stretch",
                        )

                    top_failure_reasons = evals.get("top_failure_reasons")
                    if isinstance(top_failure_reasons, list) and top_failure_reasons:
                        st.caption("Top failure reasons")
                        st.dataframe(top_failure_reasons, width="stretch")

                    adaptation_candidates = evals.get("adaptation_candidates")
                    if isinstance(adaptation_candidates, list) and adaptation_candidates:
                        st.caption("Candidatos de adaptação")
                        st.dataframe(
                            [
                                {
                                    "task_type": item.get("task_type"),
                                    "priority": _humanize_adaptation_priority(item.get("adaptation_priority")),
                                    "fail_rate": _format_ratio(item.get("fail_rate")),
                                    "avg_score_ratio": _format_ratio(item.get("avg_score_ratio")),
                                    "recommended_action": _humanize_eval_recommendation(item.get("recommended_action")),
                                }
                                for item in adaptation_candidates
                                if isinstance(item, dict)
                            ],
                            width="stretch",
                        )

                    next_eval_priorities = evals.get("next_eval_priorities")
                    if isinstance(next_eval_priorities, list) and next_eval_priorities:
                        st.caption("Próximas prioridades de eval")
                        st.dataframe(
                            [
                                {
                                    "task_type": item.get("task_type"),
                                    "fail_rate": _format_ratio(item.get("fail_rate")),
                                    "recent_fail_rate": _format_ratio(item.get("recent_fail_rate")),
                                    "recommended_action": _humanize_eval_recommendation(item.get("recommended_action")),
                                }
                                for item in next_eval_priorities
                                if isinstance(item, dict)
                            ],
                            width="stretch",
                        )

                    healthy_tasks = evals.get("healthy_tasks")
                    if isinstance(healthy_tasks, list) and healthy_tasks:
                        st.caption("Tasks saudáveis (prompt + RAG parecem suficientes)")
                        st.dataframe(
                            [
                                {
                                    "task_type": item.get("task_type"),
                                    "pass_rate": _format_ratio(item.get("pass_rate")),
                                    "avg_score_ratio": _format_ratio(item.get("avg_score_ratio")),
                                }
                                for item in healthy_tasks
                                if isinstance(item, dict)
                            ],
                            width="stretch",
                        )
