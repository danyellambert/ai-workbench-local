import unittest

from src.config import HuggingFaceSettings
from src.providers.huggingface_local_provider import HuggingFaceLocalProvider


class HuggingFaceLocalProviderTests(unittest.TestCase):
    def test_list_available_models_preserves_declared_order_without_duplicates(self) -> None:
        provider = HuggingFaceLocalProvider(
            HuggingFaceSettings(
                model="local-model-a",
                embedding_model="",
                default_context_window=8192,
                available_models_env=["local-model-a", "local-model-b"],
                available_embedding_models_env=[],
                generation_task="text-generation",
                max_new_tokens=256,
            )
        )
        self.assertEqual(provider.list_available_models(), ["local-model-a", "local-model-b"])

    def test_iter_stream_text_yields_strings_from_simple_iterable(self) -> None:
        stream = ["part 1", "part 2"]
        self.assertEqual(list(HuggingFaceLocalProvider.iter_stream_text(stream)), ["part 1", "part 2"])

    def test_format_messages_as_prompt_falls_back_to_manual_role_prompt(self) -> None:
        provider = HuggingFaceLocalProvider(
            HuggingFaceSettings(
                model="local-model-a",
                embedding_model="",
                default_context_window=8192,
                available_models_env=[],
                available_embedding_models_env=[],
                generation_task="text-generation",
                max_new_tokens=256,
            )
        )

        prompt, metadata = provider._format_messages_as_prompt([{"role": "user", "content": "Hello"}], tokenizer=None)

        self.assertIn("USER: Hello", prompt)
        self.assertEqual(metadata["prompt_serialization_mode"], "manual_role_prompt")
        self.assertFalse(metadata["chat_template_used"])


if __name__ == "__main__":
    unittest.main()