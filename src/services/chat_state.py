import streamlit as st


MESSAGES_KEY = "lista_mensagens"
LATENCY_KEY = "ultima_latencia_s"


def initialize_chat_state(initial_messages: list[dict[str, str]] | None = None) -> None:
    if MESSAGES_KEY not in st.session_state:
        st.session_state[MESSAGES_KEY] = initial_messages or []

    if LATENCY_KEY not in st.session_state:
        st.session_state[LATENCY_KEY] = None


def get_chat_messages() -> list[dict[str, str]]:
    return st.session_state[MESSAGES_KEY]


def append_chat_message(role: str, content: str) -> dict[str, str]:
    message = {"role": role, "content": content}
    st.session_state[MESSAGES_KEY].append(message)
    return message


def clear_chat_state() -> None:
    st.session_state[MESSAGES_KEY] = []
    st.session_state[LATENCY_KEY] = None


def get_last_latency() -> float | None:
    return st.session_state.get(LATENCY_KEY)


def set_last_latency(value: float | None) -> None:
    st.session_state[LATENCY_KEY] = value