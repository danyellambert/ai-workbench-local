import unittest

from src.storage.phase55_langgraph_shadow_log import summarize_langgraph_shadow_log


class Phase55LanggraphShadowLogTests(unittest.TestCase):
    def test_summarize_langgraph_shadow_log_aggregates_metrics(self) -> None:
        entries = [
            {
                "primary_strategy_used": "direct",
                "alternate_strategy_used": "langgraph_context_retry",
                "same_success": True,
                "latency_delta_s": 0.2,
                "quality_delta": 0.1,
                "alternate_better_quality": True,
                "primary_better_quality": False,
                "alternate_faster": False,
                "primary_faster": True,
                "alternate_avoided_review": True,
            },
            {
                "primary_strategy_used": "langgraph_context_retry",
                "alternate_strategy_used": "direct",
                "same_success": False,
                "latency_delta_s": -0.3,
                "quality_delta": -0.2,
                "alternate_better_quality": False,
                "primary_better_quality": True,
                "alternate_faster": True,
                "primary_faster": False,
                "alternate_avoided_review": False,
                "alternate_fallback_reason": "langgraph_not_installed",
            },
        ]
        summary = summarize_langgraph_shadow_log(entries)
        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(summary["same_success_rate"], 0.5)
        self.assertEqual(summary["avg_latency_delta_s"], -0.05)
        self.assertEqual(summary["avg_quality_delta"], -0.05)
        self.assertEqual(summary["alternate_better_quality_count"], 1)
        self.assertEqual(summary["primary_better_quality_count"], 1)
        self.assertEqual(summary["alternate_avoided_review_count"], 1)
        self.assertEqual(summary["alternate_fallbacks"]["langgraph_not_installed"], 1)


if __name__ == "__main__":
    unittest.main()