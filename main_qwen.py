import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

PROJECT_NAME = os.getenv("PROJECT_NAME", "AI Workbench Local")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

modelo_ia = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
)

st.write(f"# {PROJECT_NAME}")
st.caption(f"Modelo local atual: `{OLLAMA_MODEL}`")

if "lista_mensagens" not in st.session_state:
    st.session_state["lista_mensagens"] = []

texto_usuario = st.chat_input("Digite sua mensagem")
arquivo = st.file_uploader("Selecione um arquivo")

for mensagem in st.session_state["lista_mensagens"]:
    role = mensagem["role"]
    content = mensagem["content"]
    st.chat_message(role).write(content)

if texto_usuario:
    st.chat_message("user").write(texto_usuario)
    mensagem_usuario = {"role": "user", "content": texto_usuario}
    st.session_state["lista_mensagens"].append(mensagem_usuario)

    try:
        resposta_ia = modelo_ia.chat.completions.create(
            messages=st.session_state["lista_mensagens"],
            model=OLLAMA_MODEL,
        )
        texto_resposta_ia = resposta_ia.choices[0].message.content
    except Exception as erro:
        texto_resposta_ia = (
            "Não foi possível obter resposta do Ollama. "
            "Verifique se o servidor está ativo e se o modelo está instalado.\n\n"
            f"Detalhes: {erro}"
        )

    st.chat_message("assistant").write(texto_resposta_ia)
    mensagem_ia = {"role": "assistant", "content": texto_resposta_ia}
    st.session_state["lista_mensagens"].append(mensagem_ia)
