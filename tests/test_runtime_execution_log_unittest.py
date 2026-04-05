import tempfile
import unittest
from pathlib import Path

from src.services.runtime_snapshot import build_runtime_execution_summary
from src.storage.runtime_execution_log import append_runtime_execution_log_entry, summarize_runtime_execution_log


class RuntimeExecutionLogTests(unittest.TestCase):
    def test_summarize_runtime_execution_log_aggregates_chat_and_structured_runs(self) -> None:
        entries = [
            {
                "timestamp": "2026-03-30 20:00:00",
                "flow_type": "chat_rag",
                "task_type": "chat_rag",
                "success": True,
                "provider": "ollama",
                "model": "qwen2.5:7b",
                "latency_s": 1.2,
                "retrieval_latency_s": 0.2,
                "generation_latency_s": 0.8,
                "prompt_build_latency_s": 0.1,
                "prompt_chars": 1200,
                "output_chars": 240,
                "context_chars": 700,
                "selected_documents": 1,
                "retrieved_chunks_count": 4,
                "prompt_context_used_chunks": 3,
                "prompt_context_dropped_chunks": 2,
                "prompt_context_truncated": True,
                "prompt_tokens": 300,
                "completion_tokens": 60,
                "total_tokens": 360,
                "usage_source": "estimated_chars",
                "cost_source": "local_runtime_not_priced",
                "context_window_mode": "manual",
                "budget_routing_mode": "budget_guarded",
                "budget_routing_reason": "high_context_pressure",
                "budget_auto_degrade_applied": True,
                "context_pressure_ratio": 1.12,
                "evidence_pipeline_document_count": 1,
                "ocr_document_count": 1,
                "docling_document_count": 1,
                "vl_document_count": 0,
                "ocr_backend_counts": {"ocrmypdf": 1},
            },
            {
                "timestamp": "2026-03-30 20:05:00",
                "flow_type": "structured",
                "task_type": "document_agent",
                "success": False,
                "provider": "ollama",
                "model": "qwen2.5:7b",
                "latency_s": 2.4,
                "needs_review": True,
                "error_message": "boom",
                "prompt_chars": 800,
                "output_chars": 120,
                "context_chars": 450,
                "prompt_tokens": 200,
                "completion_tokens": 30,
                "total_tokens": 230,
                "usage_source": "estimated_chars",
                "cost_source": "pricing_not_configured",
                "context_window_mode": "auto",
                "budget_routing_mode": "quality_first",
                "budget_routing_reason": "high_sensitivity_task",
                "budget_auto_degrade_applied": False,
                "context_pressure_ratio": 0.42,
                "vl_document_count": 1,
            },
        ]

        summary = summarize_runtime_execution_log(entries)

        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["error_rate"], 0.5)
        self.assertEqual(summary["needs_review_rate"], 0.5)
        self.assertEqual(summary["flow_counts"]["chat_rag"], 1)
        self.assertEqual(summary["task_counts"]["document_agent"], 1)
        self.assertEqual(summary["provider_counts"]["ollama"], 2)
        self.assertEqual(summary["total_tokens"], 590)
        self.assertEqual(summary["avg_total_tokens"], 295.0)
        self.assertEqual(summary["avg_prompt_tokens"], 250.0)
        self.assertEqual(summary["avg_prompt_build_latency_s"], 0.1)
        self.assertEqual(summary["avg_retrieved_chunks_count"], 4.0)
        self.assertEqual(summary["avg_context_pressure_ratio"], 0.77)
        self.assertEqual(summary["auto_degrade_rate"], 0.5)
        self.assertEqual(summary["truncated_prompt_rate"], 0.5)
        self.assertEqual(summary["ocr_involved_runs"], 1)
        self.assertEqual(summary["docling_involved_runs"], 1)
        self.assertEqual(summary["vl_involved_runs"], 1)
        self.assertEqual(summary["usage_source_counts"]["estimated_chars"], 2)
        self.assertEqual(summary["budget_mode_counts"]["budget_guarded"], 1)
        self.assertEqual(summary["cost_source_counts"]["local_runtime_not_priced"], 1)
        self.assertEqual(summary["ocr_backend_counts"]["ocrmypdf"], 1)

    def test_build_runtime_execution_summary_exposes_recent_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "runtime_execution_log.json"
            append_runtime_execution_log_entry(
                log_path,
                {
                    "timestamp": "2026-03-30 20:00:00",
                    "flow_type": "chat_rag",
                    "task_type": "chat_rag",
                    "success": True,
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                    "latency_s": 1.2,
                    "prompt_tokens": 180,
                    "completion_tokens": 40,
                    "total_tokens": 220,
                    "usage_source": "estimated_chars",
                },
            )
            append_runtime_execution_log_entry(
                log_path,
                {
                    "timestamp": "2026-03-30 20:05:00",
                    "flow_type": "structured",
                    "task_type": "summary",
                    "success": True,
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                    "latency_s": 2.1,
                    "needs_review": False,
                    "prompt_tokens": 320,
                    "completion_tokens": 90,
                    "total_tokens": 410,
                    "usage_source": "estimated_chars",
                },
            )

            summary = build_runtime_execution_summary(log_path, recent_limit=5)

        self.assertTrue(summary["log_exists"])
        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(len(summary["recent_entries"]), 2)
        self.assertEqual(summary["recent_entries"][0]["task_type"], "summary")
        self.assertEqual(summary["avg_total_tokens"], 315.0)
        self.assertEqual(summary["recent_entries"][0]["total_tokens"], 410)


if __name__ == "__main__":
    unittest.main()