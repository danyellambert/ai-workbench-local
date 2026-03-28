import unittest
from unittest.mock import patch

from src.config import RagSettings
from src.services import document_context


class DocumentContextRuntimeTests(unittest.TestCase):
    def test_get_effective_rag_settings_prefers_runtime_state(self) -> None:
        runtime_settings = RagSettings(
            loader_strategy="manual",
            chunking_strategy="manual",
            retrieval_strategy="manual_hybrid",
            embedding_provider="huggingface_local",
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_context_window=1024,
            embedding_truncate=True,
            chunk_size=1200,
            chunk_overlap=80,
            top_k=6,
            store_path=document_context.get_rag_settings().store_path,
            chroma_path=document_context.get_rag_settings().chroma_path,
        )
        with patch("src.services.rag_state.get_rag_runtime_settings", return_value=runtime_settings):
            effective = document_context._get_effective_rag_settings()

        self.assertIs(effective, runtime_settings)

    def test_get_effective_rag_settings_falls_back_to_env_settings(self) -> None:
        with patch("src.services.rag_state.get_rag_runtime_settings", return_value=None):
            effective = document_context._get_effective_rag_settings()

        self.assertIsInstance(effective, RagSettings)


if __name__ == "__main__":
    unittest.main()