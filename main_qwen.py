import time

import streamlit as st
from src.config import get_ollama_settings
from src.prompt_profiles import build_prompt_messages, get_prompt_profiles
from src.providers.registry import build_provider_registry
from src.services.chat_state import (
    append_chat_message,
    clear_chat_state,
    get_chat_messages,
    get_last_latency,
    initialize_chat_state,
    set_last_latency,
)
from src.storage.chat_history import clear_chat_history, load_chat_history, save_chat_history
from src.ui.chat import render_chat_message
from src.ui.sidebar import render_chat_sidebar


settings = get_ollama_settings()
provider_registry = build_provider_registry()
prompt_profiles = get_prompt_profiles()

initialize_chat_state(load_chat_history(settings.history_path))

messages = get_chat_messages()
last_latency = get_last_latency()

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

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            inicio = time.perf_counter()
            stream = selected_provider_instance.stream_chat_completion(
                messages=build_prompt_messages(selected_prompt_profile, get_chat_messages()),
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
    }
    append_chat_message("assistant", texto_resposta_ia, metadata=assistant_metadata)
    save_chat_history(settings.history_path, get_chat_messages())
