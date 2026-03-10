import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def criar_cliente_openai():
    if not OPENAI_API_KEY:
        return None
    return OpenAI(api_key=OPENAI_API_KEY)


modelo_ia = criar_cliente_openai()

st.write("# Chatbot com IA - OpenAI")

if not OPENAI_API_KEY:
    st.info("Defina OPENAI_API_KEY no arquivo .env para usar esta versão com a OpenAI.")

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

    if modelo_ia is None:
        texto_resposta_ia = "Configure OPENAI_API_KEY no arquivo .env para usar o chatbot com OpenAI."
    else:
        try:
            resposta_ia = modelo_ia.chat.completions.create(
                messages=st.session_state["lista_mensagens"],
                model=OPENAI_MODEL,
            )
            texto_resposta_ia = resposta_ia.choices[0].message.content
        except Exception as erro:
            texto_resposta_ia = f"Erro ao chamar a OpenAI: {erro}"

    st.chat_message("assistant").write(texto_resposta_ia)
    mensagem_ia = {"role": "assistant", "content": texto_resposta_ia}
    st.session_state["lista_mensagens"].append(mensagem_ia)