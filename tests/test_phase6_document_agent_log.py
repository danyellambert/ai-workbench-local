import unittest

from src.storage.phase6_document_agent_log import summarize_document_agent_log


class Phase6DocumentAgentLogTests(unittest.TestCase):
    def test_summarize_document_agent_log_aggregates_metrics(self) -> None:
        entries = [
            {
                "success": True,
                "user_intent": "document_question",
                "tool_used": "consult_documents",
                "answer_mode": "friendly",
                "execution_strategy_used": "langgraph_context_retry",
                "needs_review": False,
                "confidence": 0.82,
                "source_count": 3,
                "available_tools_count": 5,
                "error_tool_runs": 0,
            },
            {
                "success": False,
                "user_intent": "document_comparison",
                "tool_used": "compare_documents",
                "answer_mode": "comparison_structured",
                "execution_strategy_used": "langgraph_context_retry",
                "needs_review": True,
                "needs_review_reason": "comparison_grounding_is_partial",
                "confidence": 0.61,
                "source_count": 1,
                "available_tools_count": 5,
                "error_tool_runs": 1,
            },
        ]
        summary = summarize_document_agent_log(entries)
        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["needs_review_rate"], 0.5)
        self.assertEqual(summary["avg_confidence"], 0.715)
        self.assertEqual(summary["avg_source_count"], 2.0)
        self.assertEqual(summary["runs_with_tool_errors"], 1)
        self.assertEqual(summary["intent_counts"]["document_question"], 1)
        self.assertEqual(summary["tool_counts"]["compare_documents"], 1)
        self.assertEqual(summary["review_reasons"]["comparison_grounding_is_partial"], 1)