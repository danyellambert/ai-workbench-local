import streamlit as st


def _format_ratio(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.0%}"
    return "n/a"


def _humanize_eval_recommendation(value: object) -> str:
    normalized = str(value or "").strip().lower()
    mapping = {
        "consider_targeted_adaptation_only_for_specific_tasks": "Consider targeted adaptation only for specific tasks.",
        "prompt_rag_schema_iteration_still_sufficient_globally": "Prompt + RAG + schema still seem sufficient overall.",
        "prompt_rag_stack_currently_sufficient": "Current prompt + RAG seem sufficient for this task.",
        "improve_checklist_decomposition_and_source_alignment": "Improve checklist decomposition and alignment with the source text.",
        "improve_ocr_router_contact_postprocessing_before_model_adaptation": "Improve OCR/router/contact post-processing before adapting the model.",
        "improve_grounding_and_field_resolution_before_model_adaptation": "Improve grounding and field resolution before adapting the model.",
        "consider_task_specific_model_adaptation_after_more_eval_cases": "Consider task-specific adaptation after expanding the eval cases.",
        "continue_prompt_grounding_and_schema_iteration": "Continue iterating on prompt, grounding, and schema.",
        "expand_eval_cases_and_iterate_prompt_rag_schema": "Expand the eval cases and keep iterating on prompt + RAG + schema.",
        "insufficient_eval_data": "There is still not enough eval data.",
    }
    return mapping.get(normalized, str(value or ""))


