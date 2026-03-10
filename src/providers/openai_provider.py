from openai import OpenAI

from src.config import OpenAISettings


class OpenAIProvider:
    def __init__(self, settings: OpenAISettings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.api_key) if settings.api_key else None

    def list_available_models(self) -> list[str]:
        ordered_models: list[str] = []
        for model in [self.settings.model, *self.settings.available_models_env]:
            if model and model not in ordered_models:
                ordered_models.append(model)
        return ordered_models

    def stream_chat_completion(self, messages: list[dict[str, str]], model: str, temperature: float):
        if self.client is None:
            raise RuntimeError("OPENAI_API_KEY não configurada")

        return self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
            stream=True,
        )

    @staticmethod
    def iter_stream_text(stream):
        for chunk in stream:
            if not getattr(chunk, "choices", None):
                continue

            delta = getattr(chunk.choices[0], "delta", None)
            content = getattr(delta, "content", None) or ""
            if content:
                yield content

    def format_error(self, model: str, error: Exception) -> str:
        return f"Não foi possível obter resposta do provider OpenAI com o modelo `{model}`. Detalhes: {error}"


def create_openai_client(settings: OpenAISettings):
    if not settings.api_key:
        return None
    return OpenAI(api_key=settings.api_key)


def create_openai_response(client: OpenAI, messages: list[dict[str, str]], model: str):
    return client.chat.completions.create(messages=messages, model=model)


def format_openai_error(error: Exception) -> str:
    return f"Erro ao chamar a OpenAI: {error}"