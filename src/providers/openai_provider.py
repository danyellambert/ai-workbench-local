from openai import OpenAI

from src.config import OpenAISettings


class OpenAIProvider:
    def __init__(self, settings: OpenAISettings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.api_key) if settings.api_key else None
        self._last_usage_metrics: dict[str, object] = {}

    def reset_last_usage_metrics(self) -> None:
        self._last_usage_metrics = {}

    def get_last_usage_metrics(self) -> dict[str, object]:
        return dict(self._last_usage_metrics)

    def list_available_models(self) -> list[str]:
        ordered_models: list[str] = []
        for model in [self.settings.model, *self.settings.available_models_env]:
            if model and model not in ordered_models:
                ordered_models.append(model)
        return ordered_models

    def list_available_embedding_models(self) -> list[str]:
        ordered_models: list[str] = []
        for model in [self.settings.embedding_model, *self.settings.available_embedding_models_env]:
            if model and model not in ordered_models:
                ordered_models.append(model)
        return ordered_models

    def inspect_embedding_context_window(self, model: str, requested_context_window: int | None = None) -> dict[str, object]:
        return {
            "api_route": "https://api.openai.com/v1/embeddings",
            "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
            "model": model,
            "validation_summary": (
                "OpenAI embeddings não expõem um controle equivalente a `num_ctx` do Ollama. "
                "O valor configurado no app fica registrado como metadado operacional, mas não é aplicado como janela de contexto explícita no provider OpenAI."
            ),
        }

    def stream_chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        context_window: int | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        think: bool | None = None,
    ):
        if self.client is None:
            raise RuntimeError("OPENAI_API_KEY não configurada")
        self.reset_last_usage_metrics()

        request_kwargs: dict[str, object] = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        resolved_top_p = top_p if top_p is not None else self.settings.default_top_p
        resolved_max_tokens = max_tokens if max_tokens is not None else self.settings.default_max_tokens
        if resolved_top_p is not None:
            request_kwargs["top_p"] = float(resolved_top_p)
        if resolved_max_tokens is not None:
            request_kwargs["max_tokens"] = int(resolved_max_tokens)

        return self.client.chat.completions.create(**request_kwargs)

    def create_embeddings(
        self,
        texts: list[str],
        model: str,
        context_window: int | None = None,
        truncate: bool = True,
    ) -> list[list[float]]:
        if self.client is None:
            raise RuntimeError("OPENAI_API_KEY não configurada")

        response = self.client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in response.data]

    def iter_stream_text(self, stream):
        for chunk in stream:
            usage = getattr(chunk, "usage", None)
            if usage is not None:
                self._last_usage_metrics = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                    "usage_source": "openai_native_usage",
                }
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