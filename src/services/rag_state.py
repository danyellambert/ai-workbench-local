import streamlit as st

from src.config import RagSettings


RAG_INDEX_KEY = "rag_index"
RAG_RUNTIME_SETTINGS_KEY = "rag_runtime_settings"


def initialize_rag_state(initial_index: dict[str, object] | None = None) -> None:
    if RAG_INDEX_KEY not in st.session_state:
        st.session_state[RAG_INDEX_KEY] = initial_index


def initialize_rag_runtime_settings(initial_settings: RagSettings | None = None) -> None:
    if RAG_RUNTIME_SETTINGS_KEY not in st.session_state:
        st.session_state[RAG_RUNTIME_SETTINGS_KEY] = initial_settings


def get_rag_index() -> dict[str, object] | None:
    return st.session_state.get(RAG_INDEX_KEY)


def set_rag_index(index: dict[str, object] | None) -> None:
    st.session_state[RAG_INDEX_KEY] = index


def clear_rag_state() -> None:
    st.session_state[RAG_INDEX_KEY] = None


def get_rag_runtime_settings() -> RagSettings | None:
    value = st.session_state.get(RAG_RUNTIME_SETTINGS_KEY)
    return value if isinstance(value, RagSettings) else None


def set_rag_runtime_settings(settings: RagSettings | None) -> None:
    st.session_state[RAG_RUNTIME_SETTINGS_KEY] = settings