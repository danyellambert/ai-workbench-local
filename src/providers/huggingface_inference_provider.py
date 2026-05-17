from __future__ import annotations

from typing import Iterable

from huggingface_hub import InferenceClient
from openai import OpenAI

from src.config import HuggingFaceInferenceSettings


class HuggingFaceInferenceProvider:
    EMBEDDING_FALLBACK_MODELS = (
        "BAAI/bge-small-en-v1.5",
        "sentence-transformers/all-MiniLM-L6-v2",
        "thenlper/gte-large",
        "google/embeddinggemma-300m",
    )

    def __init__(self, settings: HuggingFaceInferenceSettings):
        self.settings = settings
        self.client = OpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key,
        )
        self.embedding_client = self._build_embedding_client(settings.api_key)
        self._last_usage_metrics: dict[str, object] = {}

    @staticmethod
    def _build_embedding_client(api_key: str | None) -> InferenceClient:
        try:
            return InferenceClient(provider="hf-inference", api_key=api_key)
        except TypeError:
            return InferenceClient(api_key=api_key)

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
        for model in [self.settings.embedding_model, *self.settings.available_embedding_models_env, *self.EMBEDDING_FALLBACK_MODELS]:
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
                "Hugging Face Inference depends on the remote endpoint configured in your account. "
                "For chat to work well here, the ideal setup is an endpoint compatible with chat completions/OpenAI-style APIs."
            ),
        }

    def inspect_embedding_context_window(self, model: str, requested_context_window: int | None = None) -> dict[str, object]:
        return {
            "runtime": "huggingface_inference",
            "base_url": self.settings.base_url,
            "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
            "model": model,
            "validation_summary": (
                "Embeddings through Hugging Face Inference depend on the configured endpoint/model. "
                "The app records this value as operational metadata and only uses embeddings if you explicitly configure that path."
            ),
        }

    def _iter_embedding_candidates(self, requested_model: str | None = None) -> Iterable[str]:
        ordered: list[str] = []
        for model in [requested_model, self.settings.embedding_model, *self.settings.available_embedding_models_env, *self.EMBEDDING_FALLBACK_MODELS]:
            normalized = str(model or "").strip()
            if normalized and normalized not in ordered:
                ordered.append(normalized)
        return ordered

    def _create_embedding_once(self, text: str, model: str, *, truncate: bool = True) -> list[float]:
        embedding = self.embedding_client.feature_extraction(
            text,
            model=model,
            truncate=truncate,
        )
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()
        if isinstance(embedding, list) and embedding and isinstance(embedding[0], list):
            embedding = embedding[0]
        return [float(value) for value in embedding]

    @staticmethod
    def _looks_like_missing_embedding_route(error: Exception) -> bool:
        message = str(error).lower()
        return (
            "404" in message
            or "not found" in message
            or "feature-extraction" in message
            or "does not seem to support" in message
            or "task not found" in message
        )

    def probe_connection(self) -> dict[str, object]:
        if not self.settings.api_key:
            return {"status": "not_configured", "last_error_message": "A Hugging Face token is required for this connection."}

        embedding_errors: list[str] = []
        for index, embedding_model in enumerate(self._iter_embedding_candidates()):
            try:
                self._create_embedding_once("health check", embedding_model)
                if index == 0:
                    return {"status": "connected", "last_error_message": None}
                return {
                    "status": "connected",
                    "last_error_message": f"Preferred embedding model was unavailable; using `{embedding_model}` as the first working fallback for probe/embedding routing.",
                }
            except Exception as error:
                embedding_errors.append(f"`{embedding_model}`: {error}")
                if not self._looks_like_missing_embedding_route(error):
                    break

        chat_model = self.settings.model or (self.settings.available_models_env[0] if self.settings.available_models_env else "")
        if chat_model:
            try:
                self.client.chat.completions.create(
                    model=chat_model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=1,
                    temperature=0,
                    stream=False,
                )
                return {
                    "status": "degraded",
                    "last_error_message": "Chat is reachable, but no embedding model probe succeeded. " + (" Last embedding error: " + embedding_errors[-1] if embedding_errors else ""),
                }
            except Exception as error:
                return {
                    "status": "degraded",
                    "last_error_message": f"Chat probe failed for `{chat_model}`. Details: {error}",
                }

        if embedding_errors:
            return {
                "status": "degraded",
                "last_error_message": "No Hugging Face Inference embedding model probe succeeded. " + " Last tried: " + embedding_errors[-1],
            }

        return {
            "status": "degraded",
            "last_error_message": "Token saved, but no chat or embedding model is configured for Hugging Face Inference yet.",
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
        normalized_model = str(model or self.settings.embedding_model or "").strip()
        candidates = list(self._iter_embedding_candidates(normalized_model))
        if not candidates:
            raise ValueError("No Hugging Face Inference embedding model is configured.")

        errors: list[str] = []
        for candidate in candidates:
            try:
                vectors = [self._create_embedding_once(text, candidate, truncate=truncate) for text in texts]
                self._last_usage_metrics = {
                    "embedding_model_requested": normalized_model or candidate,
                    "embedding_model_used": candidate,
                    "usage_source": "huggingface_inference_feature_extraction",
                    "embedding_model_fallback_applied": candidate != (normalized_model or candidate),
                }
                return vectors
            except Exception as error:
                errors.append(f"`{candidate}`: {error}")
                if not self._looks_like_missing_embedding_route(error):
                    break

        requested_label = normalized_model or candidates[0]
        detail = errors[-1] if errors else "unknown embedding error"
        raise RuntimeError(
            f"No Hugging Face Inference embedding model could be used. Requested `{requested_label}`. Last error: {detail}"
        )

    def iter_stream_text(self, stream):
        for chunk in stream:
            usage = getattr(chunk, "usage", None)
            if usage is not None:
                self._last_usage_metrics = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                    "usage_source": "huggingface_inference_native_usage",
                }
            if not getattr(chunk, "choices", None):
                continue
            delta = getattr(chunk.choices[0], "delta", None)
            content = getattr(delta, "content", None) or ""
            if content:
                yield content

    def format_error(self, model: str, error: Exception) -> str:
        return (
            f"Could not get a response from Hugging Face Inference using model `{model}`. "
            f"Base URL: `{self.settings.base_url}`. Details: {error}"
        )
