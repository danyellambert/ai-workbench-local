import unittest

from src.storage.phase7_model_comparison_log import summarize_model_comparison_log


class Phase7ModelComparisonLogTests(unittest.TestCase):
    def test_summarize_model_comparison_log_aggregates_candidates(self) -> None:
        entries = [
            {
                "benchmark_use_case": "executive_summary",
                "prompt_profile": "neutro",
                "response_format": "bullet_list",
                "retrieval_strategy": "manual_hybrid",
                "embedding_provider": "ollama",
                "embedding_model": "embeddinggemma:300m",
                "use_documents": True,
                "aggregate": {
                    "total_candidates": 2,
                    "success_rate": 0.5,
                    "avg_latency_s": 1.0,
                    "avg_output_chars": 60.0,
                    "avg_format_adherence": 0.5,
                    "avg_groundedness_score": 0.4,
                    "avg_schema_adherence": 0.0,
                    "avg_use_case_fit_score": 0.6,
                },
                "candidate_results": [
                    {
                        "provider_effective": "ollama",
                        "model_effective": "qwen2.5:7b",
                        "runtime_bucket": "local",
                        "quantization_family": "unspecified_local",
                        "success": True,
                        "latency_s": 1.1,
                        "output_chars": 120,
                        "format_adherence": 1.0,
                        "groundedness_score": 0.8,
                        "use_case_fit_score": 0.9,
                    },
                    {
                        "provider_effective": "openai",
                        "model_effective": "gpt-4o-mini",
                        "runtime_bucket": "cloud",
                        "quantization_family": "cloud_managed",
                        "success": False,
                        "latency_s": 0.9,
                        "output_chars": 0,
                        "format_adherence": 0.0,
                        "groundedness_score": 0.0,
                        "use_case_fit_score": 0.3,
                    },
                ],
            }
        ]
        summary = summarize_model_comparison_log(entries)
        self.assertEqual(summary["total_runs"], 1)
        self.assertEqual(summary["total_candidates"], 2)
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["provider_counts"]["ollama"], 1)
        self.assertEqual(summary["model_counts"]["gpt-4o-mini"], 1)
        self.assertEqual(summary["format_counts"]["bullet_list"], 1)
        self.assertEqual(summary["runtime_bucket_counts"]["local"], 1)
        self.assertEqual(summary["runtime_bucket_counts"]["cloud"], 1)
        self.assertEqual(summary["quantization_family_counts"]["unspecified_local"], 1)
        self.assertEqual(summary["quantization_family_counts"]["cloud_managed"], 1)
        self.assertEqual(summary["top_provider"]["provider"], "ollama")
        self.assertEqual(summary["top_model"]["model"], "ollama" if False else "qwen2.5:7b")
        self.assertEqual(summary["top_format"]["response_format"], "bullet_list")
        self.assertEqual(summary["top_runtime_bucket"]["runtime_bucket"], "local")
        self.assertEqual(len(summary["provider_leaderboard"]), 2)
        self.assertEqual(summary["quantization_family_leaderboard"][0]["quantization_family"], "unspecified_local")
        self.assertEqual(summary["retrieval_strategy_leaderboard"][0]["retrieval_strategy"], "manual_hybrid")
        self.assertEqual(summary["embedding_provider_leaderboard"][0]["embedding_provider"], "ollama")
        self.assertEqual(summary["embedding_model_leaderboard"][0]["embedding_model"], "embeddinggemma:300m")
        self.assertEqual(summary["prompt_profile_leaderboard"][0]["prompt_profile"], "neutro")
        self.assertEqual(summary["document_usage_leaderboard"][0]["document_usage"], "with_documents")
        self.assertEqual(summary["benchmark_use_case_leaderboard"][0]["benchmark_use_case"], "executive_summary")
        self.assertEqual(summary["avg_groundedness_score"], 0.4)
        self.assertEqual(summary["avg_use_case_fit_score"], 0.6)

    def test_summarize_model_comparison_log_infers_runtime_bucket_for_legacy_entries(self) -> None:
        entries = [
            {
                "response_format": "plain_text",
                "candidate_results": [
                    {
                        "provider_effective": "ollama",
                        "model_effective": "qwen2.5:7b",
                        "success": True,
                        "latency_s": 1.0,
                        "output_chars": 100,
                        "format_adherence": 1.0,
                    },
                    {
                        "provider_effective": "openai",
                        "model_effective": "gpt-4o-mini",
                        "success": True,
                        "latency_s": 0.8,
                        "output_chars": 90,
                        "format_adherence": 1.0,
                    },
                ],
            }
        ]
        summary = summarize_model_comparison_log(entries)
        self.assertEqual(summary["runtime_bucket_counts"]["local"], 1)
        self.assertEqual(summary["runtime_bucket_counts"]["cloud"], 1)