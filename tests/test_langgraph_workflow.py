import unittest
from unittest.mock import patch

from src.structured.envelope import StructuredResult, TaskExecutionRequest
import src.structured.langgraph_workflow as workflow


def _make_result(*, success: bool = True, quality_score: float | None = 0.9, execution_metadata: dict | None = None) -> StructuredResult:
    return StructuredResult(
        success=success,
        task_type="summary",
        parsed_json={},
        execution_metadata=execution_metadata or {},
        quality_score=quality_score,
    )


class LanggraphWorkflowTests(unittest.TestCase):
    def test_select_initial_context_strategy_prefers_retrieval_for_query_driven_summary(self) -> None:
        request = TaskExecutionRequest(
            task_type="summary",
            input_text="Faça um resumo focando nos pontos financeiros e de governança do documento.",
            use_document_context=True,
            source_document_ids=["doc-1"],
            context_strategy="",
        )
        strategy, reason = workflow._select_initial_context_strategy(request)
        self.assertEqual(strategy, "retrieval")
        self.assertEqual(reason, "query_driven_task_prefers_retrieval")

    def test_evaluate_guardrails_requests_retry_after_failed_document_scan(self) -> None:
        request = TaskExecutionRequest(
            task_type="extraction",
            input_text="",
            use_document_context=True,
            source_document_ids=["doc-1"],
            context_strategy="document_scan",
        )
        state = {
            "result": _make_result(success=False, quality_score=0.0),
            "effective_request": request,
            "attempt": 1,
            "max_attempts": 2,
            "workflow_trace": [],
        }
        updated = workflow._evaluate_guardrails(state)
        self.assertEqual(updated["guardrail_decision"], "retry_with_retrieval_after_failure")
        self.assertEqual(updated["retry_reason"], "structured_result_failed_under_document_scan")

    def test_evaluate_guardrails_marks_needs_review_on_low_quality_without_retry(self) -> None:
        request = TaskExecutionRequest(
            task_type="summary",
            input_text="Resumo do documento",
            use_document_context=True,
            source_document_ids=["doc-1"],
            context_strategy="retrieval",
        )
        state = {
            "result": _make_result(success=True, quality_score=0.7),
            "effective_request": request,
            "attempt": 2,
            "max_attempts": 2,
            "workflow_trace": [],
        }
        updated = workflow._evaluate_guardrails(state)
        self.assertEqual(updated["guardrail_decision"], "finish_needs_review_low_quality")
        self.assertTrue(updated["needs_review"])

    def test_run_structured_execution_workflow_records_direct_timing_and_metadata(self) -> None:
        request = TaskExecutionRequest(task_type="summary", input_text="Resumo")
        with patch("src.structured.service.structured_service.execute_task", return_value=_make_result()):
            result = workflow.run_structured_execution_workflow(request, strategy="direct")

        self.assertEqual(result.execution_metadata["execution_strategy_used"], "direct")
        self.assertIsInstance(result.execution_metadata.get("workflow_total_s"), float)
        self.assertGreaterEqual(result.execution_metadata["workflow_node_count"], 1)

    def test_run_structured_execution_workflow_records_fallback_when_langgraph_not_available(self) -> None:
        request = TaskExecutionRequest(task_type="summary", input_text="Resumo")
        with patch.object(
            workflow,
            "resolve_structured_execution_strategy",
            return_value=("langgraph_context_retry", "direct", "langgraph_not_installed"),
        ):
            with patch("src.structured.service.structured_service.execute_task", return_value=_make_result()):
                result = workflow.run_structured_execution_workflow(request, strategy="langgraph_context_retry")

        self.assertEqual(result.execution_metadata["execution_strategy_requested"], "langgraph_context_retry")
        self.assertEqual(result.execution_metadata["execution_strategy_used"], "direct")
        self.assertEqual(result.execution_metadata["execution_strategy_fallback_reason"], "langgraph_not_installed")

    def test_run_structured_execution_workflow_annotates_langgraph_state_from_fake_app(self) -> None:
        request = TaskExecutionRequest(task_type="summary", input_text="Resumo")
        fake_result = _make_result(success=True, quality_score=0.92)

        class FakeApp:
            def invoke(self, _state: dict[str, object]) -> dict[str, object]:
                return {
                    "workflow_id": "lgw-test",
                    "result": fake_result,
                    "route_decision": "test_route",
                    "guardrail_decision": "finish_ok",
                    "attempt_context_strategies": ["document_scan"],
                    "workflow_trace": [
                        {
                            "node": "prepare_request",
                            "detail": "fake",
                            "attempt": 1,
                            "context_strategy": "document_scan",
                            "success": True,
                        }
                    ],
                    "needs_review": False,
                }

        with patch.object(
            workflow,
            "resolve_structured_execution_strategy",
            return_value=("langgraph_context_retry", "langgraph_context_retry", None),
        ):
            with patch.object(workflow, "_build_langgraph_app", return_value=FakeApp()):
                result = workflow.run_structured_execution_workflow(request, strategy="langgraph_context_retry")

        self.assertEqual(result.execution_metadata["workflow_id"], "lgw-test")
        self.assertEqual(result.execution_metadata["workflow_route_decision"], "test_route")
        self.assertEqual(result.execution_metadata["workflow_guardrail_decision"], "finish_ok")
        self.assertIsInstance(result.execution_metadata.get("workflow_total_s"), float)


if __name__ == "__main__":
    unittest.main()
