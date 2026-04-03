import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.config import HuggingFaceInferenceSettings, HuggingFaceServerSettings
from src.providers.huggingface_inference_provider import HuggingFaceInferenceProvider
from src.providers.huggingface_server_provider import HuggingFaceServerProvider
from src.providers.registry import build_provider_registry


class _FakeHttpResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        import json

        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class HuggingFaceRemoteProviderTests(unittest.TestCase):
    def test_server_provider_lists_declared_models_without_duplicates(self) -> None:
        provider = HuggingFaceServerProvider(
            HuggingFaceServerSettings(
                base_url="http://127.0.0.1:8010/v1",
                api_key=None,
                model="model-a",
                embedding_model="",
                default_context_window=8192,
                available_models_env=["model-a", "model-b"],
                available_embedding_models_env=[],
            )
        )
        self.assertEqual(provider.list_available_models(), ["model-a", "model-b"])

    def test_server_provider_discovers_models_and_embedding_models_from_service_catalog(self) -> None:
        provider = HuggingFaceServerProvider(
            HuggingFaceServerSettings(
                base_url="http://127.0.0.1:8788/v1",
                api_key=None,
                model="",
                embedding_model="",
                default_context_window=8192,
                available_models_env=[],
                available_embedding_models_env=[],
            )
        )

        with patch(
            "src.providers.huggingface_server_provider.urllib_request.urlopen",
            return_value=_FakeHttpResponse(
                {
                    "models": [
                        {"alias": "service-chat", "supports_chat": True, "supports_embeddings": False},
                        {"alias": "service-both", "supports_chat": True, "supports_embeddings": True},
                        {"alias": "service-embed", "supports_chat": False, "supports_embeddings": True},
                    ]
                }
            ),
        ):
            self.assertEqual(provider.list_available_models(), ["service-chat", "service-both"])
            self.assertEqual(provider.list_available_embedding_models(), ["service-both", "service-embed"])

    def test_server_provider_uses_api_show_for_context_inspection_when_available(self) -> None:
        provider = HuggingFaceServerProvider(
            HuggingFaceServerSettings(
                base_url="http://127.0.0.1:8788/v1",
                api_key=None,
                model="service-chat",
                embedding_model="service-embed",
                default_context_window=8192,
                available_models_env=[],
                available_embedding_models_env=[],
            )
        )

        with patch(
            "src.providers.huggingface_server_provider.urllib_request.urlopen",
            return_value=_FakeHttpResponse(
                {
                    "model_info": {
                        "context_length": 32768,
                        "hf_local_llm_service.provider": "huggingface_mlx",
                        "hf_local_llm_service.model_ref": "mlx-community/Qwen3.5-4B-MLX-4bit",
                        "hf_local_llm_service.supports_embeddings": False,
                    }
                }
            ),
        ):
            context_payload = provider.inspect_context_window("service-chat", requested_context_window=12000)
            embedding_payload = provider.inspect_embedding_context_window("service-chat", requested_context_window=12000)

        self.assertTrue(context_payload["show_available"])
        self.assertEqual(context_payload["declared_context_length"], 32768)
        self.assertEqual(context_payload["backend_provider"], "huggingface_mlx")
        self.assertEqual(embedding_payload["supports_embeddings"], False)

    def test_server_provider_passes_operational_chat_overrides_via_extra_body(self) -> None:
        provider = HuggingFaceServerProvider(
            HuggingFaceServerSettings(
                base_url="http://127.0.0.1:8788/v1",
                api_key=None,
                model="service-chat",
                embedding_model="",
                default_context_window=8192,
                available_models_env=[],
                available_embedding_models_env=[],
            )
        )

        captured: dict[str, object] = {}

        def _fake_create(**kwargs):
            captured.update(kwargs)
            return object()

        with patch.object(provider.client.chat.completions, "create", side_effect=_fake_create):
            provider.stream_chat_completion(
                messages=[{"role": "user", "content": "oi"}],
                model="service-chat",
                temperature=0.35,
                context_window=16384,
                top_p=0.8,
                max_tokens=512,
            )

        self.assertEqual(captured["model"], "service-chat")
        self.assertEqual(captured["temperature"], 0.35)
        self.assertTrue(captured["stream"])
        self.assertEqual(
            captured["extra_body"],
            {"provider_config": {"temperature": 0.35, "ctx_size": 16384, "top_p": 0.8, "max_tokens": 512}},
        )

    def test_server_provider_passes_embedding_overrides_via_extra_body(self) -> None:
        provider = HuggingFaceServerProvider(
            HuggingFaceServerSettings(
                base_url="http://127.0.0.1:8788/v1",
                api_key=None,
                model="service-chat",
                embedding_model="service-embed",
                default_context_window=8192,
                available_models_env=[],
                available_embedding_models_env=[],
            )
        )

        captured: dict[str, object] = {}

        def _fake_create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])])

        with patch.object(provider.client.embeddings, "create", side_effect=_fake_create):
            embeddings = provider.create_embeddings(
                texts=["alpha"],
                model="service-embed",
                context_window=2048,
                truncate=False,
            )

        self.assertEqual(embeddings, [[0.1, 0.2]])
        self.assertEqual(captured["model"], "service-embed")
        self.assertEqual(captured["input"], ["alpha"])
        self.assertEqual(
            captured["extra_body"],
            {"provider_config": {"truncate": False, "ctx_size": 2048}},
        )

    @patch("src.providers.registry.get_huggingface_server_settings")
    def test_registry_includes_huggingface_server_from_remote_catalog_even_without_env_default_model(self, mock_settings) -> None:
        mock_settings.return_value = HuggingFaceServerSettings(
            base_url="http://127.0.0.1:8788/v1",
            api_key=None,
            model="",
            embedding_model="",
            default_context_window=8192,
            available_models_env=[],
            available_embedding_models_env=[],
        )

        with patch(
            "src.providers.huggingface_server_provider.urllib_request.urlopen",
            return_value=_FakeHttpResponse(
                {
                    "models": [
                        {"alias": "service-chat", "supports_chat": True, "supports_embeddings": False},
                        {"alias": "service-both", "supports_chat": True, "supports_embeddings": True},
                    ]
                }
            ),
        ):
            registry = build_provider_registry()

        self.assertIn("huggingface_server", registry)
        self.assertEqual(registry["huggingface_server"]["default_model"], "service-chat")
        self.assertTrue(registry["huggingface_server"]["supports_embeddings"])

    @patch("src.providers.registry.get_huggingface_server_settings")
    def test_registry_auto_discovers_local_hf_service_when_base_url_is_blank(self, mock_settings) -> None:
        mock_settings.return_value = HuggingFaceServerSettings(
            base_url="",
            api_key=None,
            model="",
            embedding_model="",
            default_context_window=8192,
            available_models_env=[],
            available_embedding_models_env=[],
        )

        def _fake_urlopen(url, timeout=5):
            assert str(url).endswith("127.0.0.1:8788/v1/models")
            return _FakeHttpResponse(
                {
                    "models": [
                        {"alias": "service-chat", "supports_chat": True, "supports_embeddings": False},
                    ]
                }
            )

        with patch("src.providers.huggingface_server_provider.urllib_request.urlopen", side_effect=_fake_urlopen):
            registry = build_provider_registry()

        self.assertIn("huggingface_server", registry)
        self.assertEqual(registry["huggingface_server"]["default_model"], "service-chat")
        self.assertIn("auto-descoberto", registry["huggingface_server"]["detail"])

    def test_inference_provider_lists_declared_models_without_duplicates(self) -> None:
        provider = HuggingFaceInferenceProvider(
            HuggingFaceInferenceSettings(
                base_url="https://router.huggingface.co/v1",
                api_key="hf_token",
                model="model-a",
                embedding_model="",
                default_context_window=8192,
                available_models_env=["model-a", "model-b"],
                available_embedding_models_env=[],
            )
        )
        self.assertEqual(provider.list_available_models(), ["model-a", "model-b"])


if __name__ == "__main__":
    unittest.main()