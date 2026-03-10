import streamlit as st


def render_chat_message(message: dict[str, object]) -> None:
    role = message.get("role", "assistant")
    content = message.get("content", "")
    metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}

    with st.chat_message(role):
        st.write(content)

        if metadata:
            info_parts = []
            provider_label = metadata.get("provider_label") or metadata.get("provider")
            model = metadata.get("model")
            profile_label = metadata.get("prompt_profile_label") or metadata.get("prompt_profile")
            temperature = metadata.get("temperature")
            latency = metadata.get("latency_s")

            if provider_label:
                info_parts.append(str(provider_label))
            if model:
                info_parts.append(str(model))
            if profile_label:
                info_parts.append(f"perfil: {profile_label}")
            if temperature is not None:
                info_parts.append(f"temp: {temperature}")
            if latency is not None:
                info_parts.append(f"latência: {latency}s")

            if info_parts:
                st.caption(" · ".join(info_parts))