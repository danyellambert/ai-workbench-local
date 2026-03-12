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
    provider_details: dict[str, str],
    history_filename: str,
    messages_count: int,
    last_latency: float | None,
) -> tuple[str, str, str, float, int, bool]:
    provider_keys = list(provider_options.keys())
    default_provider_index = provider_keys.index(default_provider) if default_provider in provider_keys else 0

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
        if selected_provider == "ollama":
            context_window = int(
                st.number_input(
                    "Janela de contexto (num_ctx)",
                    min_value=1024,
                    max_value=65536,
                    value=max(int(context_window), 1024),
                    step=1024,
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

        clear_requested = st.button("🧹 Limpar conversa", width="stretch")

        st.divider()
        st.metric("Mensagens na conversa", messages_count)
        if last_latency is not None:
            st.metric("Última resposta", f"{last_latency:.2f}s")

        detail = provider_details.get(selected_provider)
        if detail:
            st.caption(detail)
        if selected_provider == "ollama":
            st.caption(f"Contexto ativo no Ollama: `{context_window}`")
        st.caption(f"Histórico local: `{history_filename}`")
        st.caption(prompt_profiles[selected_prompt_profile]["description"])
        st.info("Chat com documentos entra na Fase 4 do roadmap.")

    return selected_provider, selected_model, selected_prompt_profile, temperature, int(context_window), clear_requested