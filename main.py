import streamlit as st
from src.config import get_openai_settings
from src.providers.openai_provider import (
    create_openai_client,
    create_openai_response,
    format_openai_error,
)
from src.services.app_logging import configure_logging, get_logger
from src.services.chat_state import append_chat_message, get_chat_messages, initialize_chat_state


configure_logging()
logger = get_logger(__name__)

settings = get_openai_settings()
modelo_ia = create_openai_client(settings)

st.write("# Chatbot com IA - OpenAI")

if not settings.api_key:
    st.info("Defina OPENAI_API_KEY no arquivo .env para usar esta versão com a OpenAI.")

initialize_chat_state()

texto_usuario = st.chat_input("Digite sua mensagem")
arquivo = st.file_uploader("Selecione um arquivo")

for mensagem in get_chat_messages():
    role = mensagem["role"]
    content = mensagem["content"]
    st.chat_message(role).write(content)

if texto_usuario:
    st.chat_message("user").write(texto_usuario)
    append_chat_message("user", texto_usuario)

    if modelo_ia is None:
        texto_resposta_ia = "Configure OPENAI_API_KEY no arquivo .env para usar o chatbot com OpenAI."
    else:
        try:
            resposta_ia = create_openai_response(
                client=modelo_ia,
                messages=get_chat_messages(),
                model=settings.model,
            )
            texto_resposta_ia = resposta_ia.choices[0].message.content
        except Exception as erro:
            logger.exception("OpenAI-compatible chat request failed")
            texto_resposta_ia = format_openai_error(erro)

    st.chat_message("assistant").write(texto_resposta_ia)
    append_chat_message("assistant", texto_resposta_ia)