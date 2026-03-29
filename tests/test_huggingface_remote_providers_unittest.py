import unittest

from src.config import HuggingFaceInferenceSettings, HuggingFaceServerSettings
from src.providers.huggingface_inference_provider import HuggingFaceInferenceProvider
from src.providers.huggingface_server_provider import HuggingFaceServerProvider


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