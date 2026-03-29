import tempfile
import unittest
from pathlib import Path

from src.evals.phase8_agent_workflow import (
    evaluate_routing_case,
    evaluate_workflow_case,
    load_phase8_agent_workflow_cases,
    summarize_phase8_case_results,
)


class Phase8AgentWorkflowEvalTests(unittest.TestCase):
    def test_evaluate_routing_case_returns_pass_for_expected_mapping(self) -> None:
        result = evaluate_routing_case(
            {
                "case_id": "comparison",
                "input_text": "Compare estes dois contratos e destaque as diferenças.",
                "document_count": 2,
                "expected_intent": "document_comparison",
                "expected_tool": "compare_documents",
                "expected_answer_mode": "comparison_structured",
                "expected_context_strategy": "retrieval",
            }
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["score"], 4)
        self.assertEqual(result["suite_name"], "document_agent_routing_eval")

    def test_evaluate_workflow_case_returns_pass_for_expected_retry(self) -> None:
        result = evaluate_workflow_case(
            {
                "case_id": "structured_failed_scan_retry",
                "workflow_type": "structured",
                "task_type": "extraction",
                "input_text": "Extraia os campos",
                "document_count": 1,
                "context_strategy": "document_scan",
                "result": {"success": False, "quality_score": 0.0},
                "expected_guardrail_decision": "retry_with_retrieval_after_failure",
                "expected_transition": "retry_with_retrieval",
                "retry_expected": True,
                "needs_review_expected": False,
            }
        )
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["metrics"]["retry_actual"])
        self.assertEqual(result["metadata"]["actual_transition"], "retry_with_retrieval")

    def test_load_cases_and_summarize_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            fixture_path = Path(tmp_dir) / "cases.json"
            fixture_path.write_text(
                '{"routing_cases": [{"case_id": "r1"}], "workflow_cases": [{"case_id": "w1"}]}',
                encoding="utf-8",
            )
            payload = load_phase8_agent_workflow_cases(fixture_path)
            self.assertEqual(len(payload["routing_cases"]), 1)
            self.assertEqual(len(payload["workflow_cases"]), 1)

            summary = summarize_phase8_case_results(
                [
                    {"status": "PASS", "score": 4, "max_score": 4, "latency_s": 0.001, "reasons": []},
                    {"status": "WARN", "score": 3, "max_score": 4, "latency_s": 0.002, "reasons": ["tool_correct"]},
                ],
                suite_name="document_agent_routing_eval",
            )
            self.assertEqual(summary["total_cases"], 2)
            self.assertEqual(summary["pass_rate"], 0.5)
            self.assertEqual(summary["warn_rate"], 0.5)