import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.product.models import ProductWorkflowRequest
from src.product.service import (
    build_grounding_preview,
    build_product_workflow_catalog,
    list_product_documents,
    run_product_workflow,
)
from src.structured.base import CVAnalysisPayload
from src.structured.envelope import StructuredResult


class ProductServiceTests(unittest.TestCase):
    def test_build_product_workflow_catalog_exposes_four_core_workflows(self) -> None:
        catalog = build_product_workflow_catalog()

        self.assertEqual(set(catalog.keys()), {
            "document_review",
            "policy_contract_comparison",
            "action_plan_evidence_review",
            "candidate_review",
        })
        self.assertEqual(catalog["candidate_review"].default_export_kind, "candidate_review_deck")

    def test_build_grounding_preview_returns_context_metadata(self) -> None:
        with patch("src.product.service.build_structured_document_context", return_value="[Source: doc]\nhello world"):
            preview = build_grounding_preview(query="hello", document_ids=["doc-1"], strategy="document_scan")

        self.assertEqual(preview.context_chars, len("[Source: doc]\nhello world"))
        self.assertEqual(preview.source_block_count, 1)
        self.assertEqual(preview.document_ids, ["doc-1"])

    def test_run_product_workflow_candidate_review_uses_cv_analysis_engine(self) -> None:
        structured_result = StructuredResult(
            success=True,
            task_type="cv_analysis",
            validated_output=CVAnalysisPayload(
                personal_info={"full_name": "Ada Candidate", "location": "Remote"},
                skills=["Python", "LLM Ops"],
                strengths=["Strong product thinking"],
                improvement_areas=["Needs deeper stakeholder examples"],
                experience_years=7.0,
            ),
        )
        request = ProductWorkflowRequest(
            workflow_id="candidate_review",
            document_ids=["cv-1"],
            provider="ollama",
            model="qwen2.5:7b",
        )

        with (
            patch("src.product.service.build_structured_document_context", return_value="[Source: cv-1]\nAda Candidate"),
            patch("src.product.service.run_structured_execution_workflow", return_value=structured_result) as workflow_mock,
        ):
            result = run_product_workflow(request)

        self.assertEqual(result.workflow_id, "candidate_review")
        self.assertEqual(result.workflow_label, "Candidate Review")
        self.assertEqual(result.deck_export_kind, "candidate_review_deck")
        self.assertTrue(result.deck_available)
        self.assertIn("Ada Candidate", result.summary)
        self.assertEqual(workflow_mock.call_args.kwargs["strategy"], "direct")
        self.assertEqual(workflow_mock.call_args.args[0].task_type, "cv_analysis")

    def test_list_product_documents_reads_current_rag_store(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            rag_store_path = temp_path / ".rag_store.json"
            rag_store_path.write_text(
                '{"documents":[{"document_id":"doc-1","name":"Policy A","file_type":"pdf","char_count":1200,"chunk_count":4,"indexed_at":"2026-04-05 19:00:00","loader_metadata":{"loader_strategy_label":"Manual local"}}],"chunks":[],"settings":{},"updated_at":"2026-04-05 19:00:00"}',
                encoding="utf-8",
            )

            class FakeRagSettings:
                store_path = rag_store_path
                chunk_size = 1200
                chunk_overlap = 80
                top_k = 4
                rerank_pool_size = 8
                rerank_lexical_weight = 0.35
                loader_strategy = "manual"
                chunking_strategy = "manual"
                retrieval_strategy = "manual_hybrid"
                embedding_provider = "ollama"
                embedding_model = "embeddinggemma:300m"
                embedding_context_window = 512
                embedding_truncate = True
                chroma_path = temp_path / ".chroma_rag"
                context_budget_ratio = 0.45
                pdf_extraction_mode = "hybrid"
                pdf_docling_enabled = True
                pdf_docling_ocr_enabled = True
                pdf_docling_force_full_page_ocr = False
                pdf_docling_picture_description = False
                pdf_ocr_fallback_enabled = True
                pdf_ocr_fallback_languages = "eng+por"

            documents = list_product_documents(FakeRagSettings())

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].document_id, "doc-1")
        self.assertEqual(documents[0].loader_strategy_label, "Manual local")


if __name__ == "__main__":
    unittest.main()