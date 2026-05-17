import json
import os
import re
import subprocess
from urllib import error as urllib_error
from urllib import request as urllib_request
from types import SimpleNamespace
from urllib.parse import urlparse


class _CompatResponseStream:
    def __init__(self, content: str, usage: dict[str, object] | None = None) -> None:
        self.usage = usage or {}
        self.choices = []
        self._chunks = [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])]

    def __iter__(self):
        return iter(self._chunks)

try:
    from openai import OpenAI
except Exception:  # optional dependency
    OpenAI = None

from src.config import OllamaSettings
from src.storage.secret_store import get_secret


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
        self.native_base_url = self._build_native_base_url(settings.base_url)
        self.openai_compat_base_url = self._build_openai_compat_base_url(settings.base_url)
        self._last_usage_metrics: dict[str, object] = {}

    def reset_last_usage_metrics(self) -> None:
        self._last_usage_metrics = {}

    def get_last_usage_metrics(self) -> dict[str, object]:
        return dict(self._last_usage_metrics)

    def _current_api_key(self) -> str | None:
        """Return the freshest credential for this provider.

        Hosted Ollama credentials can be replaced from Preferences while the
        backend keeps running. Every request must re-read the UI-managed secret
        instead of reusing a value captured when the provider was constructed.
        """
        secret_key = str(getattr(self.settings, "api_key_secret_key", "") or "").strip()
        if secret_key:
            secret_value = str(get_secret(secret_key) or "").strip()
            if secret_value:
                return secret_value
        settings_value = str(self.settings.api_key or "").strip()
        return settings_value or None

    def _openai_client(self):
        if OpenAI is None:
            return None
        return OpenAI(base_url=self.openai_compat_base_url, api_key=self._current_api_key() or "ollama")

    def _has_ui_managed_secret(self) -> bool:
        return bool(str(getattr(self.settings, "api_key_secret_key", "") or "").strip())

    @staticmethod
    def _build_native_base_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/v1"):
            normalized = normalized[:-3]
        elif normalized.endswith("/api"):
            normalized = normalized[:-4]
        return normalized.rstrip("/")

    @staticmethod
    def _build_openai_compat_base_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/v1"):
            return normalized
        if normalized.endswith("/api"):
            return f"{normalized}/v1"
        return f"{normalized}/v1"

    def _is_local_runtime(self) -> bool:
        parsed = urlparse(self.native_base_url)
        hostname = (parsed.hostname or "").strip().lower()
        return hostname in {"127.0.0.1", "localhost", "0.0.0.0", "host.docker.internal"}

    def _is_hosted_runtime(self) -> bool:
        return not self._is_local_runtime()

    @staticmethod
    def _normalize_hosted_model_name(model_name: str) -> str:
        normalized = str(model_name or "").strip()
        lookup = normalized.lower()
        hosted_aliases = {
            "nemotron-3-nano:30b": "nemotron-3-nano:30b-cloud",
            "nemotron-3-nano-30b": "nemotron-3-nano:30b-cloud",
            "nemotron-3-nano-30b-cloud": "nemotron-3-nano:30b-cloud",
            "nemotron-3-super": "nemotron-3-super:cloud",
            "nemotron-3-super:cloud": "nemotron-3-super:cloud",
            "nemotron-3-super-cloud": "nemotron-3-super:cloud",
        }
        return hosted_aliases.get(lookup, normalized)


    def _effective_model_name(self, model_name: str) -> str:
        normalized = str(model_name or "").strip()
        if not normalized:
            return normalized
        if self._is_hosted_runtime():
            return self._normalize_hosted_model_name(normalized)
        return normalized


    def _discover_local_models(self) -> list[str]:
        discovered_via_api = self._discover_models_via_api()
        if discovered_via_api:
            return discovered_via_api

        if not self._is_local_runtime():
            return []

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
            request = urllib_request.Request(
                f"{self.native_base_url}/api/tags",
                headers=self._native_headers(),
                method="GET",
            )
            with urllib_request.urlopen(request, timeout=5) as response:
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

    def _native_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = self._current_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

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
        hosted_defaults = ["nemotron-3-nano:30b-cloud", "nemotron-3-super:cloud"] if self._is_hosted_runtime() else []
        fallback_models = self.FALLBACK_MODELS if self._is_local_runtime() else []
        ordered_models: list[str] = []
        for model in [
            self.settings.default_model,
            *self.settings.available_models_env,
            *discovered_models,
            *hosted_defaults,
            *fallback_models,
        ]:
            normalized = self._effective_model_name(str(model or ""))
            if normalized and normalized not in ordered_models:
                ordered_models.append(normalized)
        return ordered_models

    def list_available_embedding_models(self) -> list[str]:
        discovered_models = self._discover_local_models()
        fallback_models = self.FALLBACK_EMBEDDING_MODELS if self._is_local_runtime() else []
        ordered_models: list[str] = []
        for model in [
            *self.settings.available_embedding_models_env,
            *discovered_models,
            *fallback_models,
        ]:
            if model and self._looks_like_embedding_model(model) and model not in ordered_models:
                ordered_models.append(model)
        if ordered_models:
            return ordered_models
        return self.FALLBACK_EMBEDDING_MODELS[:] if self._is_local_runtime() else []

    def probe_connection(self) -> dict[str, object]:
        request = urllib_request.Request(
            f"{self.native_base_url}/api/tags",
            headers=self._native_headers(),
            method="GET",
        )
        timeout_seconds = int(os.getenv("OLLAMA_HTTP_TIMEOUT_SECONDS", "300"))
        try:
            with urllib_request.urlopen(request, timeout=min(timeout_seconds, 10)) as response:
                payload = json.loads(response.read().decode("utf-8"))
            models = payload.get("models") if isinstance(payload, dict) else []
            return {
                "status": "connected",
                "last_error_message": None,
                "model_count": len(models) if isinstance(models, list) else 0,
            }
        except urllib_error.HTTPError as error:
            self._close_http_error(error)
            status = "degraded"
            if int(getattr(error, "code", 0) or 0) in {401, 403}:
                status = "degraded"
            elif self._is_local_runtime():
                status = "disconnected"
            return {
                "status": status,
                "last_error_message": f"HTTP {getattr(error, 'code', 'error')}: {getattr(error, 'reason', 'request failed')}",
                "model_count": 0,
            }
        except Exception as error:
            return {
                "status": "disconnected" if self._is_local_runtime() else "degraded",
                "last_error_message": str(error),
                "model_count": 0,
            }

    def _native_json_request(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        request = urllib_request.Request(
            url=f"{self.native_base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._native_headers(),
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
            "model": self._effective_model_name(model),
        }

        effective_model = self._effective_model_name(model)
        try:
            show_payload = self._native_json_request("/api/show", {"model": effective_model})
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
            "Use `/api/chat` to apply `num_ctx`, `/api/show` to inspect the model's declared context, "
            "and `ollama ps` only as an auxiliary runtime confirmation."
        )
        return output

    def inspect_embedding_context_window(self, model: str, requested_context_window: int | None = None) -> dict[str, object]:
        output: dict[str, object] = {
            "api_route": f"{self.native_base_url}/api/embed",
            "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
            "model": self._effective_model_name(model),
            "truncate": True,
        }
        effective_model = self._effective_model_name(model)
        try:
            show_payload = self._native_json_request("/api/show", {"model": effective_model})
            output["show_available"] = True
            output["declared_context_length"] = self._extract_declared_context_length(show_payload)
            modified_at = show_payload.get("modified_at")
            if modified_at:
                output["model_modified_at"] = modified_at
        except Exception as error:
            output["show_available"] = False
            output["show_error"] = str(error)

        output["validation_summary"] = (
            "The native `/api/embed` endpoint accepts `truncate` and `options`. The app sends `options.num_ctx` as operational "
            "control for the embedding window, but effective behavior still depends on the model and the Ollama runtime."
        )
        return output

    def _stream_chat_completion_openai_compat(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        top_p: float | None,
        max_tokens: int | None,
        context_window: int | None = None,
    ):
        client = self._openai_client()
        if client is None:
            raise RuntimeError("OpenAI-compatible Ollama client is unavailable for fallback chat routing.")

        request_kwargs: dict[str, object] = {
            "messages": messages,
            "model": self._effective_model_name(model),
            "temperature": temperature,
            "stream": True,
        }
        if top_p is not None:
            request_kwargs["top_p"] = float(top_p)
        if max_tokens is not None:
            request_kwargs["max_tokens"] = int(max_tokens)
        if context_window is not None:
            request_kwargs["extra_body"] = {"options": {"num_ctx": int(context_window)}}
        return client.chat.completions.create(**request_kwargs)

    @staticmethod
    def _close_http_error(error: Exception) -> None:
        close_fn = getattr(error, "close", None)
        if callable(close_fn):
            try:
                close_fn()
            except Exception:
                pass
        fp = getattr(error, "fp", None)
        close_fp = getattr(fp, "close", None)
        if callable(close_fp):
            try:
                close_fp()
            except Exception:
                pass

    @staticmethod
    def _is_not_found_error(error: Exception) -> bool:
        code = getattr(error, "code", None)
        status_code = getattr(error, "status_code", None)
        if code == 404 or status_code == 404:
            return True
        message = str(error or "").lower()
        return "404" in message and ("not found" in message or 'path "' in message or "path '" in message)

    def _openai_compat_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = self._current_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _candidate_openai_compat_urls(self) -> list[str]:
        raw_base = self.settings.base_url.rstrip("/")
        candidates: list[str] = []
        if raw_base.endswith("/v1"):
            candidates.extend([
                f"{raw_base}/chat/completions",
                f"{raw_base[:-3].rstrip('/')}/api/v1/chat/completions",
                f"{raw_base[:-3].rstrip('/')}/api/chat/completions",
            ])
        elif raw_base.endswith("/api"):
            candidates.extend([
                f"{raw_base}/v1/chat/completions",
                f"{raw_base[:-4].rstrip('/')}/v1/chat/completions",
                f"{raw_base}/chat/completions",
            ])
        else:
            candidates.extend([
                f"{raw_base}/v1/chat/completions",
                f"{raw_base}/api/v1/chat/completions",
                f"{raw_base}/chat/completions",
            ])
        deduped: list[str] = []
        for url in candidates:
            normalized = url.rstrip("/")
            if normalized and normalized not in deduped:
                deduped.append(normalized)
        return deduped

    def _request_openai_compat_completion(
        self,
        *,
        url: str,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        top_p: float | None,
        max_tokens: int | None,
        context_window: int | None = None,
    ):
        payload: dict[str, object] = {
            "messages": messages,
            "model": self._effective_model_name(model),
            "temperature": temperature,
            "stream": False,
        }
        if top_p is not None:
            payload["top_p"] = float(top_p)
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        if context_window is not None:
            payload["options"] = {"num_ctx": int(context_window)}
        request = urllib_request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._openai_compat_headers(),
            method="POST",
        )
        with urllib_request.urlopen(request, timeout=300) as response:
            payload = json.loads(response.read().decode("utf-8"))
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("OpenAI-compatible chat completion returned no choices.")
        first_choice = choices[0] if isinstance(choices[0], dict) else {}
        message = first_choice.get("message") if isinstance(first_choice, dict) else {}
        content = str(message.get("content") or "") if isinstance(message, dict) else ""
        usage = payload.get("usage") if isinstance(payload, dict) and isinstance(payload.get("usage"), dict) else None
        return _CompatResponseStream(content=content, usage=usage)

    def _stream_chat_completion_openai_compat_with_fallbacks(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        top_p: float | None,
        max_tokens: int | None,
        context_window: int | None = None,
    ):
        last_error: Exception | None = None

        # Prefer the direct HTTP path for Ollama-compatible hosted runtimes.
        # It builds Authorization headers at request time from _current_api_key().
        # This avoids SDK/client state or connection reuse keeping an older
        # credential alive after Preferences replaces the Keychain item.
        for candidate_url in self._candidate_openai_compat_urls():
            try:
                return self._request_openai_compat_completion(
                    url=candidate_url,
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    context_window=context_window,
                )
            except Exception as error:
                last_error = error
                if not self._is_not_found_error(error):
                    raise
                self._close_http_error(error)
                continue

        # The SDK is kept only as a last-resort compatibility path for local
        # runtimes that are not using UI-managed credentials.
        if OpenAI is not None and not self._has_ui_managed_secret():
            try:
                return self._stream_chat_completion_openai_compat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    context_window=context_window,
                )
            except Exception as error:
                last_error = error
                if not self._is_not_found_error(error):
                    raise
                self._close_http_error(error)

        if last_error is not None:
            raise last_error
        raise RuntimeError("OpenAI-compatible Ollama fallback could not resolve a working chat route.")

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
            "model": self._effective_model_name(model),
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
            headers=self._native_headers(),
            method="POST",
        )

        try:
            return urllib_request.urlopen(request, timeout=300)
        except urllib_error.HTTPError as error:
            should_try_openai_compat = error.code == 404 and not self._should_use_native_cli_runtime_hints()
            if not should_try_openai_compat:
                raise
            self._close_http_error(error)
            return self._stream_chat_completion_openai_compat_with_fallbacks(
                messages=messages,
                model=model,
                temperature=temperature,
                top_p=resolved_top_p,
                max_tokens=resolved_max_tokens,
                context_window=context_window,
            )

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
                "model": self._effective_model_name(model),
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
                raise RuntimeError("Invalid response from the Ollama /api/embed endpoint.")
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

        final_usage = getattr(stream, "usage", None)
        if isinstance(final_usage, dict):
            prompt_tokens = final_usage.get("prompt_tokens")
            completion_tokens = final_usage.get("completion_tokens")
            total_tokens = final_usage.get("total_tokens")
            self._last_usage_metrics = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "usage_source": "openai_compat_usage",
            }

    def format_error(self, model: str, error: Exception) -> str:
        return (
            "Could not get a response from Ollama.\n\n"
            "Check whether:\n"
            f"- the server is active at `{self.settings.base_url}`\n"
            f"- the model `{model}` is installed\n"
            "- Ollama is responding normally\n\n"
            f"Technical details: {error}"
        )
