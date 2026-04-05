import json
import os
import re
import subprocess
from urllib import request as urllib_request
from urllib.parse import urlparse

from openai import OpenAI

from src.config import OllamaSettings


class OllamaProvider:
    FALLBACK_MODELS = [
        "qwen2.5-coder:7b",
        "qwen3.5:397b-cloud",
        "qwen3-coder:480b-cloud",
    ]
    FALLBACK_EMBEDDING_MODELS = [
        "bge-m3",
        "nomic-embed-text",
        "qwen3-embedding",
        "embeddinggemma",
    ]

    def __init__(self, settings: OllamaSettings):
        self.settings = settings
        self.client = OpenAI(base_url=settings.base_url, api_key="ollama")
        self.native_base_url = self._build_native_base_url(settings.base_url)
        self._last_usage_metrics: dict[str, object] = {}

    def reset_last_usage_metrics(self) -> None:
        self._last_usage_metrics = {}

    def get_last_usage_metrics(self) -> dict[str, object]:
        return dict(self._last_usage_metrics)

    @staticmethod
    def _build_native_base_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/v1"):
            normalized = normalized[:-3]
        return normalized

    def _discover_local_models(self) -> list[str]:
        discovered_via_api = self._discover_models_via_api()
        if discovered_via_api:
            return discovered_via_api

        discovered_models: list[str] = []
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines()[1:]:
                    parts = line.split()
                    if parts:
                        discovered_models.append(parts[0])
        except OSError:
            pass
        return discovered_models

    def _discover_models_via_api(self) -> list[str]:
        try:
            with urllib_request.urlopen(f"{self.native_base_url}/api/tags", timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        ordered_models: list[str] = []
        for item in payload.get("models") or []:
            if not isinstance(item, dict):
                continue
            model_name = str(item.get("name") or item.get("model_ref") or "").strip()
            if model_name and model_name not in ordered_models:
                ordered_models.append(model_name)
        return ordered_models

    def _should_use_native_cli_runtime_hints(self) -> bool:
        if os.getenv("OLLAMA_USE_NATIVE_CLI_HINTS", "true").strip().lower() in {"0", "false", "no", "off"}:
            return False
        parsed = urlparse(self.native_base_url)
        hostname = (parsed.hostname or "").strip().lower()
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return hostname in {"127.0.0.1", "localhost"} and port == 11434

    @staticmethod
    def _looks_like_embedding_model(model_name: str) -> bool:
        normalized = model_name.lower()
        return any(token in normalized for token in ["embed", "embedding", "bge", "minilm", "e5", "nomic", "mxbai"])

    def list_available_models(self) -> list[str]:
        discovered_models = self._discover_local_models()
        ordered_models: list[str] = []
        for model in [
            self.settings.default_model,
            *self.settings.available_models_env,
            *discovered_models,
            *self.FALLBACK_MODELS,
        ]:
            if model and model not in ordered_models:
                ordered_models.append(model)
        return ordered_models

    def list_available_embedding_models(self) -> list[str]:
        discovered_models = self._discover_local_models()
        ordered_models: list[str] = []
        for model in [
            *self.settings.available_embedding_models_env,
            *discovered_models,
            *self.FALLBACK_EMBEDDING_MODELS,
        ]:
            if model and self._looks_like_embedding_model(model) and model not in ordered_models:
                ordered_models.append(model)
        return ordered_models or self.FALLBACK_EMBEDDING_MODELS[:]

    def _native_json_request(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        request = urllib_request.Request(
            url=f"{self.native_base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        timeout_seconds = int(os.getenv("OLLAMA_HTTP_TIMEOUT_SECONDS", "300"))
        with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _extract_declared_context_length(show_payload: dict[str, object]) -> int | None:
        model_info = show_payload.get("model_info")
        if not isinstance(model_info, dict):
            return None

        preferred_keys = [
            "llama.context_length",
            "qwen2.context_length",
            "phi3.context_length",
            "mistral.context_length",
            "gemma.context_length",
            "bert.context_length",
            "context_length",
        ]
        for key in preferred_keys:
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

    @staticmethod
    def _read_ollama_ps_context(model: str) -> int | None:
        try:
            result = subprocess.run(
                ["ollama", "ps"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None

        if result.returncode != 0:
            return None

        for line in result.stdout.splitlines()[1:]:
            if not line.strip().startswith(model):
                continue

            columns = re.split(r"\s{2,}", line.strip())
            if len(columns) < 5:
                continue

            context_value = columns[4]
            digits = "".join(char for char in context_value if char.isdigit())
            if digits:
                return int(digits)
        return None

    def inspect_context_window(self, model: str, requested_context_window: int | None = None) -> dict[str, object]:
        output: dict[str, object] = {
            "api_route": f"{self.native_base_url}/api/chat",
            "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
            "model": model,
        }

        try:
            show_payload = self._native_json_request("/api/show", {"model": model})
            output["show_available"] = True
            output["declared_context_length"] = self._extract_declared_context_length(show_payload)
            modified_at = show_payload.get("modified_at")
            if modified_at:
                output["model_modified_at"] = modified_at
        except Exception as error:
            output["show_available"] = False
            output["show_error"] = str(error)

        if self._should_use_native_cli_runtime_hints():
            ps_context = self._read_ollama_ps_context(model)
            if ps_context is not None:
                output["ollama_ps_context"] = ps_context
        else:
            output["ollama_ps_context"] = None
            output["runtime_hint_source"] = "http-only"

        output["validation_summary"] = (
            "Use `/api/chat` para aplicar `num_ctx`, `/api/show` para ver o contexto declarado do modelo "
            "e `ollama ps` apenas como confirmação auxiliar de runtime."
        )
        return output

    def inspect_embedding_context_window(self, model: str, requested_context_window: int | None = None) -> dict[str, object]:
        output: dict[str, object] = {
            "api_route": f"{self.native_base_url}/api/embed",
            "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
            "model": model,
            "truncate": True,
        }
        try:
            show_payload = self._native_json_request("/api/show", {"model": model})
            output["show_available"] = True
            output["declared_context_length"] = self._extract_declared_context_length(show_payload)
            modified_at = show_payload.get("modified_at")
            if modified_at:
                output["model_modified_at"] = modified_at
        except Exception as error:
            output["show_available"] = False
            output["show_error"] = str(error)

        output["validation_summary"] = (
            "O endpoint nativo `/api/embed` aceita `truncate` e `options`. O app envia `options.num_ctx` como controle operacional "
            "da janela de embedding, mas o comportamento efetivo ainda depende do modelo e do runtime do Ollama."
        )
        return output

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
        resolved_top_p = top_p if top_p is not None else self.settings.default_top_p
        resolved_max_tokens = max_tokens if max_tokens is not None else self.settings.default_max_tokens
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }
        if think is not None:
            payload["think"] = bool(think)

        if context_window:
            payload["options"]["num_ctx"] = int(context_window)
        if resolved_top_p is not None:
            payload["options"]["top_p"] = float(resolved_top_p)
        if resolved_max_tokens is not None:
            payload["options"]["num_predict"] = int(resolved_max_tokens)

        request = urllib_request.Request(
            url=f"{self.native_base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        return urllib_request.urlopen(request, timeout=300)

    def create_embeddings(
        self,
        texts: list[str],
        model: str,
        context_window: int | None = None,
        truncate: bool = True,
    ) -> list[list[float]]:
        if not texts:
            return []

        batch_size = max(1, int(os.getenv("OLLAMA_EMBED_BATCH_SIZE", "16")))
        all_embeddings: list[list[float]] = []

        for start_index in range(0, len(texts), batch_size):
            batch = texts[start_index : start_index + batch_size]
            payload: dict[str, object] = {
                "model": model,
                "input": batch,
                "truncate": bool(truncate),
            }
            options: dict[str, object] = {}
            if context_window:
                options["num_ctx"] = int(context_window)
            if options:
                payload["options"] = options
            response = self._native_json_request("/api/embed", payload)
            embeddings = response.get("embeddings")
            if not isinstance(embeddings, list):
                raise RuntimeError("Resposta inválida do endpoint /api/embed do Ollama.")
            all_embeddings.extend(embeddings)

        return all_embeddings

    def iter_stream_text(self, stream):
        if hasattr(stream, "__iter__") and not hasattr(stream, "choices"):
            for raw_line in stream:
                if isinstance(raw_line, bytes):
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    message = payload.get("message")
                    if isinstance(message, dict):
                        content = message.get("content") or ""
                        if content:
                            yield content
                    if bool(payload.get("done")):
                        prompt_tokens = payload.get("prompt_eval_count")
                        completion_tokens = payload.get("eval_count")
                        total_tokens = None
                        if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
                            total_tokens = int(prompt_tokens) + int(completion_tokens)
                        self._last_usage_metrics = {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens,
                            "usage_source": "ollama_native_usage",
                        }
            return

        for chunk in stream:
            if not getattr(chunk, "choices", None):
                continue

            delta = getattr(chunk.choices[0], "delta", None)
            content = getattr(delta, "content", None) or ""
            if content:
                yield content

    def format_error(self, model: str, error: Exception) -> str:
        return (
            "Não foi possível obter resposta do Ollama.\n\n"
            "Verifique se:\n"
            f"- o servidor está ativo em `{self.settings.base_url}`\n"
            f"- o modelo `{model}` está instalado\n"
            "- o Ollama está respondendo normalmente\n\n"
            f"Detalhes técnicos: {error}"
        )
