"""
Runtime provider trace hook for AI Decision Studio.

Usage from the repository root:
  PYTHONPATH="$PWD/diagnostics:${PYTHONPATH:-}" RUNTIME_TRACE_FILE="$PWD/runtime-provider-trace.log" <your normal backend command>

This module is auto-imported by Python when it is on PYTHONPATH as `sitecustomize`.
It logs outbound HTTP calls made by requests/httpx, redacting secrets but keeping
provider host, path, model name, and Authorization/api-key fingerprints.
"""
from __future__ import annotations

import datetime as _dt
import hashlib as _hashlib
import json as _json
import os as _os
import sys as _sys
import threading as _threading
import traceback as _traceback
from typing import Any as _Any
from urllib.parse import parse_qsl as _parse_qsl, urlencode as _urlencode, urlsplit as _urlsplit, urlunsplit as _urlunsplit

_TRACE_LOCK = _threading.Lock()
_TRACE_FILE = _os.getenv("RUNTIME_TRACE_FILE", "").strip()
_ENABLE_STACK = _os.getenv("RUNTIME_TRACE_STACK", "1").strip().lower() not in {"0", "false", "no", "off"}
_MAX_STACK = int(_os.getenv("RUNTIME_TRACE_STACK_FRAMES", "8") or "8")

_SECRET_KEYS = {
    "authorization",
    "api-key",
    "api_key",
    "x-api-key",
    "x-api-token",
    "hf-token",
    "access_token",
    "token",
    "key",
}
_URL_SECRET_PARAMS = {"api_key", "apikey", "key", "token", "access_token", "authorization"}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _hash_secret(value: object) -> str:
    text = str(value or "")
    if not text:
        return "empty"
    return _hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:12]


def _redact_url(url: object) -> str:
    text = str(url or "")
    try:
        parts = _urlsplit(text)
        if not parts.query:
            return text
        items = []
        for key, value in _parse_qsl(parts.query, keep_blank_values=True):
            if key.lower() in _URL_SECRET_PARAMS:
                items.append((key, f"<redacted:{_hash_secret(value)}>"))
            else:
                items.append((key, value))
        return _urlunsplit((parts.scheme, parts.netloc, parts.path, _urlencode(items), parts.fragment))
    except Exception:
        return text


def _normalize_headers(headers: object) -> dict[str, object]:
    if headers is None:
        return {}
    try:
        if hasattr(headers, "multi_items"):
            return {str(k).lower(): v for k, v in headers.multi_items()}
        if hasattr(headers, "items"):
            return {str(k).lower(): v for k, v in headers.items()}
    except Exception:
        return {}
    return {}


def _header_fingerprints(*header_maps: object) -> dict[str, str]:
    merged: dict[str, object] = {}
    for headers in header_maps:
        merged.update(_normalize_headers(headers))
    result: dict[str, str] = {}
    for key, value in merged.items():
        lower = key.lower()
        if lower in _SECRET_KEYS or "authorization" in lower or "api-key" in lower or lower.endswith("token"):
            text = str(value or "")
            if lower == "authorization" and text.lower().startswith("bearer "):
                text = text[7:].strip()
                result[lower] = f"Bearer sha256:{_hash_secret(text)}"
            else:
                result[lower] = f"sha256:{_hash_secret(text)}"
    return result


def _extract_body_summary(kwargs: dict[str, _Any]) -> dict[str, _Any]:
    summary: dict[str, _Any] = {}
    payload = None
    if "json" in kwargs:
        payload = kwargs.get("json")
    elif "content" in kwargs:
        payload = kwargs.get("content")
    elif "data" in kwargs:
        payload = kwargs.get("data")

    if isinstance(payload, (bytes, bytearray)):
        try:
            if len(payload) <= 1024 * 1024:
                payload = _json.loads(payload.decode("utf-8", "ignore"))
        except Exception:
            payload = None
    elif isinstance(payload, str):
        try:
            if len(payload) <= 1024 * 1024:
                payload = _json.loads(payload)
        except Exception:
            payload = None

    if isinstance(payload, dict):
        for key in ["model", "max_tokens", "max_completion_tokens", "stream"]:
            if key in payload:
                summary[key] = payload.get(key)
        if isinstance(payload.get("options"), dict):
            opts = payload.get("options") or {}
            for key in ["num_predict", "temperature", "top_p", "num_ctx"]:
                if key in opts:
                    summary[f"options.{key}"] = opts.get(key)
        messages = payload.get("messages")
        if isinstance(messages, list):
            summary["messages_count"] = len(messages)
        prompt = payload.get("prompt")
        if isinstance(prompt, str):
            summary["prompt_chars"] = len(prompt)
        input_value = payload.get("input")
        if isinstance(input_value, str):
            summary["input_chars"] = len(input_value)
        elif isinstance(input_value, list):
            summary["input_count"] = len(input_value)
    return summary


def _interesting_stack() -> list[str]:
    frames = _traceback.extract_stack()[:-2]
    selected: list[str] = []
    for frame in reversed(frames):
        filename = frame.filename.replace("\\", "/")
        if "/site-packages/" in filename or filename.endswith("diagnostics/sitecustomize.py"):
            continue
        if filename.startswith("<"):
            continue
        selected.append(f"{filename}:{frame.lineno}:{frame.name}")
        if len(selected) >= _MAX_STACK:
            break
    return list(reversed(selected))


