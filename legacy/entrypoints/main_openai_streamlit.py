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
ai_model = create_openai_client(settings)

st.write("# AI Chatbot - OpenAI-Compatible App")

if not settings.api_key:
    st.info("Set OPENAI_API_KEY in the .env file to use this OpenAI-compatible version.")

initialize_chat_state()

user_text = st.chat_input("Type your message")
uploaded_file = st.file_uploader("Select a file")

for message in get_chat_messages():
    role = message["role"]
    content = message["content"]
    st.chat_message(role).write(content)

if user_text:
    st.chat_message("user").write(user_text)
    append_chat_message("user", user_text)

    if ai_model is None:
        ai_response_text = "Configure OPENAI_API_KEY in the .env file to use the OpenAI-compatible chatbot."
    else:
        try:
            ai_response = create_openai_response(
                client=ai_model,
                messages=get_chat_messages(),
                model=settings.model,
            )
            ai_response_text = ai_response.choices[0].message.content
        except Exception as error:
            logger.exception("OpenAI-compatible chat request failed")
            ai_response_text = format_openai_error(error)

    st.chat_message("assistant").write(ai_response_text)
    append_chat_message("assistant", ai_response_text)
