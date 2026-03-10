from openai import OpenAI

from src.config import OpenAISettings


def create_openai_client(settings: OpenAISettings):
    if not settings.api_key:
        return None
    return OpenAI(api_key=settings.api_key)


def create_openai_response(client: OpenAI, messages: list[dict[str, str]], model: str):
    return client.chat.completions.create(messages=messages, model=model)


def format_openai_error(error: Exception) -> str:
    return f"Erro ao chamar a OpenAI: {error}"