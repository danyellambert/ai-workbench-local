import json
import tempfile
import unittest
from pathlib import Path

from src.services.phase8_5_benchmark import (
    DEFAULT_PHASE8_5_MANIFEST_PATH,
    aggregate_case_results,
    build_case_id,
    build_preflight_payload,
    build_run_id,
    classify_runtime_path,
    load_benchmark_manifest,
    load_successful_case_ids,
    normalize_case_results,
    validate_benchmark_manifest,
)
from src.services.runtime_snapshot import build_benchmark_environment_snapshot


class _FakeOllamaProvider:
    def _discover_local_models(self):
        return [
            "qwen2.5:7b",
            "qwen2.5-coder:7b",
            "embeddinggemma:300m",
            "bge-m3:latest",
            "qwen3-embedding:0.6b",
        ]

    @staticmethod
    def _looks_like_embedding_model(model: str) -> bool:
        normalized = str(model).lower()
        return "embed" in normalized or "embedding" in normalized or "bge" in normalized


class Phase85BenchmarkTests(unittest.TestCase):
    def test_load_benchmark_manifest_reads_repo_manifest(self) -> None:
        manifest = load_benchmark_manifest(DEFAULT_PHASE8_5_MANIFEST_PATH)

        self.assertEqual(manifest["benchmark_id"], "phase8_5_round1")
        self.assertIn("generation", manifest["groups"])
        self.assertIn("embeddings", manifest["groups"])

    def test_validate_benchmark_manifest_rejects_missing_required_keys(self) -> None:
        with self.assertRaises(ValueError):
            validate_benchmark_manifest({"benchmark_id": "phase8_5_round1"})

    def test_build_case_id_is_stable_for_same_payload(self) -> None:
        payload = {
            "group": "generation",
            "provider": "ollama",
            "model": "qwen2.5:7b",
            "case_name": "ops_update_summary",
            "use_case_id": "ops_update_summary",
            "input_file": "phase5_eval/fixtures/02_summary_input.txt",
            "prompt_profile": "neutro",
            "response_format": "bullet_list",
            "temperature": 0.2,
            "context_window": 8192,
            "repetition": 1,
        }

        self.assertEqual(build_case_id(payload), build_case_id(payload))

    def test_build_run_id_is_stable_for_same_selection(self) -> None:
        manifest = load_benchmark_manifest(DEFAULT_PHASE8_5_MANIFEST_PATH)

        run_id_a = build_run_id(
            manifest,
            selected_groups=["generation", "embeddings"],
            provider_filter=None,
            model_filter=None,
            smoke=True,
        )
        run_id_b = build_run_id(
            manifest,
            selected_groups=["generation", "embeddings"],
            provider_filter=None,
            model_filter=None,
            smoke=True,
        )

        self.assertEqual(run_id_a, run_id_b)

    def test_load_successful_case_ids_only_returns_successful_case_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            events_path = Path(tmp_dir) / "events.jsonl"
            events_path.write_text(
                "\n".join(
                    [
                        json.dumps({"event_type": "run_started", "run_id": "run-1"}),
                        json.dumps({"event_type": "case_result", "case_id": "case_ok", "status": "success"}),
                        json.dumps({"event_type": "case_result", "case_id": "case_fail", "status": "failed"}),
                        "not-json",
                    ]
                ),
                encoding="utf-8",
            )

            successful_ids = load_successful_case_ids(events_path)

        self.assertEqual(successful_ids, {"case_ok"})

    def test_normalize_case_results_splits_generation_embedding_and_question_rows(self) -> None:
        normalized = normalize_case_results(
            [
                {
                    "run_id": "run-1",
                    "case_id": "case-gen",
                    "group": "generation",
                    "status": "success",
                    "provider_requested": "ollama",
                    "provider_effective": "ollama",
                    "model_requested": "qwen2.5:7b",
                    "model_effective": "qwen2.5:7b",
                    "group_id": "g1",
                    "use_case_id": "ops_update_summary",
                    "benchmark_use_case": "executive_summary",
                    "prompt_profile": "neutro",
                    "response_format": "bullet_list",
                    "structured_output_mode": "bullet_prompt_contract",
                    "temperature": 0.2,
                    "context_window": 8192,
                    "repetition": 1,
                    "runtime_bucket": "local",
                    "quantization_family": "unspecified_local",
                    "latency_s": 1.1,
                    "output_chars": 120,
                    "output_words": 20,
                    "format_adherence": 1.0,
                    "groundedness_score": 0.8,
                    "schema_adherence": None,
                    "use_case_fit_score": 0.9,
                    "prompt_tokens": 20,
                    "completion_tokens": 30,
                    "total_tokens": 50,
                    "usage_source": "dummy",
                    "runtime_path": "direct_runtime",
                    "runtime_path_label": "Direct runtime",
                    "backend_equivalence_type": "native_runtime",
                    "backend_provider_resolved": "ollama",
                    "backend_model_ref_resolved": "qwen2.5:7b",
                    "backend_equivalence_key": "ollama::qwen2.5:7b",
                    "equivalent_direct_runtime_key": "ollama::qwen2.5:7b",
                    "path_overhead_expected": False,
                    "path_comparison_note": "Direct provider path with no hub-wrapper layer.",
                    "seed_requested": None,
                    "seed_supported": False,
                    "seed_applied": False,
                    "error": None,
                },
                {
                    "run_id": "run-1",
                    "case_id": "case-embed",
                    "group": "embeddings",
                    "status": "success",
                    "provider_requested": "ollama",
                    "provider_effective": "ollama",
                    "model_requested": "embeddinggemma:300m",
                    "model_effective": "embeddinggemma:300m",
                    "candidate_id": "embed-baseline",
                    "candidate_role": "baseline",
                    "dataset_id": "dataset-1",
                    "question_set_id": "qs-1",
                    "document_count": 2,
                    "question_count": 2,
                    "embedding_context_window": 512,
                    "embedding_truncate": True,
                    "chunk_size": 1200,
                    "chunk_overlap": 80,
                    "top_k": 4,
                    "rerank_pool_size": 8,
                    "rerank_lexical_weight": 0.35,
                    "repetition": 1,
                    "runtime_bucket": "local",
                    "quantization_family": "unspecified_local",
                    "runtime_path": "hub_wrapped_runtime",
                    "runtime_path_label": "Hub-wrapped runtime",
                    "backend_equivalence_type": "wrapped_backend",
                    "backend_provider_resolved": "ollama",
                    "backend_model_ref_resolved": "embeddinggemma:300m",
                    "backend_equivalence_key": "ollama::embeddinggemma:300m",
                    "equivalent_direct_runtime_key": "ollama::embeddinggemma:300m",
                    "path_overhead_expected": True,
                    "path_comparison_note": "Wrapped via local hub.",
                    "indexing_seconds": 2.5,
                    "aggregate_metrics": {
                        "hit_at_1": 0.5,
                        "hit_at_k": 1.0,
                        "mrr": 0.75,
                        "average_retrieval_seconds": 0.2,
                        "median_retrieval_seconds": 0.2,
                        "max_retrieval_seconds": 0.3,
                    },
                    "per_question_results": [
                        {
                            "question": "Which document discusses OCR?",
                            "hit_at_1": True,
                            "hit_at_k": True,
                            "reciprocal_rank": 1.0,
                            "first_relevant_rank": 1,
                            "retrieval_seconds": 0.2,
                            "backend_used": "chroma",
                        }
                    ],
                    "error": None,
                },
            ]
        )

        self.assertEqual(len(normalized["generation"]), 1)
        self.assertEqual(len(normalized["embeddings"]), 1)
        self.assertEqual(len(normalized["embedding_questions"]), 1)
        self.assertEqual(normalized["embeddings"][0]["mrr"], 0.75)
        self.assertEqual(normalized["generation"][0]["runtime_path"], "direct_runtime")
        self.assertEqual(normalized["embeddings"][0]["backend_equivalence_key"], "ollama::embeddinggemma:300m")
        self.assertEqual(normalized["embedding_questions"][0]["runtime_path"], "hub_wrapped_runtime")

    def test_classify_runtime_path_marks_huggingface_server_over_ollama_as_wrapped(self) -> None:
        classified = classify_runtime_path(
            provider_requested="huggingface_server",
            provider_effective="huggingface_server",
            model_effective="qwen2.5:7b-ollama",
            runtime_artifact={
                "backend_provider": "ollama",
                "backend_model_ref": "qwen2.5:7b",
            },
        )

        self.assertEqual(classified["runtime_path"], "hub_wrapped_runtime")
        self.assertEqual(classified["backend_equivalence_key"], "ollama::qwen2.5:7b")
        self.assertEqual(classified["equivalent_direct_runtime_key"], "ollama::qwen2.5:7b")
        self.assertTrue(classified["path_overhead_expected"])

    def test_aggregate_case_results_includes_runtime_path_breakdown(self) -> None:
        aggregated = aggregate_case_results(
            [
                {
                    "group": "generation",
                    "status": "success",
                    "provider_requested": "ollama",
                    "model_requested": "qwen2.5:7b",
                    "runtime_path": "direct_runtime",
                    "runtime_path_label": "Direct runtime",
                    "backend_provider_resolved": "ollama",
                    "backend_model_ref_resolved": "qwen2.5:7b",
                    "backend_equivalence_key": "ollama::qwen2.5:7b",
                    "path_overhead_expected": False,
                    "latency_s": 1.0,
                    "format_adherence": 1.0,
                    "groundedness_score": 0.8,
                    "use_case_fit_score": 0.9,
                    "total_tokens": 100,
                },
                {
                    "group": "generation",
                    "status": "success",
                    "provider_requested": "huggingface_server",
                    "model_requested": "qwen2.5:7b-ollama",
                    "runtime_path": "hub_wrapped_runtime",
                    "runtime_path_label": "Hub-wrapped runtime",
                    "backend_provider_resolved": "ollama",
                    "backend_model_ref_resolved": "qwen2.5:7b",
                    "backend_equivalence_key": "ollama::qwen2.5:7b",
                    "equivalent_direct_runtime_key": "ollama::qwen2.5:7b",
                    "path_overhead_expected": True,
                    "latency_s": 1.4,
                    "format_adherence": 1.0,
                    "groundedness_score": 0.7,
                    "use_case_fit_score": 0.85,
                    "total_tokens": 100,
                },
            ]
        )

        self.assertEqual(len(aggregated["runtime_path_breakdown"]), 2)
        generation_ranking = aggregated["generation"]["candidate_ranking"]
        wrapped = next(item for item in generation_ranking if item["provider"] == "huggingface_server")
        self.assertEqual(wrapped["runtime_path"], "hub_wrapped_runtime")
        self.assertEqual(wrapped["equivalent_direct_runtime_key"], "ollama::qwen2.5:7b")

    def test_build_benchmark_environment_snapshot_captures_provider_inventory_and_fairness(self) -> None:
        registry = {
            "ollama": {
                "label": "Ollama (local)",
                "detail": "Base URL: http://localhost:11434/v1",
                "instance": _FakeOllamaProvider(),
                "supports_chat": True,
                "supports_embeddings": True,
                "default_model": "qwen2.5:7b",
                "default_context_window": 8192,
            }
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshot = build_benchmark_environment_snapshot(
                project_root=Path(tmp_dir),
                registry=registry,
                manifest={"benchmark_id": "phase8_5_round1", "manifest_version": "1.0"},
                selected_groups=["generation", "embeddings"],
                fairness_config={"temperature": 0.2},
                environment_overrides={"RAG_TOP_K": "4"},
                resolved_case_artifacts=[{"case_id": "case-1", "provider_effective": "ollama"}],
            )

        self.assertEqual(snapshot["fairness_config"]["temperature"], 0.2)
        self.assertEqual(snapshot["active_environment"]["RAG_TOP_K"], "4")
        self.assertIn("ollama", snapshot["provider_inventory"])
        self.assertIn("qwen2.5:7b", snapshot["provider_inventory"]["ollama"]["available_chat_models"])
        self.assertIn("embeddinggemma:300m", snapshot["provider_inventory"]["ollama"]["available_embedding_models"])
        self.assertEqual(snapshot["resolved_case_artifacts"][0]["case_id"], "case-1")

    def test_build_preflight_payload_uses_resume_success_inventory(self) -> None:
        manifest = load_benchmark_manifest(DEFAULT_PHASE8_5_MANIFEST_PATH)
        registry = {
            "ollama": {
                "label": "Ollama (local)",
                "detail": "Base URL: http://localhost:11434/v1",
                "instance": _FakeOllamaProvider(),
                "supports_chat": True,
                "supports_embeddings": True,
                "default_model": "qwen2.5:7b",
                "default_context_window": 8192,
            }
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            preview = build_preflight_payload(
                manifest,
                registry=registry,
                run_id="run-1",
                output_dir=output_dir,
                selected_groups=["generation", "embeddings"],
                smoke=True,
                provider_filter=None,
                model_filter=None,
                resume=False,
            )
            first_case_id = preview["groups"]["generation"]["sample_case_ids"][0]
            raw_dir = output_dir / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / "events.jsonl").write_text(
                json.dumps({"event_type": "case_result", "case_id": first_case_id, "status": "success"}) + "\n",
                encoding="utf-8",
            )

            resumed = build_preflight_payload(
                manifest,
                registry=registry,
                run_id="run-1",
                output_dir=output_dir,
                selected_groups=["generation", "embeddings"],
                smoke=True,
                provider_filter=None,
                model_filter=None,
                resume=True,
            )

        self.assertGreater(resumed["planned_case_count"], 0)
        self.assertEqual(resumed["resume_success_case_count"], 1)


if __name__ == "__main__":
    unittest.main()