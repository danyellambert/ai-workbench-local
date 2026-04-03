import unittest

from src.providers.registry import (
    build_embedding_provider_sidebar_state,
    describe_embedding_provider_unavailable_reason,
    filter_registry_by_capability,
    resolve_provider_entry,
    resolve_provider_runtime_profile,
)


class ProviderRegistryTests(unittest.TestCase):
    class _DummyEmbeddingProvider:
        def __init__(self, models: list[str]) -> None:
            self._models = models

        def list_available_embedding_models(self) -> list[str]:
            return list(self._models)

    def test_resolve_provider_entry_returns_requested_provider_when_capability_exists(self) -> None:
        registry = {
            "ollama": {"supports_chat": True, "supports_embeddings": True, "instance": object()},
            "openai": {"supports_chat": True, "supports_embeddings": True, "instance": object()},
        }
        provider_key, provider_entry, fallback_reason = resolve_provider_entry(
            registry,
            "openai",
            capability="embeddings",
            fallback_provider="ollama",
        )
        self.assertEqual(provider_key, "openai")
        self.assertIs(provider_entry, registry["openai"])
        self.assertIsNone(fallback_reason)

    def test_resolve_provider_entry_falls_back_when_requested_provider_is_missing(self) -> None:
        registry = {
            "ollama": {"supports_chat": True, "supports_embeddings": True, "instance": object()},
        }
        provider_key, provider_entry, fallback_reason = resolve_provider_entry(
            registry,
            "openai",
            capability="embeddings",
            fallback_provider="ollama",
        )
        self.assertEqual(provider_key, "ollama")
        self.assertIs(provider_entry, registry["ollama"])
        self.assertEqual(fallback_reason, "embeddings_provider_unavailable:openai")

    def test_resolve_provider_entry_returns_error_when_capability_does_not_exist(self) -> None:
        registry = {
            "ollama": {"supports_chat": True, "supports_embeddings": False, "instance": object()},
        }
        provider_key, provider_entry, fallback_reason = resolve_provider_entry(
            registry,
            "ollama",
            capability="embeddings",
            fallback_provider="ollama",
        )
        self.assertIsNone(provider_key)
        self.assertIsNone(provider_entry)
        self.assertEqual(fallback_reason, "no_provider_with_capability:embeddings")

    def test_filter_registry_by_capability_returns_only_supported_entries(self) -> None:
        registry = {
            "ollama": {"supports_chat": True, "supports_embeddings": True, "instance": object()},
            "openai": {"supports_chat": True, "supports_embeddings": False, "instance": object()},
        }

        filtered = filter_registry_by_capability(registry, "embeddings")

        self.assertEqual(list(filtered.keys()), ["ollama"])

    def test_resolve_provider_runtime_profile_exposes_effective_runtime_metadata(self) -> None:
        registry = {
            "ollama": {
                "supports_chat": True,
                "supports_embeddings": True,
                "instance": object(),
                "label": "Ollama (local)",
                "default_model": "qwen2.5:7b",
                "default_context_window": 8192,
            },
        }

        runtime = resolve_provider_runtime_profile(
            registry,
            "openai",
            capability="chat",
            fallback_provider="ollama",
        )

        self.assertEqual(runtime["requested_provider"], "openai")
        self.assertEqual(runtime["effective_provider"], "ollama")
        self.assertEqual(runtime["provider_label"], "Ollama (local)")
        self.assertEqual(runtime["default_model"], "qwen2.5:7b")
        self.assertEqual(runtime["default_context_window"], 8192)
        self.assertEqual(runtime["fallback_reason"], "chat_provider_unavailable:openai")

    def test_describe_embedding_provider_unavailable_reason_explains_hf_server_and_inference(self) -> None:
        self.assertIn("supports_embeddings=true", describe_embedding_provider_unavailable_reason("huggingface_server"))
        self.assertIn("HUGGINGFACE_INFERENCE_EMBEDDING_MODEL", describe_embedding_provider_unavailable_reason("huggingface_inference"))

    def test_build_embedding_provider_sidebar_state_separates_available_and_disabled_entries(self) -> None:
        registry = {
            "ollama": {
                "label": "Ollama (local)",
                "supports_embeddings": True,
                "instance": self._DummyEmbeddingProvider(["embeddinggemma:300m"]),
            },
            "huggingface_server": {
                "label": "Hugging Face server local",
                "supports_embeddings": False,
                "instance": self._DummyEmbeddingProvider([]),
            },
            "huggingface_inference": {
                "label": "Hugging Face Inference",
                "supports_embeddings": False,
                "instance": self._DummyEmbeddingProvider([]),
            },
        }

        state = build_embedding_provider_sidebar_state(registry)

        self.assertEqual(state["available_options"], {"ollama": "Ollama (local)"})
        self.assertEqual(state["available_models_by_provider"]["ollama"], ["embeddinggemma:300m"])
        unavailable_by_key = {item["provider_key"]: item for item in state["unavailable_items"]}
        self.assertIn("huggingface_server", unavailable_by_key)
        self.assertIn("supports_embeddings=true", unavailable_by_key["huggingface_server"]["reason"])
        self.assertIn("huggingface_inference", unavailable_by_key)
        self.assertIn("HUGGINGFACE_INFERENCE_EMBEDDING_MODEL", unavailable_by_key["huggingface_inference"]["reason"])


if __name__ == "__main__":
    unittest.main()