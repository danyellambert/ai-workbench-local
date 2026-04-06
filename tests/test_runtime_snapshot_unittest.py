import tempfile
from pathlib import Path
import unittest
from types import SimpleNamespace

from src.services.runtime_snapshot import (
    build_document_agent_runtime_summary,
    build_eval_runtime_summary,
    build_runtime_execution_summary,
    build_runtime_snapshot,
    summarize_provider_path,
)
from src.storage.phase6_document_agent_log import append_document_agent_log_entry
from src.storage.phase95_evidenceops_action_store import append_evidenceops_actions_from_worklog_entry
from src.storage.phase95_evidenceops_worklog import append_evidenceops_worklog_entry
from src.storage.phase8_eval_store import append_eval_run
from src.storage.runtime_execution_log import append_runtime_execution_log_entry
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
        self.assertIn("Ollama server", dependency)

    def test_summarize_provider_path_for_huggingface_server(self) -> None:
        route, dependency = summarize_provider_path(
            "huggingface_server",
            "Hugging Face local server (Local server configured at `http://127.0.0.1:8788/v1`)",
            "http://localhost:11434",
        )

        self.assertIn("AI hub local", route)
        self.assertIn("effective backend may vary", dependency)

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
                "agent_intent": "Document question",
                "agent_tool": "Consult indexed documents",
                "agent_answer_mode": "friendly",
                "agent_available_tools": [{"name": "consult_documents", "available": True}],
                "needs_review": True,
                "needs_review_reason": "low_agent_confidence",
                "agent_limitations": ["Estimated confidence below ideal (68%)."],
                "agent_recommended_actions": ["Forward the result for human review before making a final decision."],
                "agent_guardrails_applied": ["Response restricted to documents selected in the document base."],
                "workflow_attempts": 2,
                "workflow_context_strategies": ["document_scan", "retrieval"],
                "context_chars_sent": 1600,
                "full_document_chars": 4200,
                "context_strategy": "document_scan",
                "telemetry": {
                    "budget_routing_mode": "quality_first",
                    "budget_routing_reason": "high_sensitivity_task",
                    "budget_auto_degrade_applied": False,
                    "budget_total_tokens": 280,
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
                    "prompt_context": {
                        "used_chars": 700,
                        "used_chunks": 3,
                        "dropped_chunks": 1,
                        "truncated": True,
                    },
                    "usage": {"total_tokens": 320, "cost_usd": None, "context_chars": 700},
                },
            }
        ]
        document_preview_map = {
            "doc-1": {
                "document": {
                    "name": "cv.pdf",
                    "file_type": "pdf",
                    "loader_metadata": {
                        "loader_strategy_label": "Local manual",
                        "strategy_label": "Smart hybrid",
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
            provider_detail=None,
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
        self.assertEqual(snapshot["structured"]["agent_intent"], "Document question")
        self.assertEqual(snapshot["structured"]["agent_tool"], "Consult indexed documents")
        self.assertEqual(snapshot["structured"]["agent_available_tools"], [{"name": "consult_documents", "available": True}])
        self.assertTrue(snapshot["structured"]["needs_review"])
        self.assertEqual(snapshot["structured"]["agent_limitations"], ["Estimated confidence below ideal (68%)."])
        self.assertEqual(snapshot["structured"]["agent_recommended_actions"], ["Forward the result for human review before making a final decision."])
        self.assertEqual(snapshot["structured"]["agent_guardrails_applied"], ["Response restricted to documents selected in the document base."])
        self.assertEqual(snapshot["structured"]["workflow_attempts"], 2)
        self.assertEqual(snapshot["structured"]["last_pre_model_prep_s"], 0.6)
        self.assertEqual(snapshot["chat"]["last_prompt_context_used_chunks"], 3)
        self.assertTrue(snapshot["chat"]["last_prompt_context_truncated"])
        self.assertEqual(snapshot["structured"]["last_context_chars"], 1600)
        self.assertEqual(snapshot["structured"]["last_context_strategy"], "document_scan")
        self.assertEqual(snapshot["documents"]["indexed_documents"], 1)
        self.assertEqual(snapshot["documents"]["chat_selected_docs"][0]["document"], "cv.pdf")
        self.assertEqual(snapshot["documents"]["chat_selected_docs"][0]["ocr_backend"], "ocrmypdf")
        self.assertEqual(snapshot["structured"]["task_model_map"]["summary"], "summary-model")

    def test_build_eval_runtime_summary_aggregates_recent_eval_readiness_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "phase8_eval.sqlite3"
            append_eval_run(
                db_path,
                {
                    "created_at": "2026-03-29T10:00:00",
                    "suite_name": "structured_smoke_eval",
                    "task_type": "summary",
                    "status": "PASS",
                    "score": 5,
                    "max_score": 5,
                },
            )
            append_eval_run(
                db_path,
                {
                    "created_at": "2026-03-29T10:05:00",
                    "suite_name": "agent_workflow_eval",
                    "task_type": "extraction",
                    "status": "FAIL",
                    "score": 2,
                    "max_score": 5,
                    "reasons": ["quality_score_below_target"],
                },
            )

            summary = build_eval_runtime_summary(db_path, recent_limit=50)

        self.assertTrue(summary["db_exists"])
        self.assertEqual(summary["entries_considered"], 2)
        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(summary["suite_counts"]["structured_smoke_eval"], 1)
        self.assertEqual(summary["task_counts"]["extraction"], 1)
        self.assertEqual(summary["global_recommendation"], "prompt_rag_schema_iteration_still_sufficient_globally")
        self.assertEqual(summary["top_failure_reasons"][0]["reason"], "quality_score_below_target")

    def test_build_document_agent_runtime_summary_aggregates_recent_agent_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / ".phase6_document_agent_log.json"
            append_document_agent_log_entry(
                log_path,
                {
                    "timestamp": "2026-03-31T10:00:00",
                    "query": "Compare the contracts",
                    "success": True,
                    "user_intent": "document_comparison",
                    "tool_used": "compare_documents",
                    "answer_mode": "comparison_structured",
                    "execution_strategy_used": "langgraph_context_retry",
                    "workflow_route_decision": "document_comparison->compare_documents",
                    "workflow_guardrail_decision": "finish_ok",
                    "needs_review": False,
                    "confidence": 0.81,
                    "source_count": 2,
                    "available_tools_count": 10,
                    "error_tool_runs": 0,
                },
            )
            append_document_agent_log_entry(
                log_path,
                {
                    "timestamp": "2026-03-31T10:05:00",
                    "query": "Review the risks",
                    "success": False,
                    "user_intent": "document_risk_review",
                    "tool_used": "review_document_risks",
                    "answer_mode": "friendly",
                    "execution_strategy_used": "langgraph_context_retry",
                    "workflow_route_decision": "document_risk_review->review_document_risks",
                    "workflow_guardrail_decision": "finish_needs_review_agent",
                    "needs_review": True,
                    "needs_review_reason": "low_grounding",
                    "confidence": 0.58,
                    "source_count": 1,
                    "available_tools_count": 10,
                    "error_tool_runs": 1,
                },
            )

            summary = build_document_agent_runtime_summary(log_path, recent_limit=10)

        self.assertTrue(summary["log_exists"])
        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["needs_review_rate"], 0.5)
        self.assertEqual(summary["tool_counts"]["compare_documents"], 1)
        self.assertEqual(summary["recent_entries"][0]["tool_used"], "review_document_risks")
        self.assertEqual(summary["needs_review_examples"][0]["needs_review_reason"], "low_grounding")

    def test_build_runtime_execution_summary_aggregates_recent_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / ".runtime_execution_log.json"
            append_runtime_execution_log_entry(
                log_path,
                {
                    "timestamp": "2026-03-31T10:00:00",
                    "flow_type": "chat_rag",
                    "task_type": "chat_rag",
                    "success": True,
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                    "latency_s": 1.3,
                    "retrieval_latency_s": 0.2,
                    "generation_latency_s": 0.8,
                    "prompt_tokens": 250,
                    "completion_tokens": 70,
                    "total_tokens": 320,
                    "usage_source": "estimated_chars",
                },
            )
            append_runtime_execution_log_entry(
                log_path,
                {
                    "timestamp": "2026-03-31T10:05:00",
                    "flow_type": "structured",
                    "task_type": "document_agent",
                    "success": False,
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                    "latency_s": 2.7,
                    "needs_review": True,
                    "error_message": "boom",
                    "prompt_tokens": 140,
                    "completion_tokens": 20,
                    "total_tokens": 160,
                    "usage_source": "estimated_chars",
                },
            )

            summary = build_runtime_execution_summary(log_path, recent_limit=10)

        self.assertTrue(summary["log_exists"])
        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["error_rate"], 0.5)
        self.assertEqual(summary["total_tokens"], 480)
        self.assertEqual(summary["avg_total_tokens"], 240.0)
        self.assertEqual(summary["usage_source_counts"]["estimated_chars"], 2)
        self.assertEqual(summary["recent_entries"][0]["task_type"], "document_agent")

    def test_build_runtime_snapshot_exposes_latest_budget_routing_signals(self) -> None:
        structured_result = StructuredResult(
            success=True,
            task_type="summary",
            raw_output_text="{\"ok\": true}",
            parsed_json={"ok": True},
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
                "telemetry": {
                    "budget_routing_mode": "quality_first",
                    "budget_routing_reason": "high_sensitivity_task",
                    "budget_auto_degrade_applied": False,
                    "budget_total_tokens": 280,
                    "budget_cost_usd": None,
                },
            },
        )
        messages = [
            {
                "role": "assistant",
                "metadata": {
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                    "usage": {"total_tokens": 320, "cost_usd": None},
                    "budget_routing_mode": "budget_guarded",
                    "budget_routing_reason": "high_context_pressure",
                    "budget_auto_degrade_applied": True,
                    "budget_alert_status": "warn",
                    "budget_alerts": [{"type": "context_pressure_threshold_exceeded", "severity": "warn"}],
                    "provider_requested": "openai",
                    "provider_effective": "ollama",
                },
            }
        ]

        snapshot = build_runtime_snapshot(
            selected_provider="ollama",
            selected_provider_label="Ollama (local)",
            provider_detail=None,
            selected_model="qwen2.5:7b",
            selected_embedding_provider="ollama",
            selected_embedding_model="embeddinggemma:300m",
            selected_loader_strategy="manual",
            selected_chunking_strategy="manual",
            selected_retrieval_strategy="manual_hybrid",
            selected_pdf_extraction_mode="hybrid",
            chat_selected_document_ids=[],
            structured_selected_document_ids=[],
            selected_structured_task="summary",
            selected_structured_execution_strategy="direct",
            messages=messages,
            structured_result=structured_result,
            structured_task_registry=_DummyStructuredTaskRegistry(),
            document_preview_map={},
            indexed_documents_count=0,
            ollama_base_url="http://localhost:11434",
            default_vl_model="llava",
            default_ocr_backend="ocrmypdf",
        )

        self.assertEqual(snapshot["chat"]["budget_routing_mode"], "budget_guarded")
        self.assertTrue(snapshot["chat"]["budget_auto_degrade_applied"])
        self.assertEqual(snapshot["chat"]["budget_alert_status"], "warn")
        self.assertEqual(snapshot["chat"]["provider_requested"], "openai")
        self.assertEqual(snapshot["chat"]["last_total_tokens"], 320)
        self.assertEqual(snapshot["structured"]["budget_routing_mode"], "quality_first")
        self.assertEqual(snapshot["structured"]["last_total_tokens"], 280)

    def test_build_runtime_snapshot_includes_phase8_eval_summary(self) -> None:
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
            execution_metadata={},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "phase8_eval.sqlite3"
            append_eval_run(
                db_path,
                {
                    "created_at": "2026-03-29T10:00:00",
                    "suite_name": "structured_smoke_eval",
                    "task_type": "summary",
                    "status": "PASS",
                    "score": 5,
                    "max_score": 5,
                },
            )
            snapshot = build_runtime_snapshot(
                selected_provider="ollama",
                selected_provider_label="Ollama (local)",
                provider_detail=None,
                selected_model="qwen2.5:7b",
                selected_embedding_provider="ollama",
                selected_embedding_model="embeddinggemma:300m",
                selected_loader_strategy="manual",
                selected_chunking_strategy="langchain_recursive",
                selected_retrieval_strategy="langchain_chroma",
                selected_pdf_extraction_mode="hybrid",
                chat_selected_document_ids=[],
                structured_selected_document_ids=[],
                selected_structured_task="summary",
                selected_structured_execution_strategy="direct",
                messages=[],
                structured_result=structured_result,
                structured_task_registry=_DummyStructuredTaskRegistry(),
                document_preview_map={},
                indexed_documents_count=0,
                ollama_base_url="http://localhost:11434",
                default_vl_model="llava",
                default_ocr_backend="ocrmypdf",
                phase8_eval_db_path=db_path,
            )

        self.assertIn("evals", snapshot)
        self.assertTrue(snapshot["evals"]["db_exists"])
        self.assertEqual(snapshot["evals"]["total_runs"], 1)
        self.assertEqual(snapshot["evals"]["pass_rate"], 1.0)

    def test_build_runtime_snapshot_includes_phase6_document_agent_summary(self) -> None:
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
            execution_metadata={},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / ".phase6_document_agent_log.json"
            append_document_agent_log_entry(
                log_path,
                {
                    "timestamp": "2026-03-31T10:00:00",
                    "query": "Compare os contratos",
                    "success": True,
                    "user_intent": "document_comparison",
                    "tool_used": "compare_documents",
                    "answer_mode": "comparison_structured",
                    "execution_strategy_used": "langgraph_context_retry",
                    "workflow_route_decision": "document_comparison->compare_documents",
                    "workflow_guardrail_decision": "finish_ok",
                    "needs_review": False,
                    "confidence": 0.81,
                    "source_count": 2,
                    "available_tools_count": 10,
                    "error_tool_runs": 0,
                },
            )

            snapshot = build_runtime_snapshot(
                selected_provider="ollama",
                selected_provider_label="Ollama (local)",
                provider_detail=None,
                selected_model="qwen2.5:7b",
                selected_embedding_provider="ollama",
                selected_embedding_model="embeddinggemma:300m",
                selected_loader_strategy="manual",
                selected_chunking_strategy="langchain_recursive",
                selected_retrieval_strategy="langchain_chroma",
                selected_pdf_extraction_mode="hybrid",
                chat_selected_document_ids=[],
                structured_selected_document_ids=[],
                selected_structured_task="summary",
                selected_structured_execution_strategy="direct",
                messages=[],
                structured_result=structured_result,
                structured_task_registry=_DummyStructuredTaskRegistry(),
                document_preview_map={},
                indexed_documents_count=0,
                ollama_base_url="http://localhost:11434",
                default_vl_model="llava",
                default_ocr_backend="ocrmypdf",
                phase6_document_agent_log_path=log_path,
            )

        self.assertIn("document_agent", snapshot)
        self.assertTrue(snapshot["document_agent"]["log_exists"])
        self.assertEqual(snapshot["document_agent"]["total_runs"], 1)
        self.assertEqual(snapshot["document_agent"]["tool_counts"]["compare_documents"], 1)

    def test_build_runtime_snapshot_includes_phase95_evidenceops_summary(self) -> None:
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
            execution_metadata={},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / ".phase95_evidenceops_worklog.json"
            append_evidenceops_worklog_entry(
                log_path,
                {
                    "timestamp": "2026-04-03T10:00:00",
                    "review_type": "risk_gap_review",
                    "tool_used": "review_document_risks",
                    "confidence": 0.81,
                    "needs_review": False,
                    "document_ids": ["CTR-002"],
                    "source_count": 2,
                    "findings": [{"finding_type": "risk"}, {"finding_type": "gap"}],
                    "action_items": [{"owner": "Legal", "status": "open", "due_date": "2026-05-01"}],
                    "recommended_actions": ["Update clause"],
                },
            )

            snapshot = build_runtime_snapshot(
                selected_provider="ollama",
                selected_provider_label="Ollama (local)",
                provider_detail=None,
                selected_model="qwen2.5:7b",
                selected_embedding_provider="ollama",
                selected_embedding_model="embeddinggemma:300m",
                selected_loader_strategy="manual",
                selected_chunking_strategy="langchain_recursive",
                selected_retrieval_strategy="langchain_chroma",
                selected_pdf_extraction_mode="hybrid",
                chat_selected_document_ids=[],
                structured_selected_document_ids=[],
                selected_structured_task="summary",
                selected_structured_execution_strategy="direct",
                messages=[],
                structured_result=structured_result,
                structured_task_registry=_DummyStructuredTaskRegistry(),
                document_preview_map={},
                indexed_documents_count=0,
                ollama_base_url="http://localhost:11434",
                default_vl_model="llava",
                default_ocr_backend="ocrmypdf",
                phase95_evidenceops_worklog_path=log_path,
            )

        self.assertIn("evidenceops", snapshot)
        self.assertTrue(snapshot["evidenceops"]["log_exists"])
        self.assertEqual(snapshot["evidenceops"]["total_runs"], 1)
        self.assertEqual(snapshot["evidenceops"]["total_findings"], 2)
        self.assertEqual(snapshot["evidenceops"]["finding_type_counts"]["risk"], 1)
        self.assertEqual(snapshot["evidenceops"]["owner_counts"]["Legal"], 1)

    def test_build_runtime_snapshot_includes_phase95_evidenceops_action_store_summary(self) -> None:
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
            execution_metadata={},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / ".phase95_evidenceops_actions.sqlite3"
            append_evidenceops_actions_from_worklog_entry(
                store_path,
                {
                    "timestamp": "2026-04-03T10:00:00",
                    "task_type": "document_agent",
                    "review_type": "risk_gap_review",
                    "tool_used": "review_document_risks",
                    "query": "List the risks",
                    "confidence": 0.81,
                    "needs_review": False,
                    "document_ids": ["CTR-002"],
                    "source_count": 2,
                    "action_items": [
                        {
                            "description": "Request a redline of the incident clause",
                            "owner": "Legal",
                            "due_date": "2026-05-01",
                            "status": "open",
                            "evidence": "notify within 10 business days",
                        }
                    ],
                    "recommended_actions": ["Update clause"],
                },
            )

            snapshot = build_runtime_snapshot(
                selected_provider="ollama",
                selected_provider_label="Ollama (local)",
                provider_detail=None,
                selected_model="qwen2.5:7b",
                selected_embedding_provider="ollama",
                selected_embedding_model="embeddinggemma:300m",
                selected_loader_strategy="manual",
                selected_chunking_strategy="langchain_recursive",
                selected_retrieval_strategy="langchain_chroma",
                selected_pdf_extraction_mode="hybrid",
                chat_selected_document_ids=[],
                structured_selected_document_ids=[],
                selected_structured_task="summary",
                selected_structured_execution_strategy="direct",
                messages=[],
                structured_result=structured_result,
                structured_task_registry=_DummyStructuredTaskRegistry(),
                document_preview_map={},
                indexed_documents_count=0,
                ollama_base_url="http://localhost:11434",
                default_vl_model="llava",
                default_ocr_backend="ocrmypdf",
                phase95_evidenceops_action_store_path=store_path,
            )

        self.assertIn("evidenceops_actions", snapshot)
        self.assertTrue(snapshot["evidenceops_actions"]["store_exists"])
        self.assertEqual(snapshot["evidenceops_actions"]["total_actions"], 2)
        self.assertEqual(snapshot["evidenceops_actions"]["open_actions"], 2)
        self.assertEqual(snapshot["evidenceops_actions"]["owner_counts"]["Legal"], 1)
        self.assertEqual(snapshot["evidenceops_actions"]["pending_approval_actions"], 0)

    def test_build_runtime_snapshot_exposes_action_governance_metrics_after_sensitive_update(self) -> None:
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
            execution_metadata={},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / ".phase95_evidenceops_actions.sqlite3"
            append_evidenceops_actions_from_worklog_entry(
                store_path,
                {
                    "timestamp": "2026-04-03T10:00:00",
                    "task_type": "document_agent",
                    "review_type": "risk_gap_review",
                    "tool_used": "review_document_risks",
                    "query": "List the risks",
                    "confidence": 0.81,
                    "needs_review": False,
                    "document_ids": ["CTR-002"],
                    "source_count": 2,
                    "action_items": [
                        {
                            "description": "Request a redline of the incident clause",
                            "owner": "Legal",
                            "due_date": "2026-05-01",
                            "status": "open",
                            "evidence": "notify within 10 business days",
                        }
                    ],
                },
            )
            from src.services.evidenceops_local_ops import list_evidenceops_action_items, update_evidenceops_action_item

            open_actions = list_evidenceops_action_items(store_path, status="open")
            update_evidenceops_action_item(
                store_path,
                action_id=int(open_actions[0]["id"]),
                status="closed",
                approval_status="approved",
                approval_reason="Closure validated by the responsible manager.",
                approved_by="manager",
            )

            snapshot = build_runtime_snapshot(
                selected_provider="ollama",
                selected_provider_label="Ollama (local)",
                provider_detail=None,
                selected_model="qwen2.5:7b",
                selected_embedding_provider="ollama",
                selected_embedding_model="embeddinggemma:300m",
                selected_loader_strategy="manual",
                selected_chunking_strategy="langchain_recursive",
                selected_retrieval_strategy="langchain_chroma",
                selected_pdf_extraction_mode="hybrid",
                chat_selected_document_ids=[],
                structured_selected_document_ids=[],
                selected_structured_task="summary",
                selected_structured_execution_strategy="direct",
                messages=[],
                structured_result=structured_result,
                structured_task_registry=_DummyStructuredTaskRegistry(),
                document_preview_map={},
                indexed_documents_count=0,
                ollama_base_url="http://localhost:11434",
                default_vl_model="llava",
                default_ocr_backend="ocrmypdf",
                phase95_evidenceops_action_store_path=store_path,
            )

        self.assertEqual(snapshot["evidenceops_actions"]["review_required_actions"], 1)
        self.assertEqual(snapshot["evidenceops_actions"]["approved_actions"], 1)
        self.assertEqual(snapshot["evidenceops_actions"]["sensitive_update_count"], 1)

    def test_build_runtime_snapshot_includes_phase95_evidenceops_repository_summary(self) -> None:
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
            execution_metadata={},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            repository_root = Path(tmp_dir) / "evidenceops_repo"
            (repository_root / "policies").mkdir(parents=True)
            (repository_root / "contracts").mkdir(parents=True)
            (repository_root / "policies" / "POL-001_Information_Security_Policy_v1.pdf").write_text("policy", encoding="utf-8")
            (repository_root / "contracts" / "CTR-001_Master_Services_Agreement.txt").write_text("contract", encoding="utf-8")

            snapshot = build_runtime_snapshot(
                selected_provider="ollama",
                selected_provider_label="Ollama (local)",
                provider_detail=None,
                selected_model="qwen2.5:7b",
                selected_embedding_provider="ollama",
                selected_embedding_model="embeddinggemma:300m",
                selected_loader_strategy="manual",
                selected_chunking_strategy="langchain_recursive",
                selected_retrieval_strategy="langchain_chroma",
                selected_pdf_extraction_mode="hybrid",
                chat_selected_document_ids=[],
                structured_selected_document_ids=[],
                selected_structured_task="summary",
                selected_structured_execution_strategy="direct",
                messages=[],
                structured_result=structured_result,
                structured_task_registry=_DummyStructuredTaskRegistry(),
                document_preview_map={},
                indexed_documents_count=0,
                ollama_base_url="http://localhost:11434",
                default_vl_model="llava",
                default_ocr_backend="ocrmypdf",
                phase95_evidenceops_repository_root=repository_root,
            )

        self.assertIn("evidenceops_repository", snapshot)
        self.assertTrue(snapshot["evidenceops_repository"]["repository_exists"])
        self.assertEqual(snapshot["evidenceops_repository"]["total_documents"], 2)
        self.assertEqual(snapshot["evidenceops_repository"]["category_counts"]["policies"], 1)
        self.assertEqual(snapshot["evidenceops_repository"]["category_counts"]["contracts"], 1)

    def test_build_runtime_snapshot_exposes_repository_drift_summary(self) -> None:
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
            execution_metadata={},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            repository_root = Path(tmp_dir) / "evidenceops_repo"
            snapshot_path = repository_root / ".phase95_evidenceops_repository_snapshot.json"
            (repository_root / "policies").mkdir(parents=True)
            (repository_root / "contracts").mkdir(parents=True)
            policy_path = repository_root / "policies" / "POL-001_Information_Security_Policy_v1.pdf"
            contract_path = repository_root / "contracts" / "CTR-001_Master_Services_Agreement.txt"
            policy_path.write_text("policy-v1", encoding="utf-8")
            contract_path.write_text("contract", encoding="utf-8")

            build_runtime_snapshot(
                selected_provider="ollama",
                selected_provider_label="Ollama (local)",
                provider_detail=None,
                selected_model="qwen2.5:7b",
                selected_embedding_provider="ollama",
                selected_embedding_model="embeddinggemma:300m",
                selected_loader_strategy="manual",
                selected_chunking_strategy="langchain_recursive",
                selected_retrieval_strategy="langchain_chroma",
                selected_pdf_extraction_mode="hybrid",
                chat_selected_document_ids=[],
                structured_selected_document_ids=[],
                selected_structured_task="summary",
                selected_structured_execution_strategy="direct",
                messages=[],
                structured_result=structured_result,
                structured_task_registry=_DummyStructuredTaskRegistry(),
                document_preview_map={},
                indexed_documents_count=0,
                ollama_base_url="http://localhost:11434",
                default_vl_model="llava",
                default_ocr_backend="ocrmypdf",
                phase95_evidenceops_repository_root=repository_root,
                phase95_evidenceops_repository_snapshot_path=snapshot_path,
            )

            policy_path.write_text("policy-v2", encoding="utf-8")
            contract_path.unlink()
            (repository_root / "audit").mkdir(parents=True)
            (repository_root / "audit" / "AUD-001_Control_Test.md").write_text("audit", encoding="utf-8")

            snapshot = build_runtime_snapshot(
                selected_provider="ollama",
                selected_provider_label="Ollama (local)",
                provider_detail=None,
                selected_model="qwen2.5:7b",
                selected_embedding_provider="ollama",
                selected_embedding_model="embeddinggemma:300m",
                selected_loader_strategy="manual",
                selected_chunking_strategy="langchain_recursive",
                selected_retrieval_strategy="langchain_chroma",
                selected_pdf_extraction_mode="hybrid",
                chat_selected_document_ids=[],
                structured_selected_document_ids=[],
                selected_structured_task="summary",
                selected_structured_execution_strategy="direct",
                messages=[],
                structured_result=structured_result,
                structured_task_registry=_DummyStructuredTaskRegistry(),
                document_preview_map={},
                indexed_documents_count=0,
                ollama_base_url="http://localhost:11434",
                default_vl_model="llava",
                default_ocr_backend="ocrmypdf",
                phase95_evidenceops_repository_root=repository_root,
                phase95_evidenceops_repository_snapshot_path=snapshot_path,
            )

        drift_summary = snapshot["evidenceops_repository"]["drift_summary"]
        self.assertTrue(drift_summary["has_previous_snapshot"])
        self.assertEqual(drift_summary["changed_documents_count"], 1)
        self.assertEqual(drift_summary["removed_documents_count"], 1)
        self.assertEqual(drift_summary["new_documents_count"], 1)
        self.assertEqual(snapshot["evidenceops_repository"]["changed_documents"][0]["document_id"], "POL-001")

    def test_build_runtime_snapshot_includes_runtime_execution_summary(self) -> None:
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
            execution_metadata={},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / ".runtime_execution_log.json"
            append_runtime_execution_log_entry(
                log_path,
                {
                    "timestamp": "2026-03-31T10:00:00",
                    "flow_type": "chat_rag",
                    "task_type": "chat_rag",
                    "success": True,
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                    "latency_s": 1.3,
                },
            )

            snapshot = build_runtime_snapshot(
                selected_provider="ollama",
                selected_provider_label="Ollama (local)",
                provider_detail=None,
                selected_model="qwen2.5:7b",
                selected_embedding_provider="ollama",
                selected_embedding_model="embeddinggemma:300m",
                selected_loader_strategy="manual",
                selected_chunking_strategy="langchain_recursive",
                selected_retrieval_strategy="langchain_chroma",
                selected_pdf_extraction_mode="hybrid",
                chat_selected_document_ids=[],
                structured_selected_document_ids=[],
                selected_structured_task="summary",
                selected_structured_execution_strategy="direct",
                messages=[],
                structured_result=structured_result,
                structured_task_registry=_DummyStructuredTaskRegistry(),
                document_preview_map={},
                indexed_documents_count=0,
                ollama_base_url="http://localhost:11434",
                default_vl_model="llava",
                default_ocr_backend="ocrmypdf",
                runtime_execution_log_path=log_path,
            )

        self.assertIn("runtime_execution", snapshot)
        self.assertTrue(snapshot["runtime_execution"]["log_exists"])
        self.assertEqual(snapshot["runtime_execution"]["total_runs"], 1)
        self.assertEqual(snapshot["runtime_execution"]["flow_counts"]["chat_rag"], 1)

    def test_build_runtime_snapshot_reports_huggingface_server_route(self) -> None:
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
            execution_metadata={},
        )

        snapshot = build_runtime_snapshot(
            selected_provider="huggingface_server",
            selected_provider_label="Hugging Face server local",
            provider_detail="Local server configured at `http://127.0.0.1:8788/v1`",
            selected_model="service-chat",
            selected_embedding_provider="huggingface_server",
            selected_embedding_model="service-embed",
            selected_loader_strategy="manual",
            selected_chunking_strategy="langchain_recursive",
            selected_retrieval_strategy="langchain_chroma",
            selected_pdf_extraction_mode="hybrid",
            chat_selected_document_ids=[],
            structured_selected_document_ids=[],
            selected_structured_task="summary",
            selected_structured_execution_strategy="direct",
            messages=[],
            structured_result=structured_result,
            structured_task_registry=_DummyStructuredTaskRegistry(),
            document_preview_map={},
            indexed_documents_count=0,
            ollama_base_url="http://localhost:11434",
            default_vl_model="llava",
            default_ocr_backend="ocrmypdf",
        )

        self.assertIn("AI hub local", snapshot["provider_path"])
        self.assertIn("effective backend may vary", snapshot["local_dependency"])


if __name__ == "__main__":
    unittest.main()