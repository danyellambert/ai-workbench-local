import streamlit as st


RAG_INDEX_KEY = "rag_index"


def initialize_rag_state(initial_index: dict[str, object] | None = None) -> None:
    if RAG_INDEX_KEY not in st.session_state:
        st.session_state[RAG_INDEX_KEY] = initial_index


def get_rag_index() -> dict[str, object] | None:
    return st.session_state.get(RAG_INDEX_KEY)


def set_rag_index(index: dict[str, object] | None) -> None:
    st.session_state[RAG_INDEX_KEY] = index


def clear_rag_state() -> None:
    st.session_state[RAG_INDEX_KEY] = None