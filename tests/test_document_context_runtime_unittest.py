import sys
import types
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
        fake_rag_state = types.SimpleNamespace(get_rag_runtime_settings=lambda: runtime_settings)
        with patch.dict(sys.modules, {"src.services.rag_state": fake_rag_state}):
            effective = document_context._get_effective_rag_settings()

        self.assertIs(effective, runtime_settings)

    def test_get_effective_rag_settings_falls_back_to_env_settings(self) -> None:
        fake_rag_state = types.SimpleNamespace(get_rag_runtime_settings=lambda: None)
        with patch.dict(sys.modules, {"src.services.rag_state": fake_rag_state}):
            effective = document_context._get_effective_rag_settings()

        self.assertIsInstance(effective, RagSettings)


class DocumentContextGroundingTests(unittest.TestCase):
    def test_get_rag_index_reads_store_path_without_duplicating_runtime_root(self) -> None:
        settings = document_context.get_rag_settings()
        sample_index = {
            "documents": [{"document_id": "doc-1", "name": "Evidence.pdf"}],
            "chunks": [
                {
                    "document_id": "doc-1",
                    "source": "Evidence.pdf",
                    "chunk_id": 1,
                    "text": "Action owner: Identity Ops\nDue date: 2024-03-21\nEvidence gap: approval email missing.",
                }
            ],
        }

        with patch("src.storage.rag_store.load_rag_store", return_value=sample_index) as load_mock, patch(
            "src.services.document_context.get_rag_settings",
            return_value=RagSettings(
                loader_strategy="manual",
                chunking_strategy="manual",
                retrieval_strategy="manual_hybrid",
                embedding_provider="ollama",
                embedding_model="embeddinggemma:300m",
                embedding_context_window=512,
                embedding_truncate=True,
                chunk_size=1200,
                chunk_overlap=80,
                top_k=4,
                store_path=settings.store_path,
                chroma_path=settings.chroma_path,
            ),
        ), patch.dict(sys.modules, {"src.services.rag_state": types.SimpleNamespace(get_rag_index=lambda: None)}):
            rag_index = document_context._get_rag_index()

        load_mock.assert_called_once_with(settings.store_path)
        self.assertEqual(rag_index["chunks"][0]["document_id"], "doc-1")

    def test_build_document_scan_context_returns_grounded_blocks_for_selected_docs(self) -> None:
        sample_index = {
            "documents": [{"document_id": "doc-1", "name": "Evidence.pdf"}],
            "chunks": [
                {
                    "document_id": "doc-1",
                    "source": "Evidence.pdf",
                    "chunk_id": 1,
                    "text": "Action owner: Identity Ops\nDue date: 2024-03-21\nEvidence gap: approval email missing.",
                }
            ],
        }

        with patch("src.services.document_context._get_rag_index", return_value=sample_index):
            context = document_context.build_document_scan_context(document_ids=["doc-1"])

        self.assertIn("[Source: Evidence.pdf]", context)
        self.assertIn("Action owner: Identity Ops", context)
        self.assertIn("Due date: 2024-03-21", context)

    def test_build_document_scan_context_falls_back_to_document_metadata_when_chunks_missing(self) -> None:
        sample_index = {
            "documents": [
                {
                    "document_id": "doc-1",
                    "name": "Access Review Evidence Log.pdf",
                    "loader_metadata": {
                        "indexing_payload": {
                            "raw_text": "EV-002 missing approval email for privileged vendor accounts. Owner: Compliance Operations."
                        }
                    },
                }
            ],
            "chunks": [],
        }

        with patch("src.services.document_context._get_rag_index", return_value=sample_index):
            context = document_context.build_document_scan_context(document_ids=["doc-1"])

        self.assertIn("[Source: Access Review Evidence Log.pdf]", context)
        self.assertIn("missing approval email", context)
        self.assertIn("Compliance Operations", context)


    def test_build_document_scan_context_falls_back_to_document_loader_excerpt_when_chunks_missing(self) -> None:
        sample_index = {
            "documents": [
                {
                    "document_id": "doc-1",
                    "name": "Evidence.pdf",
                    "loader_metadata": {
                        "grounding_text_excerpt": "Action owner: Identity Ops\nDue date: 2024-03-21\nEvidence gap: approval email missing.",
                    },
                }
            ],
            "chunks": [],
        }

        with patch("src.services.document_context._get_rag_index", return_value=sample_index):
            context = document_context.build_document_scan_context(document_ids=["doc-1"])

        self.assertIn("[Source: Evidence.pdf]", context)
        self.assertIn("Action owner: Identity Ops", context)
        self.assertIn("Due date: 2024-03-21", context)

    def test_build_document_scan_context_reads_chroma_chunks_when_json_store_has_no_chunks(self) -> None:
        sample_index = {
            "documents": [{"document_id": "doc-1", "name": "Evidence.pdf"}],
            "chunks": [],
        }

        chroma_chunks = [
            {
                "document_id": "doc-1",
                "source": "Evidence.pdf",
                "chunk_id": 1,
                "text": "Action owner: Identity Ops\nDue date: 2024-03-21\nEvidence gap: approval email missing.",
            }
        ]

        with patch("src.services.document_context._get_rag_index", return_value=sample_index), patch(
            "src.services.document_context._load_chroma_chunks", return_value=chroma_chunks
        ):
            context = document_context.build_document_scan_context(document_ids=["doc-1"])

        self.assertIn("[Source: Evidence.pdf]", context)
        self.assertIn("Action owner: Identity Ops", context)
        self.assertIn("Due date: 2024-03-21", context)



if __name__ == "__main__":
    unittest.main()
