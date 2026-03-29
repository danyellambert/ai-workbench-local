import unittest
from types import SimpleNamespace

from src.services.runtime_snapshot import build_runtime_snapshot, summarize_provider_path
from src.structured.base import SummaryPayload
from src.structured.envelope import StructuredResult


class _DummyStructuredTaskRegistry:
    def list_tasks(self):
        return {
            "summary": SimpleNamespace(default_model="summary-model"),
            "extraction": SimpleNamespace(default_model=None),
        }


class RuntimeSnapshotTests(unittest.TestCase):
    def test_summarize_provider_path_for_local_ollama(self) -> None:
        route, dependency = summarize_provider_path("ollama", "Ollama (local)", "http://localhost:11434")

        self.assertIn("localhost:11434", route)
        self.assertIn("servidor Ollama", dependency)

    def test_build_runtime_snapshot_aggregates_chat_structured_and_document_metadata(self) -> None:
        structured_result = StructuredResult(
            success=True,
            task_type="summary",
            raw_output_text="{}",
            parsed_json={},
            validated_output=SummaryPayload(
                task_type="summary",
                topics=[],
                executive_summary="ok",
                key_insights=[],
                reading_time_minutes=1,
                completeness_score=0.8,
            ),
            execution_metadata={
                "provider": "ollama",
                "model": "qwen2.5:7b",
                "execution_strategy_used": "langgraph_context_retry",
                "agent_intent": "Pergunta documental",
                "agent_tool": "Consultar documentos indexados",
                "agent_answer_mode": "friendly",
                "agent_available_tools": [{"name": "consult_documents", "available": True}],
                "needs_review": True,
                "needs_review_reason": "low_agent_confidence",
                "agent_limitations": ["Confiança estimada abaixo do ideal (68%)."],
                "agent_recommended_actions": ["Encaminhe o resultado para revisão humana."],
                "agent_guardrails_applied": ["Resposta restrita aos documentos selecionados."],
                "workflow_attempts": 2,
                "workflow_context_strategies": ["document_scan", "retrieval"],
                "telemetry": {
                    "timings_s": {
                        "total_s": 2.5,
                        "provider_total_s": 1.5,
                        "document_load_s": 0.2,
                        "sanitize_s": 0.1,
                        "context_build_s": 0.3,
                        "parsing_s": 0.2,
                    }
                },
            },
        )
        messages = [
            {
                "role": "assistant",
                "metadata": {
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                    "vector_backend_used": "chroma",
                    "retrieval_strategy_used": "langchain_chroma",
                    "latency_s": 1.2,
                    "generation_latency_s": 0.8,
                    "retrieval_latency_s": 0.2,
                    "prompt_build_latency_s": 0.1,
                },
            }
        ]
        document_preview_map = {
            "doc-1": {
                "document": {
                    "name": "cv.pdf",
                    "file_type": "pdf",
                    "loader_metadata": {
                        "loader_strategy_label": "Manual local",
                        "strategy_label": "Híbrido inteligente",
                        "source_type": "pdf",
                        "ocr_backend": "ocrmypdf",
                        "evidence_pipeline_used": True,
                        "vl_runtime": {"model": "llava"},
                    },
                },
                "chunks_count": 5,
            }
        }

        snapshot = build_runtime_snapshot(
            selected_provider="ollama",
            selected_provider_label="Ollama (local)",
            selected_model="qwen2.5:7b",
            selected_embedding_provider="ollama",
            selected_embedding_model="embeddinggemma:300m",
            selected_loader_strategy="manual",
            selected_chunking_strategy="langchain_recursive",
            selected_retrieval_strategy="langchain_chroma",
            selected_pdf_extraction_mode="hybrid",
            chat_selected_document_ids=["doc-1"],
            structured_selected_document_ids=["doc-1"],
            selected_structured_task="summary",
            selected_structured_execution_strategy="langgraph_context_retry",
            messages=messages,
            structured_result=structured_result,
            structured_task_registry=_DummyStructuredTaskRegistry(),
            document_preview_map=document_preview_map,
            indexed_documents_count=1,
            ollama_base_url="http://localhost:11434",
            default_vl_model="llava",
            default_ocr_backend="ocrmypdf",
        )

        self.assertEqual(snapshot["chat"]["embedding_provider"], "ollama")
        self.assertEqual(snapshot["chat"]["embedding_model"], "embeddinggemma:300m")
        self.assertEqual(snapshot["structured"]["execution_strategy"], "langgraph_context_retry")
        self.assertEqual(snapshot["structured"]["agent_intent"], "Pergunta documental")
        self.assertEqual(snapshot["structured"]["agent_tool"], "Consultar documentos indexados")
        self.assertEqual(snapshot["structured"]["agent_available_tools"], [{"name": "consult_documents", "available": True}])
        self.assertTrue(snapshot["structured"]["needs_review"])
        self.assertEqual(snapshot["structured"]["agent_limitations"], ["Confiança estimada abaixo do ideal (68%)."])
        self.assertEqual(snapshot["structured"]["agent_recommended_actions"], ["Encaminhe o resultado para revisão humana."])
        self.assertEqual(snapshot["structured"]["agent_guardrails_applied"], ["Resposta restrita aos documentos selecionados."])
        self.assertEqual(snapshot["structured"]["workflow_attempts"], 2)
        self.assertEqual(snapshot["structured"]["last_pre_model_prep_s"], 0.6)
        self.assertEqual(snapshot["documents"]["indexed_documents"], 1)
        self.assertEqual(snapshot["documents"]["chat_selected_docs"][0]["documento"], "cv.pdf")
        self.assertEqual(snapshot["documents"]["chat_selected_docs"][0]["ocr_backend"], "ocrmypdf")
        self.assertEqual(snapshot["structured"]["task_model_map"]["summary"], "summary-model")


if __name__ == "__main__":
    unittest.main()