from __future__ import annotations

import json

from src.config import OllamaSettings
from src.providers.ollama_provider import OllamaProvider


class _FakeHttpResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_ollama_provider_discovers_models_via_api_before_cli(monkeypatch) -> None:
    settings = OllamaSettings(
        project_name="AI Workbench Local",
        base_url="http://127.0.0.1:8788/v1",
        default_model="service-default",
        default_temperature=0.2,
        default_context_window=8192,
        default_prompt_profile="neutro",
        available_models_env=[],
        available_embedding_models_env=[],
        history_path=None,
    )
    provider = OllamaProvider(settings)

    def _fake_urlopen(url, timeout=5):
        assert str(url).endswith("/api/tags")
        return _FakeHttpResponse(
            {
                "models": [
                    {"name": "hf-local-demo", "provider": "huggingface_local"},
                    {"name": "embeddinggemma:300m", "provider": "ollama"},
                ]
            }
        )

    def _unexpected_subprocess_run(*args, **kwargs):
        raise AssertionError("CLI discovery should not be used when /api/tags is available")

    monkeypatch.setattr("src.providers.ollama_provider.urllib_request.urlopen", _fake_urlopen)
    monkeypatch.setattr("src.providers.ollama_provider.subprocess.run", _unexpected_subprocess_run)

    assert provider.list_available_models()[:2] == ["service-default", "hf-local-demo"]
    assert "embeddinggemma:300m" in provider.list_available_embedding_models()


def test_ollama_provider_skips_native_cli_runtime_hints_for_service_base_url() -> None:
    settings = OllamaSettings(
        project_name="AI Workbench Local",
        base_url="http://127.0.0.1:8788/v1",
        default_model="service-default",
        default_temperature=0.2,
        default_context_window=8192,
        default_prompt_profile="neutro",
        available_models_env=[],
        available_embedding_models_env=[],
        history_path=None,
    )
    provider = OllamaProvider(settings)

    assert provider._should_use_native_cli_runtime_hints() is False


def test_ollama_provider_forwards_chat_operational_overrides(monkeypatch) -> None:
    settings = OllamaSettings(
        project_name="AI Workbench Local",
        base_url="http://127.0.0.1:11434/v1",
        default_model="qwen2.5:7b",
        default_temperature=0.2,
        default_context_window=8192,
        default_top_p=0.9,
        default_max_tokens=1024,
        default_prompt_profile="neutro",
        available_models_env=[],
        available_embedding_models_env=[],
        history_path=None,
    )
    provider = OllamaProvider(settings)
    captured: dict[str, object] = {}

    def _fake_urlopen(request, timeout=300):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeHttpResponse({"message": {"content": "ok"}})

    monkeypatch.setattr("src.providers.ollama_provider.urllib_request.urlopen", _fake_urlopen)

    provider.stream_chat_completion(
        messages=[{"role": "user", "content": "oi"}],
        model="qwen2.5:7b",
        temperature=0.3,
        context_window=16384,
        top_p=0.75,
        max_tokens=256,
    )

    assert str(captured["url"]).endswith("/api/chat")
    assert captured["payload"]["options"] == {
        "temperature": 0.3,
        "num_ctx": 16384,
        "top_p": 0.75,
        "num_predict": 256,
    }