def _humanize_adaptation_priority(value: object) -> str:
    normalized = str(value or "").strip().lower()
    mapping = {
        "high": "High",
        "medium": "Medium",
        "low": "Low",
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
        "basic": "Basic · pypdf only · faster",
        "hybrid": "Smart hybrid · better balance",
        "complete": "Per-page complete · maximum coverage",
    }
    default_pdf_mode = default_pdf_extraction_mode if default_pdf_extraction_mode in pdf_mode_options else "hybrid"

    with st.sidebar:
        st.header("Operational settings")
        st.subheader("Generation")
        provider_state_key = "phase5_sidebar_provider"
        provider_current = st.session_state.get(provider_state_key, default_provider)
        if provider_current not in provider_keys:
            provider_current = provider_keys[default_provider_index] if provider_keys else default_provider
        selected_provider = st.selectbox(
            "Generation provider",
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
            "Generation model",
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
            "Prompt profile",
            prompt_profile_keys,
            index=default_profile_index,
            key="phase5_sidebar_prompt_profile",
            format_func=lambda key: prompt_profiles[key]["label"],
        )

        context_window = default_context_window_by_provider.get(selected_provider, 8192)
        context_window_mode = "manual"
        if selected_provider in context_window_supported_providers:
            context_window_mode = st.radio(
                "Context window mode",
                options=["auto", "manual"],
                index=0,
                key="phase5_sidebar_context_window_mode",
                format_func=lambda value: "Automatic" if value == "auto" else "Manual",
                help="In automatic mode, the app chooses an operational context budget based on the task and document size. In manual mode, it uses the slider value.",
            )
            if context_window_mode == "manual":
                context_window = int(
                    st.slider(
                        "Generation context window",
                        min_value=1000,
                        max_value=256000,
                        value=max(int(context_window), 1024),
                        step=100,
                        key="phase5_sidebar_context_window_value",
                        help="Controls the operational context budget used in this execution.",
                    )
                )

        temperature = st.slider(
            "Temperature",
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
            "Embedding provider",
            embedding_provider_keys,
            index=(
                embedding_provider_keys.index(embedding_provider_current)
                if embedding_provider_current in embedding_provider_keys
                else default_embedding_provider_index
            ),
            key=embedding_provider_state_key,
            format_func=lambda key: embedding_provider_options[key],
            help="Lets you separate the generation provider from the provider used for embeddings and retrieval.",
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
            "Embedding model",
            embedding_options,
            index=embedding_options.index(embedding_model_current) if embedding_model_current in embedding_options else default_embedding_index,
            key=embedding_model_state_key,
            help="Changing the embedding model requires reindexing to keep the vector space consistent.",
        )
        selected_embedding_context_window = int(
            st.slider(
                "Embedding context window",
                min_value=256,
                max_value=65536,
                value=max(int(default_embedding_context_window), 256),
                step=256,
                key="phase5_sidebar_embedding_context_window",
                help="Value sent to Ollama's native embedding endpoint via `options.num_ctx`. If it changes, reindex to keep the index consistent.",
            )
        )
        selected_embedding_truncate = st.checkbox(
            "Allow truncation in embeddings",
            value=bool(default_embedding_truncate),
            key="phase5_sidebar_embedding_truncate",
            help="When enabled, the embedding provider may truncate long inputs if the backend supports it.",
        )
        if embedding_provider_unavailable_items:
            with st.expander("Embedding providers currently unavailable", expanded=False):
                for item in embedding_provider_unavailable_items:
                    provider_label = str(item.get("label") or item.get("provider_key") or "provider")
                    reason = str(item.get("reason") or "unavailable")
                    st.caption(f"- **{provider_label}** · disabled: {reason}")

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
                help="Controls chunk size for the next indexing run.",
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
                help="Controls chunk overlap for the next indexing run.",
            )
        )
        rag_top_k = int(
            st.slider(
                "Retrieval top-k",
                min_value=1,
                max_value=12,
                value=max(int(default_rag_top_k), 1),
                step=1,
                key="phase5_sidebar_rag_top_k",
                help="Number of chunks retrieved for each question.",
            )
        )
        selected_rerank_pool_size = int(
            st.slider(
                "Reranking pool",
                min_value=max(2, rag_top_k),
                max_value=32,
                value=max(int(default_rerank_pool_size), rag_top_k),
                step=1,
                key="phase5_sidebar_rerank_pool_size",
                help="Number of candidates considered before the final top-k cut after hybrid reranking.",
            )
        )
        selected_rerank_lexical_weight = float(
            st.slider(
                "Lexical weight in reranking",
                min_value=0.0,
                max_value=0.9,
                value=min(max(float(default_rerank_lexical_weight), 0.0), 0.9),
                step=0.05,
                key="phase5_sidebar_rerank_lexical_weight",
                help="Mix between vector score and lexical score in hybrid reranking. Higher values give more weight to textual matching.",
            )
        )
        loader_strategy_options = ["manual", "langchain_basic"]
        loader_strategy_labels = {
            "manual": "Local manual",
            "langchain_basic": "LangChain loaders (experimental)",
        }
        default_loader_strategy = (
            default_rag_loader_strategy
            if default_rag_loader_strategy in loader_strategy_options
            else "manual"
        )
        selected_loader_strategy = st.selectbox(
            "Loader strategy",
            loader_strategy_options,
            index=loader_strategy_options.index(default_loader_strategy),
            key="phase5_sidebar_loader_strategy",
            format_func=lambda key: loader_strategy_labels[key],
            help="Phase 5.5 micro-slice: uses basic LangChain ecosystem loaders for TXT/CSV/MD/PY when the optional package is available. PDFs still use the project's custom pipeline.",
        )
        chunking_strategy_options = ["manual", "langchain_recursive"]
        chunking_strategy_labels = {
            "manual": "Local manual",
            "langchain_recursive": "LangChain Recursive (experimental)",
        }
        default_chunking_strategy = (
            default_rag_chunking_strategy
            if default_rag_chunking_strategy in chunking_strategy_options
            else "manual"
        )
        selected_chunking_strategy = st.selectbox(
            "Chunking strategy",
            chunking_strategy_options,
            index=chunking_strategy_options.index(default_chunking_strategy),
            key="phase5_sidebar_chunking_strategy",
            format_func=lambda key: chunking_strategy_labels[key],
            help="First Phase 5.5 slice: lets you test manual chunking vs a LangChain-compatible splitter when the optional package is available.",
        )
        retrieval_strategy_options = ["manual_hybrid", "langchain_chroma"]
        retrieval_strategy_labels = {
            "manual_hybrid": "Manual hybrid",
            "langchain_chroma": "LangChain + Chroma (experimental)",
        }
        default_retrieval_strategy = (
            default_rag_retrieval_strategy
            if default_rag_retrieval_strategy in retrieval_strategy_options
            else "manual_hybrid"
        )
        selected_retrieval_strategy = st.selectbox(
            "Retrieval strategy",
            retrieval_strategy_options,
            index=retrieval_strategy_options.index(default_retrieval_strategy),
            key="phase5_sidebar_retrieval_strategy",
            format_func=lambda key: retrieval_strategy_labels[key],
            help="Second Phase 5.5 slice: lets you compare the current manual retrieval path with an experimental LangChain + Chroma route.",
        )

        st.divider()
        st.subheader("PDF / OCR / Vision")
        selected_pdf_extraction_mode = st.selectbox(
            "PDF extraction",
            pdf_mode_options,
            index=pdf_mode_options.index(default_pdf_mode),
            key="phase5_sidebar_pdf_extraction_mode",
            format_func=lambda key: pdf_mode_labels[key],
            help="Basic = pypdf. Hybrid = fast with selective enrichment. Complete = page-by-page Docling/OCR with maximum coverage and higher cost.",
        )
        ocr_backend_options = ["ocrmypdf", "docling"]
        ocr_backend_labels = {
            "ocrmypdf": "OCRMyPDF",
            "docling": "Docling",
        }
        selected_ocr_backend = st.selectbox(
            "Document OCR backend",
            ocr_backend_options,
            index=ocr_backend_options.index(default_ocr_backend) if default_ocr_backend in ocr_backend_options else 0,
            key="phase5_sidebar_ocr_backend",
            format_func=lambda key: ocr_backend_labels.get(key, key),
            help="Preferred backend for the document/evidence path when OCR is needed.",
        )
        selected_vl_model = (
            st.text_input(
                "Document VLM model",
                value=default_vl_model,
                key="phase5_sidebar_vlm_model",
                help="Vision model used by the document path in cases that require visual/regional document reading.",
            ).strip()
            or default_vl_model
        )
        debug_retrieval = st.checkbox(
            "Show retrieval debug",
            value=False,
            key="phase5_sidebar_debug_retrieval",
            help="Shows details about retrieved chunks, scores, active RAG parameters, and a shadow comparison with the alternative retrieval strategy.",
        )

        clear_requested = st.button("🧹 Clear conversation", width="stretch")

        st.divider()
        st.metric("Messages in conversation", messages_count)
        if last_latency is not None:
            st.metric("Last response", f"{last_latency:.2f}s")

        detail = provider_details.get(selected_provider)
        if detail:
            st.caption(detail)
        if selected_provider == "huggingface_server":
            st.caption(
                "The models shown for this provider are aliases published by the service. The real backend may be Ollama, MLX, GGUF, OpenAI, or another runtime supported by the hub."
            )
        if selected_provider in context_window_supported_providers:
            if context_window_mode == "auto":
                st.caption(f"Active context in {provider_options.get(selected_provider, selected_provider)}: `auto`")
            else:
                st.caption(f"Active context in {provider_options.get(selected_provider, selected_provider)}: `{context_window}`")
        st.caption(
            f"Active embeddings: {embedding_provider_options.get(selected_embedding_provider, selected_embedding_provider)} · {selected_embedding_model} · num_ctx={selected_embedding_context_window} · truncate={selected_embedding_truncate}"
        )
        st.caption(
            f"Current RAG: {indexed_documents_count} document(s) · {indexed_chunks_count} chunks · top-k={rag_top_k} · overlap={rag_chunk_overlap} · rerank_pool={selected_rerank_pool_size} · lexical_weight={selected_rerank_lexical_weight:.2f}"
        )
        st.caption(f"Active loader: {loader_strategy_labels[selected_loader_strategy]}")
        st.caption(f"Active chunking: {chunking_strategy_labels[selected_chunking_strategy]}")
        st.caption(f"Active retrieval: {retrieval_strategy_labels[selected_retrieval_strategy]}")
        st.caption(f"Active PDF extraction: {pdf_mode_labels[selected_pdf_extraction_mode]}")
        st.caption(f"Document OCR: {ocr_backend_labels.get(selected_ocr_backend, selected_ocr_backend)}")
        st.caption(f"Document VLM: {selected_vl_model}")
        st.caption("Active pipeline: vector retrieval + hybrid reranking + prompt context budget.")
        st.caption(f"Local history: `{history_filename}`")
        st.caption(prompt_profiles[selected_prompt_profile]["description"])
        st.info("Advanced RAG (Document Base): Phase 4.5 active.")

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
        st.subheader("Operational map")

        provider_path = snapshot.get("provider_path")
        local_dependency = snapshot.get("local_dependency")
        if provider_path:
            st.caption(f"Active route: {provider_path}")
        if local_dependency:
            st.caption(str(local_dependency))

        chat = snapshot.get("chat")
        if isinstance(chat, dict):
            with st.expander("Chat with RAG", expanded=False):
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
                        "last_context_chars": chat.get("last_context_chars"),
                        "last_prompt_context_used_chunks": chat.get("last_prompt_context_used_chunks"),
                        "last_prompt_context_dropped_chunks": chat.get("last_prompt_context_dropped_chunks"),
                        "last_prompt_context_truncated": chat.get("last_prompt_context_truncated"),
                        "last_total_tokens": chat.get("last_total_tokens"),
                        "last_cost_usd": chat.get("last_cost_usd"),
                        "budget_routing_mode": chat.get("budget_routing_mode"),
                        "budget_routing_reason": chat.get("budget_routing_reason"),
                        "budget_auto_degrade_applied": chat.get("budget_auto_degrade_applied"),
                        "budget_alert_status": chat.get("budget_alert_status"),
                        "budget_alerts": chat.get("budget_alerts"),
                        "provider_requested": chat.get("provider_requested"),
                        "provider_effective": chat.get("provider_effective"),
                    }
                )
                if str(chat.get("budget_alert_status") or "") == "warn":
                    st.warning("The latest chat triggered budget/runtime alerts. Review the details before repeating this pattern in local production.")

        structured = snapshot.get("structured")
        if isinstance(structured, dict):
            with st.expander("Structured tasks", expanded=False):
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
                        "last_context_chars": structured.get("last_context_chars"),
                        "last_full_document_chars": structured.get("last_full_document_chars"),
                        "last_context_strategy": structured.get("last_context_strategy"),
                        "last_total_tokens": structured.get("last_total_tokens"),
                        "last_cost_usd": structured.get("last_cost_usd"),
                        "budget_routing_mode": structured.get("budget_routing_mode"),
                        "budget_routing_reason": structured.get("budget_routing_reason"),
                        "budget_auto_degrade_applied": structured.get("budget_auto_degrade_applied"),
                        "budget_alert_status": structured.get("budget_alert_status"),
                        "budget_alerts": structured.get("budget_alerts"),
                    }
                )
                if str(structured.get("budget_alert_status") or "") == "warn":
                    st.warning("The latest structured execution triggered budget/runtime alerts. Review the details before automating this flow.")
                task_model_map = structured.get("task_model_map")
                if isinstance(task_model_map, dict) and task_model_map:
                    st.caption("Effective model by task")
                    st.dataframe(
                        [
                            {"task": task_name, "model": model_name}
                            for task_name, model_name in task_model_map.items()
                        ],
                        width="stretch",
                    )

        documents = snapshot.get("documents")
        if isinstance(documents, dict):
            with st.expander("Documents / PDF / OCR / VL", expanded=False):
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
            with st.expander("Document Operations Copilot · aggregate history", expanded=False):
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
                    metric_col_2.metric("Success", _format_ratio(document_agent.get("success_rate")))
                    metric_col_3.metric("Needs review", _format_ratio(document_agent.get("needs_review_rate")))
                    metric_col_4.metric("Average confidence", _format_ratio(document_agent.get("avg_confidence")))
                    st.caption(
                        "This block summarizes the aggregated behavior of the document copilot: intents, tools, guardrails, and recent cases that required human review."
                    )

                    runs_with_tool_errors = int(document_agent.get("runs_with_tool_errors") or 0)
                    if runs_with_tool_errors:
                        st.warning(f"Runs with tool errors: {runs_with_tool_errors}")

                    for label, field_name, key_name in [
                        ("Distribution by intent", "intent_counts", "intent"),
                        ("Distribution by tool", "tool_counts", "tool"),
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
                        st.caption("Recent examples that required human review")
                        st.dataframe(needs_review_examples, width="stretch")

                    recent_entries = document_agent.get("recent_entries")
                    if isinstance(recent_entries, list) and recent_entries:
                        st.caption("Recent copilot runs")
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

        evidenceops = snapshot.get("evidenceops")
        if isinstance(evidenceops, dict) and evidenceops:
            with st.expander("EvidenceOps · operational worklog", expanded=False):
                st.write(
                    {
                        "log_path": evidenceops.get("log_path"),
                        "log_exists": evidenceops.get("log_exists"),
                        "entries_considered": evidenceops.get("entries_considered"),
                        "latest_timestamp": evidenceops.get("latest_timestamp"),
                    }
                )

                if evidenceops.get("log_exists") and int(evidenceops.get("total_runs") or 0) > 0:
                    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
                    metric_col_1.metric("Runs", int(evidenceops.get("total_runs") or 0))
                    metric_col_2.metric("Findings", int(evidenceops.get("total_findings") or 0))
                    metric_col_3.metric("Actions", int(evidenceops.get("total_action_items") or 0))
                    metric_col_4.metric("Needs review", _format_ratio(evidenceops.get("needs_review_rate")))
                    st.caption(
                        f"Average confidence: {_format_ratio(evidenceops.get('avg_confidence'))} · sources/run: {float(evidenceops.get('avg_source_count', 0.0)):.1f} · total recommendations: {int(evidenceops.get('total_recommended_actions') or 0)} · unique documents: {int(evidenceops.get('unique_document_count') or 0)}"
                    )

                    for label, field_name, key_name in [
                        ("Distribution by review type", "review_type_counts", "review_type"),
                        ("Distribution by tool", "tool_counts", "tool"),
                        ("Distribution by finding type", "finding_type_counts", "finding_type"),
                        ("Distribution by owner", "owner_counts", "owner"),
                        ("Distribution by status", "status_counts", "status"),
                        ("Distribution by due date", "due_date_counts", "due_date"),
                    ]:
                        rows = evidenceops.get(field_name)
                        if isinstance(rows, dict) and rows:
                            st.caption(label)
                            st.dataframe(
                                [{key_name: name, "count": count} for name, count in rows.items()],
                                width="stretch",
                            )

                    recent_entries = evidenceops.get("recent_entries")
                    if isinstance(recent_entries, list) and recent_entries:
                        st.caption("Recent worklog entries")
                        st.dataframe(
                            [
                                {
                                    "timestamp": entry.get("timestamp"),
                                    "review_type": entry.get("review_type"),
                                    "tool": entry.get("tool_used"),
                                    "findings": len(entry.get("findings") or []),
                                    "actions": len(entry.get("action_items") or []),
                                    "needs_review": entry.get("needs_review"),
                                    "query": entry.get("query"),
                                }
                                for entry in recent_entries[:10]
                                if isinstance(entry, dict)
                            ],
                            width="stretch",
                        )

        evidenceops_actions = snapshot.get("evidenceops_actions")
        if isinstance(evidenceops_actions, dict) and evidenceops_actions:
            with st.expander("EvidenceOps · local action store", expanded=False):
                st.write(
                    {
                        "store_path": evidenceops_actions.get("store_path"),
                        "store_exists": evidenceops_actions.get("store_exists"),
                        "entries_considered": evidenceops_actions.get("entries_considered"),
                        "latest_created_at": evidenceops_actions.get("latest_created_at"),
                    }
                )

                if evidenceops_actions.get("store_exists") and int(evidenceops_actions.get("total_actions") or 0) > 0:
                    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
                    metric_col_1.metric("Total actions", int(evidenceops_actions.get("total_actions") or 0))
                    metric_col_2.metric("Open actions", int(evidenceops_actions.get("open_actions") or 0))
                    metric_col_3.metric("Recommended", int(evidenceops_actions.get("recommended_actions") or 0))
                    metric_col_4.metric("Needs review", _format_ratio(evidenceops_actions.get("needs_review_rate")))
                    st.caption(
                        f"Actions with due date: {int(evidenceops_actions.get('actions_with_due_date') or 0)} · without owner: {int(evidenceops_actions.get('actions_without_owner') or 0)} · unique documents: {int(evidenceops_actions.get('unique_document_count') or 0)}"
                    )
                    governance_col_1, governance_col_2, governance_col_3, governance_col_4 = st.columns(4)
                    governance_col_1.metric("Review required", int(evidenceops_actions.get("review_required_actions") or 0))
                    governance_col_2.metric("Approved", int(evidenceops_actions.get("approved_actions") or 0))
                    governance_col_3.metric("Pending approval", int(evidenceops_actions.get("pending_approval_actions") or 0))
                    governance_col_4.metric("Overdue", int(evidenceops_actions.get("overdue_actions") or 0))
                    st.caption(
                        f"Open without owner: {int(evidenceops_actions.get('unassigned_open_actions') or 0)} · audited sensitive updates: {int(evidenceops_actions.get('sensitive_update_count') or 0)}"
                    )

                    for label, field_name, key_name in [
                        ("Distribution by action type", "action_type_counts", "action_type"),
                        ("Distribution by status", "status_counts", "status"),
                        ("Distribution by owner", "owner_counts", "owner"),
                        ("Distribution by review type", "review_type_counts", "review_type"),
                        ("Distribution by tool", "tool_counts", "tool"),
                    ]:
                        rows = evidenceops_actions.get(field_name)
                        if isinstance(rows, dict) and rows:
                            st.caption(label)
                            st.dataframe(
                                [{key_name: name, "count": count} for name, count in rows.items()],
                                width="stretch",
                            )

                    recent_entries = evidenceops_actions.get("recent_entries")
                    if isinstance(recent_entries, list) and recent_entries:
                        st.caption("Recent actions")
                        st.dataframe(
                            [
                                {
                                    "id": entry.get("id"),
                                    "created_at": entry.get("created_at"),
                                    "review_type": entry.get("review_type"),
                                    "action_type": entry.get("action_type"),
                                    "description": entry.get("description"),
                                    "owner": entry.get("owner"),
                                    "status": entry.get("status"),
                                    "due_date": entry.get("due_date"),
                                    "needs_review": entry.get("needs_review"),
                                }
                                for entry in recent_entries[:10]
                                if isinstance(entry, dict)
                            ],
                            width="stretch",
                        )

        evidenceops_repository = snapshot.get("evidenceops_repository")
        if isinstance(evidenceops_repository, dict) and evidenceops_repository:
            with st.expander("EvidenceOps · local document repository", expanded=False):
                st.write(
                    {
                        "repository_root": evidenceops_repository.get("repository_root"),
                        "repository_exists": evidenceops_repository.get("repository_exists"),
                        "snapshot_path": evidenceops_repository.get("snapshot_path"),
                        "entries_considered": evidenceops_repository.get("entries_considered"),
                        "latest_document": evidenceops_repository.get("latest_document"),
                    }
                )

                if evidenceops_repository.get("repository_exists") and int(evidenceops_repository.get("total_documents") or 0) > 0:
                    metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
                    metric_col_1.metric("Documents", int(evidenceops_repository.get("total_documents") or 0))
                    metric_col_2.metric("Categories", int(evidenceops_repository.get("total_categories") or 0))
                    metric_col_3.metric("Size (KB)", round(float(evidenceops_repository.get("total_size_bytes") or 0) / 1024, 1))
                    drift_summary = evidenceops_repository.get("drift_summary")
                    if isinstance(drift_summary, dict):
                        drift_col_1, drift_col_2, drift_col_3, drift_col_4 = st.columns(4)
                        drift_col_1.metric("New docs", int(drift_summary.get("new_documents_count") or 0))
                        drift_col_2.metric("Changed docs", int(drift_summary.get("changed_documents_count") or 0))
                        drift_col_3.metric("Removed docs", int(drift_summary.get("removed_documents_count") or 0))
                        drift_col_4.metric("Has drift", "Yes" if drift_summary.get("has_drift") else "No")
                        st.caption(
                            f"Previous snapshot: {drift_summary.get('previous_captured_at') or 'n/a'} · current: {drift_summary.get('current_captured_at') or 'n/a'}"
                        )

                    for label, field_name, key_name in [
                        ("Distribution by category", "category_counts", "category"),
                        ("Distribution by file type", "suffix_counts", "suffix"),
                    ]:
                        rows = evidenceops_repository.get(field_name)
                        if isinstance(rows, dict) and rows:
                            st.caption(label)
                            st.dataframe(
                                [{key_name: name, "count": count} for name, count in rows.items()],
                                width="stretch",
                            )

                    recent_documents = evidenceops_repository.get("recent_documents")
                    if isinstance(recent_documents, list) and recent_documents:
                        st.caption("Recent documents from the local corpus")
                        st.dataframe(recent_documents[:10], width="stretch")

                    for label, field_name in [
                        ("New documents detected since the last snapshot", "new_documents"),
                        ("Changed documents detected since the last snapshot", "changed_documents"),
                        ("Removed documents detected since the last snapshot", "removed_documents"),
                    ]:
                        rows = evidenceops_repository.get(field_name)
                        if isinstance(rows, list) and rows:
                            st.caption(label)
                            st.dataframe(rows[:10], width="stretch")

        runtime_execution = snapshot.get("runtime_execution")
        if isinstance(runtime_execution, dict) and runtime_execution:
            with st.expander("Observability · aggregate execution history", expanded=False):
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
                    metric_col_2.metric("Success", _format_ratio(runtime_execution.get("success_rate")))
                    metric_col_3.metric("Error", _format_ratio(runtime_execution.get("error_rate")))
                    metric_col_4.metric("Needs review", _format_ratio(runtime_execution.get("needs_review_rate")))

                    st.caption(
                        f"Average total latency: {float(runtime_execution.get('avg_latency_s', 0.0)):.2f}s · "
                        f"retrieval: {float(runtime_execution.get('avg_retrieval_latency_s', 0.0)):.2f}s · "
                        f"generation: {float(runtime_execution.get('avg_generation_latency_s', 0.0)):.2f}s · "
                        f"prompt build: {float(runtime_execution.get('avg_prompt_build_latency_s', 0.0)):.2f}s"
                    )
                    bottleneck_stage_counts = runtime_execution.get("bottleneck_stage_counts")
                    if isinstance(bottleneck_stage_counts, dict) and bottleneck_stage_counts:
                        st.caption(
                            f"Average latency share: retrieval={float(runtime_execution.get('avg_retrieval_share', 0.0)):.0%} · "
                            f"generation={float(runtime_execution.get('avg_generation_share', 0.0)):.0%} · "
                            f"prompt build={float(runtime_execution.get('avg_prompt_build_share', 0.0)):.0%} · "
                            f"other={float(runtime_execution.get('avg_other_latency_share', 0.0)):.0%} · "
                            f"average dominant bottleneck={float(runtime_execution.get('avg_bottleneck_share', 0.0)):.0%}"
                        )
                        st.caption("Dominant bottleneck by execution")
                        st.dataframe(
                            [
                                {"latency_stage": stage_name, "count": count}
                                for stage_name, count in bottleneck_stage_counts.items()
                            ],
                            width="stretch",
                        )
                    st.caption(
                        f"Average tokens: prompt={float(runtime_execution.get('avg_prompt_tokens', 0.0)):.1f} · "
                        f"completion={float(runtime_execution.get('avg_completion_tokens', 0.0)):.1f} · "
                        f"total={float(runtime_execution.get('avg_total_tokens', 0.0)):.1f}"
                    )
                    st.caption(
                        f"Docs/run: {float(runtime_execution.get('avg_selected_documents', 0.0)):.1f} · "
                        f"retrieved chunks/run: {float(runtime_execution.get('avg_retrieved_chunks_count', 0.0)):.1f} · "
                        f"average context pressure: {float(runtime_execution.get('avg_context_pressure_ratio', 0.0)):.2f} · "
                        f"auto-degrade: {_format_ratio(runtime_execution.get('auto_degrade_rate'))} · "
                        f"context truncation: {_format_ratio(runtime_execution.get('truncated_prompt_rate'))}"
                    )
                    costed_runs = int(runtime_execution.get("costed_runs") or 0)
                    if costed_runs > 0:
                        st.caption(
                            f"Estimated direct cost: total=${float(runtime_execution.get('total_cost_usd', 0.0)):.6f} · "
                            f"avg/run=${float(runtime_execution.get('avg_cost_usd', 0.0)):.6f} · runs with pricing={costed_runs}"
                        )
                    runtime_doc_metric_1, runtime_doc_metric_2, runtime_doc_metric_3, runtime_doc_metric_4 = st.columns(4)
                    runtime_doc_metric_1.metric("Evidence pipeline", int(runtime_execution.get("evidence_pipeline_runs") or 0))
                    runtime_doc_metric_2.metric("OCR involved", int(runtime_execution.get("ocr_involved_runs") or 0))
                    runtime_doc_metric_3.metric("Docling involved", int(runtime_execution.get("docling_involved_runs") or 0))
                    runtime_doc_metric_4.metric("VL involved", int(runtime_execution.get("vl_involved_runs") or 0))
                    mcp_metric_1, mcp_metric_2, mcp_metric_3, mcp_metric_4 = st.columns(4)
                    mcp_metric_1.metric("MCP runs", int(runtime_execution.get("mcp_runs") or 0))
                    mcp_metric_2.metric("MCP calls", int(runtime_execution.get("total_mcp_tool_calls") or 0))
                    mcp_metric_3.metric("MCP error", _format_ratio(runtime_execution.get("mcp_error_rate")))
                    mcp_metric_4.metric("MCP latency", f"{float(runtime_execution.get('avg_mcp_total_latency_s', 0.0)):.2f}s")
                    if int(runtime_execution.get("mcp_runs") or 0) > 0:
                        st.caption(
                            f"MCP read calls: {int(runtime_execution.get('total_mcp_read_calls') or 0)} · "
                            f"write calls: {int(runtime_execution.get('total_mcp_write_calls') or 0)} · "
                            f"average MCP calls/run: {float(runtime_execution.get('avg_mcp_tool_calls_per_run', 0.0)):.2f}"
                        )

                    for label, field_name, key_name in [
                        ("Distribution by flow", "flow_counts", "flow_type"),
                        ("Distribution by task", "task_counts", "task_type"),
                        ("Distribution by provider", "provider_counts", "provider"),
                        ("Distribution by model", "model_counts", "model"),
                        ("Distribution by usage source", "usage_source_counts", "usage_source"),
                        ("Distribution by cost source", "cost_source_counts", "cost_source"),
                        ("Distribution by budget mode", "budget_mode_counts", "budget_mode"),
                        ("Distribution by budget reason", "budget_reason_counts", "budget_reason"),
                        ("Distribution by context mode", "context_window_mode_counts", "context_window_mode"),
                        ("Distribution by OCR backend", "ocr_backend_counts", "ocr_backend"),
                        ("Distribution by MCP server", "mcp_server_counts", "mcp_server"),
                        ("Distribution by MCP tool", "mcp_tool_counts", "mcp_tool"),
                        ("Distribution by MCP transport", "mcp_transport_counts", "mcp_transport"),
                        ("Distribution by MCP status", "mcp_status_counts", "mcp_status"),
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
                        st.caption("Recent executions")
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
                                    "budget_mode": entry.get("budget_routing_mode"),
                                    "context_pressure_ratio": entry.get("context_pressure_ratio"),
                                    "mcp_status": entry.get("mcp_status"),
                                    "mcp_calls": entry.get("mcp_tool_call_count"),
                                    "mcp_latency_s": entry.get("mcp_total_latency_s"),
                                    "prompt_context_truncated": entry.get("prompt_context_truncated"),
                                    "ocr_docs": entry.get("ocr_document_count"),
                                    "docling_docs": entry.get("docling_document_count"),
                                    "vl_docs": entry.get("vl_document_count"),
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
            with st.expander("Evals / Phase 8.5 readiness", expanded=False):
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
                        "These signals help decide where to continue with prompt/RAG and where Phase 8.5 can focus on embeddings, rerankers, or light adaptation."
                    )
                    if global_recommendation:
                        st.info(global_recommendation)

                    suite_counts = evals.get("suite_counts")
                    if isinstance(suite_counts, dict) and suite_counts:
                        st.caption("Coverage by suite")
                        st.dataframe(
                            [
                                {"suite_name": name, "runs": count}
                                for name, count in suite_counts.items()
                            ],
                            width="stretch",
                        )

                    task_counts = evals.get("task_counts")
                    if isinstance(task_counts, dict) and task_counts:
                        st.caption("Coverage by task")
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
                        st.caption("Adaptation candidates")
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
                        st.caption("Next eval priorities")
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
                        st.caption("Healthy tasks (prompt + RAG seem sufficient)")
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
