import unittest

from src.config import get_rag_settings
from src.services.model_comparison import (
    MODEL_COMPARISON_USE_CASE_PRESETS,
    build_model_comparison_ranking,
    estimate_response_format_adherence,
    estimate_groundedness_score,
    estimate_schema_adherence_score,
    infer_model_comparison_quantization_family,
    infer_model_comparison_runtime_bucket,
    run_model_comparison_candidate,
    summarize_model_comparison_results,
)


class _DummyProvider:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self._last_usage_metrics = {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20,
            "usage_source": "dummy_usage",
        }

    def stream_chat_completion(self, messages, model, temperature, context_window=None, top_p=None, max_tokens=None, think=None):
        return [self.response_text]

    @staticmethod
    def iter_stream_text(stream):
        for item in stream:
            yield item

    def get_last_usage_metrics(self):
        return dict(self._last_usage_metrics)


class ModelComparisonServiceTests(unittest.TestCase):
    def test_estimate_response_format_adherence_handles_json_and_bullets(self) -> None:
        self.assertEqual(estimate_response_format_adherence('{"ok": true}', "json"), 1.0)
        self.assertEqual(estimate_response_format_adherence("- a\n- b", "bullet_list"), 1.0)
        self.assertEqual(estimate_response_format_adherence("texto comum", "plain_text"), 1.0)

    def test_run_model_comparison_candidate_collects_metrics(self) -> None:
        registry = {
            "ollama": {
                "label": "Ollama (local)",
                "instance": _DummyProvider("- item 1\n- item 2"),
                "supports_chat": True,
                "default_model": "qwen2.5:7b",
                "default_context_window": 8192,
            }
        }
        result = run_model_comparison_candidate(
            registry=registry,
            provider_name="ollama",
            model_name="qwen2.5:7b",
            prompt_profile="neutro",
            prompt_text="Liste os principais pontos.",
            benchmark_use_case="executive_summary",
            response_format="bullet_list",
            temperature=0.1,
            context_window=8192,
            retrieved_chunks=[],
            rag_settings=get_rag_settings(),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["provider_effective"], "ollama")
        self.assertEqual(result["model_effective"], "qwen2.5:7b")
        self.assertGreater(result["output_chars"], 0)
        self.assertEqual(result["format_adherence"], 1.0)
        self.assertGreaterEqual(float(result["use_case_fit_score"]), 0.5)
        self.assertEqual(result["total_tokens"], 20)
        self.assertEqual(result["usage_source"], "dummy_usage")
        self.assertEqual(result["total_wall_time_status"], "measured")
        self.assertEqual(result["ttft_status"], "measured")
        self.assertEqual(result["throughput_status"], "measured")
        self.assertIsNotNone(result["ttft_s"])
        self.assertGreater(float(result["throughput_tokens_per_s"]), 0.0)
        self.assertEqual(result["cold_start_status"], "not_supported")
        self.assertEqual(result["memory_status"], "not_supported")

    def test_run_model_comparison_candidate_marks_empty_response_as_failure(self) -> None:
        registry = {
            "ollama": {
                "label": "Ollama (local)",
                "instance": _DummyProvider(""),
                "supports_chat": True,
                "default_model": "qwen2.5:7b",
                "default_context_window": 8192,
            }
        }

        result = run_model_comparison_candidate(
            registry=registry,
            provider_name="ollama",
            model_name="qwen2.5:7b",
            prompt_profile="neutro",
            prompt_text="Liste os principais pontos.",
            benchmark_use_case="executive_summary",
            response_format="bullet_list",
            temperature=0.1,
            context_window=8192,
            retrieved_chunks=[],
            rag_settings=get_rag_settings(),
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "empty_response_text")

    def test_summarize_model_comparison_results_aggregates_metrics(self) -> None:
        summary = summarize_model_comparison_results(
            [
                {
                    "provider_effective": "ollama",
                    "model_effective": "qwen2.5:7b",
                    "success": True,
                    "latency_s": 1.2,
                    "output_chars": 120,
                    "output_words": 20,
                    "format_adherence": 1.0,
                },
                {
                    "provider_effective": "openai",
                    "model_effective": "gpt-4o-mini",
                    "success": True,
                    "latency_s": 0.8,
                    "output_chars": 100,
                    "output_words": 18,
                    "format_adherence": 0.7,
                },
            ]
        )
        self.assertEqual(summary["total_candidates"], 2)
        self.assertEqual(summary["success_rate"], 1.0)
        self.assertEqual(summary["avg_latency_s"], 1.0)
        self.assertEqual(summary["best_latency_candidate"]["model"], "gpt-4o-mini")
        self.assertEqual(summary["best_overall_candidate"]["model"], "qwen2.5:7b")
        self.assertEqual(len(summary["candidate_ranking"]), 2)

    def test_estimate_groundedness_score_uses_retrieved_chunks(self) -> None:
        score = estimate_groundedness_score(
            "RAG usa documentos externos para melhorar respostas.",
            [{"text": "Documentos externos ajudam o RAG a melhorar respostas e reduzir alucinações."}],
        )
        self.assertIsNotNone(score)
        self.assertGreater(float(score or 0.0), 0.2)

    def test_estimate_schema_adherence_score_validates_structured_extraction_keys(self) -> None:
        score = estimate_schema_adherence_score(
            '{"summary": "ok", "risks": [], "actions": ["a"], "entities": ["x"]}',
            "json",
            "structured_extraction",
        )
        self.assertEqual(score, 1.0)

    def test_build_model_comparison_ranking_prioritizes_success_format_and_latency(self) -> None:
        ranking = build_model_comparison_ranking(
            [
                {
                    "provider_effective": "ollama",
                    "model_effective": "slow-model",
                    "success": True,
                    "latency_s": 2.0,
                    "output_chars": 100,
                    "output_words": 15,
                    "format_adherence": 1.0,
                    "used_chunks": 2,
                },
                {
                    "provider_effective": "openai",
                    "model_effective": "fast-model",
                    "success": True,
                    "latency_s": 1.0,
                    "output_chars": 90,
                    "output_words": 14,
                    "format_adherence": 1.0,
                    "used_chunks": 2,
                },
            ]
        )
        self.assertEqual(ranking[0]["model"], "fast-model")

    def test_infer_model_comparison_runtime_bucket_distinguishes_local_cloud_and_experimental(self) -> None:
        self.assertEqual(infer_model_comparison_runtime_bucket("ollama", "qwen2.5:7b"), "local")
        self.assertEqual(infer_model_comparison_runtime_bucket("ollama", "nemotron-3-super:cloud"), "cloud")
        self.assertEqual(infer_model_comparison_runtime_bucket("openai", "gpt-4o-mini"), "cloud")
        self.assertEqual(infer_model_comparison_runtime_bucket("huggingface_inference", "meta-llama/Llama-3.1-8B-Instruct"), "cloud")
        self.assertEqual(infer_model_comparison_runtime_bucket("huggingface_local", "Qwen/Qwen2.5-7B-Instruct"), "experimental_local")
        self.assertEqual(infer_model_comparison_runtime_bucket("huggingface_server", "service-chat"), "local")

    def test_infer_model_comparison_quantization_family_handles_common_suffixes(self) -> None:
        self.assertEqual(infer_model_comparison_quantization_family("ollama", "llama3.1:8b-instruct-q4_K_M"), "q4")
        self.assertEqual(infer_model_comparison_quantization_family("ollama", "phi4:14b-q8_0"), "q8")
        self.assertEqual(infer_model_comparison_quantization_family("openai", "gpt-4o-mini"), "cloud_managed")
        self.assertEqual(infer_model_comparison_quantization_family("huggingface_inference", "meta-llama/Llama-3.1-8B-Instruct"), "cloud_managed")

    def test_model_comparison_use_case_presets_expose_structured_defaults(self) -> None:
        self.assertIn("executive_summary", MODEL_COMPARISON_USE_CASE_PRESETS)
        self.assertEqual(MODEL_COMPARISON_USE_CASE_PRESETS["structured_extraction"]["response_format"], "json")