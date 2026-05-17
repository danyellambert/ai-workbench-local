from __future__ import annotations

import json
import os
from urllib import error, request

from ppt_creator_ai.providers.local_service import LocalServiceBriefingProvider


class OllamaLocalBriefingProvider(LocalServiceBriefingProvider):
    name = "ollama_local"
    description = "Calls a local Ollama daemon directly over HTTP and can enumerate installed local models."
    DEFAULT_PROVIDER_NAME = "ollama"
    DEFAULT_MODEL_NAME = ""
    GENERATION_ENDPOINT_CANDIDATES = ("/api/generate",)
    MODELS_ENDPOINT = "/api/tags"
    VERSION_ENDPOINT = "/api/version"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model_name: str | None = None,
        generation_attempts: int | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            provider_name=self.DEFAULT_PROVIDER_NAME,
            model_name=model_name,
            generation_attempts=generation_attempts,
        )

    def with_runtime_overrides(self, **runtime_overrides: str | None) -> "OllamaLocalBriefingProvider":
        generation_attempts = runtime_overrides.get("generation_attempts")
        return self.__class__(
            base_url=runtime_overrides.get("base_url") or self._base_url_override,
            model_name=runtime_overrides.get("model_name") or self._model_name_override,
            generation_attempts=(
                int(str(generation_attempts))
                if generation_attempts not in {None, ""}
                else self._generation_attempts_override
            ),
        )

    def resolve_base_url(self) -> str:
        return (
            self._base_url_override
            or os.environ.get("PPT_CREATOR_OLLAMA_BASE_URL")
            or "http://127.0.0.1:11434"
        ).strip().rstrip("/")

    def resolve_provider_name(self) -> str:
        return self.DEFAULT_PROVIDER_NAME

    def resolve_provider_source(self) -> str:
        return "environment" if os.environ.get("PPT_CREATOR_OLLAMA_BASE_URL") else "app_default"

    def resolve_model_name(self) -> str:
        configured = (self._model_name_override or os.environ.get("PPT_CREATOR_OLLAMA_MODEL") or "").strip()
        if configured:
            return configured
        models = self.list_models().get("models") or []
        if not models:
            raise RuntimeError(
                "No local Ollama models are available. Pull one first, for example: ollama pull qwen2.5:7b"
            )
        first = str(models[0].get("name") or models[0].get("model") or "").strip()
        if not first:
            raise RuntimeError("Ollama returned a model list without usable model names")
        return first

    def resolve_model_source(self) -> str:
        if self._model_name_override or os.environ.get("PPT_CREATOR_OLLAMA_MODEL"):
            return "environment"
        return "auto_discovered"

    def resolve_timeout_seconds(self) -> int:
        return int(os.environ.get("PPT_CREATOR_OLLAMA_TIMEOUT_SECONDS", "180"))

    def resolve_status_timeout_seconds(self) -> float:
        raw_value = (
            os.environ.get("PPT_CREATOR_OLLAMA_STATUS_TIMEOUT_SECONDS")
            or os.environ.get("PPT_CREATOR_AI_STATUS_TIMEOUT_SECONDS")
            or "2.0"
        )
        try:
            return max(0.2, float(raw_value))
        except ValueError:
            return 2.0

    def resolve_retry_attempts(self) -> int:
        return max(1, int(os.environ.get("PPT_CREATOR_OLLAMA_RETRY_ATTEMPTS", "2")))

    def resolve_retry_backoff_seconds(self) -> float:
        return max(0.0, float(os.environ.get("PPT_CREATOR_OLLAMA_RETRY_BACKOFF_SECONDS", "1.5")))

    def resolve_generation_attempts(self) -> int:
        if self._generation_attempts_override is not None:
            return max(1, int(self._generation_attempts_override))
        return max(1, int(os.environ.get("PPT_CREATOR_OLLAMA_GENERATION_ATTEMPTS", "3")))

    def _format_service_error(
        self,
        *,
        base_url: str,
        path: str,
        status_code: int | None = None,
        code: str | None = None,
        message: str | None = None,
        retriable: bool | None = None,
        fallback_message: str,
    ) -> str:
        parts = [f"Ollama local request to {base_url}{path} failed"]
        if status_code is not None:
            parts.append(f"HTTP {status_code}")
        if code:
            parts.append(code)
        detail = message or fallback_message
        formatted = " • ".join(parts)
        if detail:
            formatted = f"{formatted}: {detail}"
        if retriable is not None:
            formatted = f"{formatted} (retriable={str(retriable).lower()})"
        return formatted

    def _request_json(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        base_url = self.resolve_base_url()
        attempts = self.resolve_retry_attempts()

        for attempt in range(1, attempts + 1):
            req = request.Request(
                f"{base_url}{path}",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=self.resolve_timeout_seconds()) as response:
                    body = response.read().decode("utf-8", errors="replace")
            except error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
                parsed_payload: dict[str, object] | None = None
                if body.strip():
                    try:
                        decoded = json.loads(body)
                    except json.JSONDecodeError:
                        decoded = None
                    if isinstance(decoded, dict):
                        parsed_payload = decoded
                message, code, retriable_hint = self._extract_error_details(parsed_payload or {})
                retriable = retriable_hint if retriable_hint is not None else exc.code in self.RETRIABLE_HTTP_STATUS_CODES
                runtime_error = RuntimeError(
                    self._format_service_error(
                        base_url=base_url,
                        path=path,
                        status_code=exc.code,
                        code=code,
                        message=message,
                        retriable=retriable,
                        fallback_message=exc.reason or exc.msg or "HTTP error",
                    )
                )
                if retriable and attempt < attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise runtime_error from exc
            except error.URLError as exc:
                runtime_error = RuntimeError(
                    f"Could not reach Ollama local runtime at {base_url}{path} after {attempt} attempt(s). "
                    f"Start the local Ollama daemon first. Details: {exc.reason}"
                )
                if attempt < attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise runtime_error from exc

            try:
                response_payload = json.loads(body)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Ollama local runtime returned invalid JSON: {exc.msg}") from exc

            if not isinstance(response_payload, dict):
                raise RuntimeError("Ollama local runtime returned a non-object JSON response")
            if response_payload.get("error"):
                message, code, retriable = self._extract_error_details(response_payload)
                runtime_error = RuntimeError(
                    self._format_service_error(
                        base_url=base_url,
                        path=path,
                        status_code=None,
                        code=code,
                        message=message,
                        retriable=retriable,
                        fallback_message="runtime returned an application error payload",
                    )
                )
                if retriable and attempt < attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise runtime_error
            return response_payload

        raise RuntimeError(f"Ollama local request to {base_url}{path} failed after {attempts} attempt(s)")

    def _request_json_get(self, path: str, *, timeout_seconds: float | None = None) -> dict[str, object]:
        base_url = self.resolve_base_url()
        req = request.Request(f"{base_url}{path}", method="GET")
        resolved_timeout = timeout_seconds if timeout_seconds is not None else min(self.resolve_timeout_seconds(), 10)
        try:
            with request.urlopen(req, timeout=resolved_timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
            parsed_payload: dict[str, object] | None = None
            if body.strip():
                try:
                    decoded = json.loads(body)
                except json.JSONDecodeError:
                    decoded = None
                if isinstance(decoded, dict):
                    parsed_payload = decoded
            message, code, retriable = self._extract_error_details(parsed_payload or {})
            raise RuntimeError(
                self._format_service_error(
                    base_url=base_url,
                    path=path,
                    status_code=exc.code,
                    code=code,
                    message=message,
                    retriable=retriable,
                    fallback_message=exc.reason or exc.msg or "HTTP error",
                )
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(
                f"Could not reach Ollama local runtime at {base_url}{path}. Start the local Ollama daemon first. Details: {exc.reason}"
            ) from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ollama local runtime returned invalid JSON: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("Ollama local runtime returned a non-object JSON response")
        return payload

    def _request_generation_round(self, prompt: str) -> tuple[dict[str, object], dict[str, object], str | None]:
        request_payload = {
            "model": self.resolve_model_name(),
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        payload = self._request_json(self.GENERATION_ENDPOINT_CANDIDATES[0], request_payload)
        raw_output = str(payload.get("response") or "") or None
        ai_exchange = {
            "kind": "external_ai_roundtrip",
            "transport": self.name,
            "target_url": f"{self.resolve_base_url()}{self.GENERATION_ENDPOINT_CANDIDATES[0]}",
            "request_payload": request_payload,
            "prompt": prompt,
            "response_payload": payload,
            "raw_response": raw_output,
        }
        return payload, ai_exchange, raw_output

    def list_models(self) -> dict[str, object]:
        payload = self._request_json_get(self.MODELS_ENDPOINT)
        raw_models = payload.get("models") if isinstance(payload.get("models"), list) else []
        models: list[dict[str, object]] = []
        for item in raw_models:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("model") or "").strip()
            if not name:
                continue
            models.append(
                {
                    "name": name,
                    "size": item.get("size"),
                    "modified_at": item.get("modified_at"),
                    "digest": item.get("digest"),
                    "details": item.get("details") if isinstance(item.get("details"), dict) else {},
                }
            )
        models.sort(key=lambda item: str(item.get("name") or ""))
        return {
            "provider": self.name,
            "service_url": self.resolve_base_url(),
            "model_count": len(models),
            "models": models,
        }

    def status_payload(self) -> dict[str, object]:
        service_url = self.resolve_base_url()
        tags_url = f"{service_url}{self.MODELS_ENDPOINT}"
        version_url = f"{service_url}{self.VERSION_ENDPOINT}"
        status_timeout_seconds = min(float(self.resolve_timeout_seconds()), self.resolve_status_timeout_seconds())
        version_payload: dict[str, object] | None = None
        health_status = "unknown"
        health_error: str | None = None
        models: list[dict[str, object]] = []
        try:
            model_payload = self._request_json_get(self.MODELS_ENDPOINT, timeout_seconds=status_timeout_seconds)
            raw_models = model_payload.get("models") if isinstance(model_payload.get("models"), list) else []
            models = []
            for item in raw_models:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or item.get("model") or "").strip()
                if not name:
                    continue
                models.append(
                    {
                        "name": name,
                        "size": item.get("size"),
                        "modified_at": item.get("modified_at"),
                        "digest": item.get("digest"),
                        "details": item.get("details") if isinstance(item.get("details"), dict) else {},
                    }
                )
            models.sort(key=lambda item: str(item.get("name") or ""))
            health_status = "ok"
            try:
                version_payload = self._request_json_get(self.VERSION_ENDPOINT, timeout_seconds=status_timeout_seconds)
            except Exception:
                version_payload = None
        except Exception as exc:  # noqa: BLE001
            health_status = "error"
            health_error = str(exc)
        selected_model = (self._model_name_override or os.environ.get("PPT_CREATOR_OLLAMA_MODEL") or "").strip() or None
        if selected_model is None and models:
            selected_model = str(models[0].get("name") or "").strip() or None
        return {
            "service_url": service_url,
            "health_url": tags_url,
            "version_url": version_url,
            "provider_name": self.resolve_provider_name(),
            "provider_source": self.resolve_provider_source(),
            "model_name": selected_model,
            "model_source": self.resolve_model_source(),
            "timeout_seconds": self.resolve_timeout_seconds(),
            "status_timeout_seconds": status_timeout_seconds,
            "retry_attempts": self.resolve_retry_attempts(),
            "retry_backoff_seconds": self.resolve_retry_backoff_seconds(),
            "generation_attempts": self.resolve_generation_attempts(),
            "health_status": health_status,
            "health_error": health_error,
            "model_count": len(models),
            "models": models,
            "version_payload": version_payload,
            "supports_model_listing": True,
        }