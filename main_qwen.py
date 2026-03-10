import time

import streamlit as st
from src.config import get_ollama_settings
from src.providers.ollama_provider import OllamaProvider
from src.services.chat_state import (
    append_chat_message,
    clear_chat_state,
    get_chat_messages,
    get_last_latency,
    initialize_chat_state,
    set_last_latency,
)
from src.storage.chat_history import clear_chat_history, load_chat_history, save_chat_history
from src.ui.sidebar import render_chat_sidebar


settings = get_ollama_settings()
provider = OllamaProvider(settings)

initialize_chat_state(load_chat_history(settings.history_path))

available_models = provider.list_available_models()
messages = get_chat_messages()
last_latency = get_last_latency()

selected_model, temperature, clear_requested = render_chat_sidebar(
    models=available_models,
    default_model=settings.default_model,
    default_temperature=settings.default_temperature,
    base_url=settings.base_url,
    history_filename=settings.history_path.name,
    messages_count=len(messages),
    last_latency=last_latency,
)

if clear_requested:
    clear_chat_state()
    clear_chat_history(settings.history_path)
    st.rerun()

st.write(f"# {settings.project_name}")
st.caption(
    f"Modelo atual: `{selected_model}` · Temperatura: `{temperature:.1f}` · Histórico salvo localmente"
)

for mensagem in messages:
    st.chat_message(mensagem["role"]).write(mensagem["content"])

texto_usuario = st.chat_input("Digite sua mensagem")

if texto_usuario:
    st.chat_message("user").write(texto_usuario)
    append_chat_message("user", texto_usuario)
    save_chat_history(settings.history_path, get_chat_messages())

    texto_resposta_ia = ""

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            inicio = time.perf_counter()
            stream = provider.stream_chat_completion(
                messages=get_chat_messages(),
                model=selected_model,
                temperature=temperature,
            )

            partes = []
            for token in provider.iter_stream_text(stream):
                partes.append(token)
                placeholder.markdown("".join(partes) + "▌")

            texto_resposta_ia = "".join(partes).strip() or "A resposta veio vazia."
            placeholder.markdown(texto_resposta_ia)

            latencia = time.perf_counter() - inicio
            set_last_latency(latencia)
            st.caption(f"Resposta em {latencia:.2f}s")
        except Exception as erro:
            set_last_latency(None)
            texto_resposta_ia = provider.format_error(selected_model, erro)
            placeholder.empty()
            st.error(texto_resposta_ia)

    append_chat_message("assistant", texto_resposta_ia)
    save_chat_history(settings.history_path, get_chat_messages())
