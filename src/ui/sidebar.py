import streamlit as st


def render_chat_sidebar(
    models: list[str],
    default_model: str,
    default_temperature: float,
    base_url: str,
    history_filename: str,
    messages_count: int,
    last_latency: float | None,
) -> tuple[str, float, bool]:
    default_index = models.index(default_model) if default_model in models else 0

    with st.sidebar:
        st.header("Configurações")
        selected_model = st.selectbox("Modelo local", models, index=default_index)
        temperature = st.slider(
            "Temperatura",
            min_value=0.0,
            max_value=1.5,
            value=min(max(default_temperature, 0.0), 1.5),
            step=0.1,
        )

        clear_requested = st.button("🧹 Limpar conversa", use_container_width=True)

        st.divider()
        st.metric("Mensagens na conversa", messages_count)
        if last_latency is not None:
            st.metric("Última resposta", f"{last_latency:.2f}s")

        st.caption(f"Base URL: `{base_url}`")
        st.caption(f"Histórico local: `{history_filename}`")
        st.info("Chat com documentos entra na Fase 4 do roadmap.")

    return selected_model, temperature, clear_requested