def _write_event(event: dict[str, _Any]) -> None:
    line = "[runtime-trace] " + _json.dumps(event, ensure_ascii=False, sort_keys=True)
    with _TRACE_LOCK:
        if _TRACE_FILE:
            try:
                with open(_TRACE_FILE, "a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
                return
            except Exception as exc:
                print(f"[runtime-trace] could not write trace file {_TRACE_FILE!r}: {exc}", file=_sys.stderr)
        print(line, file=_sys.stderr, flush=True)


def _make_event(library: str, method: object, url: object, headers: object, kwargs: dict[str, _Any], extra_headers: object = None) -> dict[str, _Any]:
    redacted_url = _redact_url(url)
    event: dict[str, _Any] = {
        "ts": _now(),
        "library": library,
        "method": str(method or "").upper(),
        "url": redacted_url,
        "auth": _header_fingerprints(extra_headers, headers, kwargs.get("headers")),
        "body": _extract_body_summary(kwargs),
    }
    try:
        parts = _urlsplit(str(url or ""))
        event["host"] = parts.netloc
        event["path"] = parts.path
    except Exception:
        pass
    if _ENABLE_STACK:
        event["stack"] = _interesting_stack()
    return event


def _emit_startup_event() -> None:
    env_names = [
        "OLLAMA_BASE_URL",
        "OLLAMA_HOSTED_BASE_URL",
        "OLLAMA_HOSTED_API_KEY",
        "OLLAMA_API_KEY",
        "HUGGINGFACEHUB_API_TOKEN",
        "HUGGINGFACE_INFERENCE_API_KEY",
        "HF_TOKEN",
        "HF_LOCAL_LLM_SERVICE_BASE_URL",
        "OPENAI_API_KEY",
    ]
    env_snapshot: dict[str, object] = {}
    for name in env_names:
        value = _os.getenv(name)
        env_snapshot[name] = None if not value else f"set sha256:{_hash_secret(value)}"
    _write_event({"ts": _now(), "event": "runtime_provider_trace_enabled", "trace_file": _TRACE_FILE or "stderr", "env": env_snapshot})


_emit_startup_event()

try:
    import requests as _requests

    _orig_requests_request = _requests.sessions.Session.request

    def _traced_requests_request(self, method, url, **kwargs):  # type: ignore[no-untyped-def]
        _write_event(_make_event("requests", method, url, getattr(self, "headers", None), kwargs))
        return _orig_requests_request(self, method, url, **kwargs)

    _requests.sessions.Session.request = _traced_requests_request
except Exception as _exc:
    _write_event({"ts": _now(), "event": "requests_patch_failed", "error": repr(_exc)})

try:
    import httpx as _httpx

    _orig_httpx_client_request = _httpx.Client.request
    _orig_httpx_async_client_request = _httpx.AsyncClient.request

    def _traced_httpx_client_request(self, method, url, **kwargs):  # type: ignore[no-untyped-def]
        _write_event(_make_event("httpx", method, url, getattr(self, "headers", None), kwargs))
        return _orig_httpx_client_request(self, method, url, **kwargs)

    async def _traced_httpx_async_client_request(self, method, url, **kwargs):  # type: ignore[no-untyped-def]
        _write_event(_make_event("httpx_async", method, url, getattr(self, "headers", None), kwargs))
        return await _orig_httpx_async_client_request(self, method, url, **kwargs)

    _httpx.Client.request = _traced_httpx_client_request
    _httpx.AsyncClient.request = _traced_httpx_async_client_request
except Exception as _exc:
    _write_event({"ts": _now(), "event": "httpx_patch_failed", "error": repr(_exc)})

try:
    from urllib import request as _urllib_request

    _orig_urllib_urlopen = _urllib_request.urlopen

    def _traced_urllib_urlopen(url, data=None, timeout=None, *args, **kwargs):  # type: ignore[no-untyped-def]
        request_obj = url
        method = kwargs.get("method")
        headers = None
        target_url = url
        body_kwargs: dict[str, _Any] = {}
        if hasattr(request_obj, "full_url"):
            target_url = getattr(request_obj, "full_url", url)
            try:
                method = getattr(request_obj, "get_method")()
            except Exception:
                method = method or ("POST" if getattr(request_obj, "data", None) is not None else "GET")
            headers = getattr(request_obj, "headers", None)
            data_value = getattr(request_obj, "data", None)
            if data_value is not None:
                body_kwargs["data"] = data_value
        elif data is not None:
            body_kwargs["data"] = data
        _write_event(_make_event("urllib", method or ("POST" if data is not None else "GET"), target_url, headers, body_kwargs, extra_headers=kwargs.get("headers")))
        if timeout is None:
            return _orig_urllib_urlopen(url, data=data, *args, **kwargs)
        return _orig_urllib_urlopen(url, data=data, timeout=timeout, *args, **kwargs)

    _urllib_request.urlopen = _traced_urllib_urlopen
except Exception as _exc:
    _write_event({"ts": _now(), "event": "urllib_patch_failed", "error": repr(_exc)})
