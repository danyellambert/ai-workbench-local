from __future__ import annotations

import json
from urllib import request as urllib_request

from openai import OpenAI

from src.config import HuggingFaceServerSettings


class HuggingFaceServerProvider:
    def __init__(self, settings: HuggingFaceServerSettings):
        self.settings = settings
        self.client = OpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key or "hf-server-local",
        )
        self._catalog_cache: dict[str, object] | None = None
        self._last_usage_metrics: dict[str, object] = {}

    def reset_last_usage_metrics(self) -> None:
        self._last_usage_metrics = {}

    def get_last_usage_metrics(self) -> dict[str, object]:
        return dict(self._last_usage_metrics)

    def _catalog_url(self) -> str:
        return f"{self.settings.base_url.rstrip('/')}/models"

    def _native_base_url(self) -> str:
        normalized = self.settings.base_url.rstrip("/")
        if normalized.endswith("/v1"):
            normalized = normalized[:-3]
        return normalized

    def _fetch_catalog(self) -> dict[str, object] | None:
        if self._catalog_cache is not None:
            return self._catalog_cache
        try:
            with urllib_request.urlopen(self._catalog_url(), timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            self._catalog_cache = None
            return None
        self._catalog_cache = payload if isinstance(payload, dict) else None
        return self._catalog_cache

    def _catalog_entries(self) -> list[dict[str, object]]:
        payload = self._fetch_catalog()
        if not isinstance(payload, dict):
            return []
        if isinstance(payload.get("models"), list):
            return [item for item in payload.get("models") or [] if isinstance(item, dict)]
        if isinstance(payload.get("data"), list):
            return [item for item in payload.get("data") or [] if isinstance(item, dict)]
        return []

    @staticmethod
    def _catalog_model_name(item: dict[str, object]) -> str | None:
        for key in ("alias", "name", "id", "model_ref"):
            value = str(item.get(key) or "").strip()
            if value:
                return value
        return None

    def _catalog_chat_models(self) -> list[str]:
        ordered_models: list[str] = []
        for item in self._catalog_entries():
            if item.get("supports_chat") is False:
                continue
            model_name = self._catalog_model_name(item)
            if model_name and model_name not in ordered_models:
                ordered_models.append(model_name)
        return ordered_models

    def _catalog_embedding_models(self) -> list[str]:
        ordered_models: list[str] = []
        for item in self._catalog_entries():
            if item.get("supports_embeddings") is False:
                continue
            if item.get("supports_embeddings") is None and item.get("supports_chat") is not None:
                continue
            model_name = self._catalog_model_name(item)
            if model_name and model_name not in ordered_models:
                ordered_models.append(model_name)
        return ordered_models

    @staticmethod
    def _extract_declared_context_length(show_payload: dict[str, object]) -> int | None:
        model_info = show_payload.get("model_info")
        if not isinstance(model_info, dict):
            return None
        for key in ("context_length", "llama.context_length", "qwen2.context_length"):
            value = model_info.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
        for key, value in model_info.items():
            if "context" not in str(key).lower():
                continue
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
        return None

    def _post_native_json_request(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        request = urllib_request.Request(
            url=f"{self._native_base_url()}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def list_available_models(self) -> list[str]:
        ordered_models: list[str] = []
        for model in [self.settings.model, *self._catalog_chat_models(), *self.settings.available_models_env]:
            if model and model not in ordered_models:
                ordered_models.append(model)
        return ordered_models

    def list_available_embedding_models(self) -> list[str]:
        ordered_models: list[str] = []
        for model in [self.settings.embedding_model, *self._catalog_embedding_models(), *self.settings.available_embedding_models_env]:
            if model and model not in ordered_models:
                ordered_models.append(model)
        return ordered_models

    def inspect_context_window(self, model: str, requested_context_window: int | None = None) -> dict[str, object]:
        try:
            show_payload = self._post_native_json_request("/api/show", {"model": model})
            return {
                "runtime": "huggingface_server",
                "base_url": self.settings.base_url,
                "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
                "model": model,
                "show_available": True,
                "declared_context_length": self._extract_declared_context_length(show_payload),
                "backend_provider": (show_payload.get("model_info") or {}).get("hf_local_llm_service.provider") if isinstance(show_payload.get("model_info"), dict) else None,
                "backend_model_ref": (show_payload.get("model_info") or {}).get("hf_local_llm_service.model_ref") if isinstance(show_payload.get("model_info"), dict) else None,
                "validation_summary": "O serviço expõe `/api/show`, então o app consegue inspecionar o contexto declarado do alias/modelo do hub.",
            }
        except Exception:
            pass
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
        try:
            show_payload = self._post_native_json_request("/api/show", {"model": model})
            return {
                "runtime": "huggingface_server",
                "base_url": self.settings.base_url,
                "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
                "model": model,
                "show_available": True,
                "declared_context_length": self._extract_declared_context_length(show_payload),
                "supports_embeddings": (show_payload.get("model_info") or {}).get("hf_local_llm_service.supports_embeddings") if isinstance(show_payload.get("model_info"), dict) else None,
                "backend_provider": (show_payload.get("model_info") or {}).get("hf_local_llm_service.provider") if isinstance(show_payload.get("model_info"), dict) else None,
                "backend_model_ref": (show_payload.get("model_info") or {}).get("hf_local_llm_service.model_ref") if isinstance(show_payload.get("model_info"), dict) else None,
                "validation_summary": "O serviço expõe `/api/show`, então o app consegue inspecionar se o alias/modelo do hub suporta embeddings.",
            }
        except Exception:
            pass
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
        top_p: float | None = None,
        max_tokens: int | None = None,
        think: bool | None = None,
    ):
        self.reset_last_usage_metrics()
        provider_config: dict[str, object] = {"temperature": temperature}
        resolved_top_p = top_p if top_p is not None else self.settings.default_top_p
        resolved_max_tokens = max_tokens if max_tokens is not None else self.settings.default_max_tokens
        if context_window:
            provider_config["ctx_size"] = int(context_window)
        if resolved_top_p is not None:
            provider_config["top_p"] = float(resolved_top_p)
        if resolved_max_tokens is not None:
            provider_config["max_tokens"] = int(resolved_max_tokens)
        request_kwargs: dict[str, object] = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if provider_config:
            request_kwargs["extra_body"] = {"provider_config": provider_config}
        return self.client.chat.completions.create(
            **request_kwargs,
        )

    def create_embeddings(
        self,
        texts: list[str],
        model: str,
        context_window: int | None = None,
        truncate: bool = True,
    ) -> list[list[float]]:
        provider_config: dict[str, object] = {"truncate": bool(truncate)}
        if context_window:
            provider_config["ctx_size"] = int(context_window)
        request_kwargs: dict[str, object] = {
            "model": model,
            "input": texts,
        }
        if provider_config:
            request_kwargs["extra_body"] = {"provider_config": provider_config}
        response = self.client.embeddings.create(**request_kwargs)
        return [item.embedding for item in response.data]

    def iter_stream_text(self, stream):
        for chunk in stream:
            usage = getattr(chunk, "usage", None)
            if usage is not None:
                self._last_usage_metrics = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                    "usage_source": "huggingface_server_native_usage",
                }
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
