from __future__ import annotations

import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

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


class OllamaProviderServiceCompatTests(unittest.TestCase):
    def test_ollama_provider_discovers_models_via_api_before_cli(self) -> None:
        settings = OllamaSettings(
            project_name="AI Decision Studio",
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
            target = getattr(url, "full_url", str(url))
            self.assertTrue(str(target).endswith("/api/tags"))
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

        with patch("src.providers.ollama_provider.urllib_request.urlopen", _fake_urlopen), patch(
            "src.providers.ollama_provider.subprocess.run", _unexpected_subprocess_run
        ):
            self.assertEqual(provider.list_available_models()[:2], ["service-default", "hf-local-demo"])
            self.assertIn("embeddinggemma:300m", provider.list_available_embedding_models())

    def test_ollama_provider_skips_native_cli_runtime_hints_for_service_base_url(self) -> None:
        settings = OllamaSettings(
            project_name="AI Decision Studio",
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
        self.assertFalse(provider._should_use_native_cli_runtime_hints())

    def test_ollama_provider_forwards_chat_operational_overrides(self) -> None:
        settings = OllamaSettings(
            project_name="AI Decision Studio",
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

        with patch("src.providers.ollama_provider.urllib_request.urlopen", _fake_urlopen):
            provider.stream_chat_completion(
                messages=[{"role": "user", "content": "oi"}],
                model="qwen2.5:7b",
                temperature=0.3,
                context_window=16384,
                top_p=0.75,
                max_tokens=256,
                think=False,
            )

        self.assertTrue(str(captured["url"]).endswith("/api/chat"))
        self.assertIs(captured["payload"]["think"], False)
        self.assertEqual(
            captured["payload"]["options"],
            {
                "temperature": 0.3,
                "num_ctx": 16384,
                "top_p": 0.75,
                "num_predict": 256,
            },
        )

    def test_ollama_hosted_base_urls_are_normalized_for_native_and_openai_compat_routes(self) -> None:
        settings = OllamaSettings(
            project_name="AI Decision Studio Hosted",
            base_url="https://ollama.com/api",
            default_model="nemotron-3-nano:30b-cloud",
            default_temperature=0.2,
            default_context_window=8192,
            default_top_p=0.9,
            default_max_tokens=1024,
            default_prompt_profile="neutro",
            available_models_env=[],
            available_embedding_models_env=[],
            history_path=None,
            api_key="test-key",
        )
        provider = OllamaProvider(settings)
        self.assertEqual(provider.native_base_url, "https://ollama.com")
        self.assertEqual(provider.openai_compat_base_url, "https://ollama.com/api/v1")

    def test_ollama_provider_falls_back_to_openai_compat_chat_when_native_route_is_missing(self) -> None:
        settings = OllamaSettings(
            project_name="AI Decision Studio Hosted",
            base_url="https://ollama.com/api",
            default_model="nemotron-3-nano:30b-cloud",
            default_temperature=0.2,
            default_context_window=8192,
            default_top_p=0.9,
            default_max_tokens=1024,
            default_prompt_profile="neutro",
            available_models_env=[],
            available_embedding_models_env=[],
            history_path=None,
            api_key="test-key",
        )
        provider = OllamaProvider(settings)

        def _native_404(request, timeout=300):
            raise HTTPError(request.full_url, 404, "Not Found", hdrs=None, fp=None)

        captured: dict[str, object] = {}

        class _FakeCompletions:
            def create(self, **kwargs):
                captured.update(kwargs)
                return iter([])

        class _FakeChat:
            completions = _FakeCompletions()

        class _FakeClient:
            chat = _FakeChat()

        provider.client = _FakeClient()

        with patch("src.providers.ollama_provider.urllib_request.urlopen", _native_404):
            stream = provider.stream_chat_completion(
                messages=[{"role": "user", "content": "oi"}],
                model="nemotron-3-nano:30b-cloud",
                temperature=0.15,
                context_window=32768,
                top_p=0.8,
                max_tokens=256,
            )

        self.assertEqual(list(stream), [])
        self.assertEqual(
            captured,
            {
                "messages": [{"role": "user", "content": "oi"}],
                "model": "nemotron-3-nano:30b-cloud",
                "temperature": 0.15,
                "stream": True,
                "top_p": 0.8,
                "max_tokens": 256,
            },
        )

    def test_ollama_provider_tries_alternate_openai_compat_routes_when_client_route_is_missing(self) -> None:
        settings = OllamaSettings(
            project_name="AI Decision Studio Hosted",
            base_url="https://ollama.com/api",
            default_model="nemotron-3-nano:30b-cloud",
            default_temperature=0.2,
            default_context_window=8192,
            default_top_p=0.9,
            default_max_tokens=1024,
            default_prompt_profile="neutro",
            available_models_env=[],
            available_embedding_models_env=[],
            history_path=None,
            api_key="test-key",
        )
        provider = OllamaProvider(settings)
        attempted_urls: list[str] = []

        def _fake_urlopen(request, timeout=300):
            attempted_urls.append(request.full_url)
            if request.full_url.endswith("/api/chat"):
                raise HTTPError(request.full_url, 404, "Not Found", hdrs=None, fp=None)
            if request.full_url.endswith("/api/v1/chat/completions"):
                raise HTTPError(request.full_url, 404, "Not Found", hdrs=None, fp=None)
            if request.full_url.endswith("/v1/chat/completions"):
                return _FakeHttpResponse({
                    "choices": [{"message": {"content": "fallback worked"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13},
                })
            raise AssertionError(f"Unexpected route attempted: {request.full_url}")

        class _FailingCompletions:
            def create(self, **kwargs):
                raise RuntimeError('404 - {"error": "path "/api/chat/completions" not found"}')

        class _FakeChat:
            completions = _FailingCompletions()

        class _FakeClient:
            chat = _FakeChat()

        provider.client = _FakeClient()

        with patch("src.providers.ollama_provider.urllib_request.urlopen", _fake_urlopen):
            stream = provider.stream_chat_completion(
                messages=[{"role": "user", "content": "oi"}],
                model="nemotron-3-nano:30b-cloud",
                temperature=0.15,
                context_window=32768,
                top_p=0.8,
                max_tokens=256,
            )
            self.assertEqual("".join(provider.iter_stream_text(stream)), "fallback worked")
            self.assertEqual(provider.get_last_usage_metrics().get("usage_source"), "openai_compat_usage")

        self.assertEqual(
            attempted_urls,
            [
                "https://ollama.com/api/chat",
                "https://ollama.com/api/v1/chat/completions",
                "https://ollama.com/v1/chat/completions",
            ],
        )


if __name__ == "__main__":
    unittest.main()
