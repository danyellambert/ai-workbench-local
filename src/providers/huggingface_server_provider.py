from __future__ import annotations

from openai import OpenAI

from src.config import HuggingFaceServerSettings


class HuggingFaceServerProvider:
    def __init__(self, settings: HuggingFaceServerSettings):
        self.settings = settings
        self.client = OpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key or "hf-server-local",
        )

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

    def inspect_context_window(self, model: str, requested_context_window: int | None = None) -> dict[str, object]:
        return {
            "runtime": "huggingface_server",
            "base_url": self.settings.base_url,
            "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
            "model": model,
            "validation_summary": (
                "O runtime Hugging Face via servidor local precisa expor um contrato HTTP compatível com chat completions. "
                "O valor configurado no app funciona como budget operacional, a menos que o seu servidor implemente controle explícito de contexto."
            ),
        }

    def inspect_embedding_context_window(self, model: str, requested_context_window: int | None = None) -> dict[str, object]:
        return {
            "runtime": "huggingface_server",
            "base_url": self.settings.base_url,
            "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
            "model": model,
            "validation_summary": (
                "Embeddings via servidor local dependem do contrato exposto pelo runtime externo. "
                "O app registra esse valor como metadado operacional e só tenta embeddings se um modelo de embedding estiver configurado."
            ),
        }

    def stream_chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        context_window: int | None = None,
    ):
        return self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
            stream=True,
        )

    def create_embeddings(
        self,
        texts: list[str],
        model: str,
        context_window: int | None = None,
        truncate: bool = True,
    ) -> list[list[float]]:
        response = self.client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in response.data]

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
        return (
            f"Não foi possível obter resposta do Hugging Face server local com o modelo `{model}`. "
            f"Base URL: `{self.settings.base_url}`. Detalhes: {error}"
        )
