from __future__ import annotations

from openai import OpenAI

from src.config import HuggingFaceInferenceSettings


class HuggingFaceInferenceProvider:
    def __init__(self, settings: HuggingFaceInferenceSettings):
        self.settings = settings
        self.client = OpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key,
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
            "runtime": "huggingface_inference",
            "base_url": self.settings.base_url,
            "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
            "model": model,
            "validation_summary": (
                "O Hugging Face Inference depende do endpoint remoto configurado na sua conta. "
                "Para chat funcionar bem aqui, o ideal é usar um endpoint compatível com chat completions/OpenAI-style."
            ),
        }

    def inspect_embedding_context_window(self, model: str, requested_context_window: int | None = None) -> dict[str, object]:
        return {
            "runtime": "huggingface_inference",
            "base_url": self.settings.base_url,
            "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
            "model": model,
            "validation_summary": (
                "Embeddings via Hugging Face Inference dependem do endpoint/modelo configurado. "
                "O app registra esse valor como metadado operacional e só usa embeddings se você configurar explicitamente esse caminho."
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
    ):
        request_kwargs: dict[str, object] = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "stream": True,
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
            f"Não foi possível obter resposta do Hugging Face Inference com o modelo `{model}`. "
            f"Base URL: `{self.settings.base_url}`. Detalhes: {error}"
        )
