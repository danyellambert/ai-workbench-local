import unittest
import tempfile
from pathlib import Path

from src.services.phase8_5_benchmark import (
    DEFAULT_PHASE8_5_MANIFEST_PATH,
    build_preflight_payload,
    load_benchmark_manifest,
)
from src.services.phase8_5_benchmark_round2 import (
    aggregate_ocr_vlm_events,
    aggregate_reranker_events,
    build_ocr_vlm_cases,
    build_reranker_cases,
    normalize_round2_case_results,
    validate_round2_manifest_groups,
)


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


class Phase85BenchmarkRound2Tests(unittest.TestCase):
    def test_manifest_includes_round2_groups(self) -> None:
        manifest = load_benchmark_manifest(DEFAULT_PHASE8_5_MANIFEST_PATH)

        self.assertIn("rerankers", manifest["groups"])
        self.assertIn("ocr_vlm", manifest["groups"])
        validate_round2_manifest_groups(manifest)

    def test_build_reranker_cases_smoke_uses_existing_local_dataset(self) -> None:
        manifest = load_benchmark_manifest(DEFAULT_PHASE8_5_MANIFEST_PATH)

        cases = build_reranker_cases(manifest, smoke=True)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["group"], "rerankers")
        self.assertEqual(cases[0]["embedding_provider"], "ollama")
        self.assertEqual(cases[0]["embedding_model"], "embeddinggemma:300m")

    def test_build_ocr_vlm_cases_smoke_uses_existing_gold_backed_cases(self) -> None:
        manifest = load_benchmark_manifest(DEFAULT_PHASE8_5_MANIFEST_PATH)

        cases = build_ocr_vlm_cases(manifest, smoke=True)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["group"], "ocr_vlm")
        self.assertTrue(Path(cases[0]["pdf_path"]).exists())
        self.assertTrue(Path(cases[0]["gold_path"]).exists())

    def test_preflight_counts_round2_groups_without_execution(self) -> None:
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
            preview = build_preflight_payload(
                manifest,
                registry=registry,
                run_id="run-round2",
                output_dir=Path(tmp_dir),
                selected_groups=["rerankers", "ocr_vlm"],
                smoke=True,
                provider_filter=None,
                model_filter=None,
                resume=False,
            )

        self.assertEqual(preview["groups"]["rerankers"]["planned_cases"], 1)
        self.assertEqual(preview["groups"]["ocr_vlm"]["planned_cases"], 1)
        self.assertEqual(preview["planned_case_count"], 2)

    def test_normalize_round2_case_results_splits_reranker_and_ocr_rows(self) -> None:
        normalized = normalize_round2_case_results(
            [
                {
                    "run_id": "run-1",
                    "case_id": "case-rerank",
                    "group": "rerankers",
                    "status": "success",
                    "candidate_id": "hybrid_rerank_current_default",
                    "candidate_label": "Hybrid rerank",
                    "candidate_role": "current_default",
                    "dataset_id": "dataset-1",
                    "question_set_id": "qs-1",
                    "provider_requested": "ollama",
                    "provider_effective": "ollama",
                    "model_requested": "embeddinggemma:300m",
                    "model_effective": "embeddinggemma:300m",
                    "retrieval_strategy": "manual_hybrid",
                    "rerank_pool_size": 8,
                    "rerank_lexical_weight": 0.35,
                    "indexing_seconds": 1.2,
                    "aggregate_metrics": {
                        "question_count": 2,
                        "hit_at_1": 0.5,
                        "hit_at_k": 1.0,
                        "mrr": 0.75,
                        "average_retrieval_seconds": 0.2,
                        "median_retrieval_seconds": 0.2,
                        "avg_groundedness_proxy": 0.6,
                    },
                    "per_question_results": [
                        {
                            "question": "Which document discusses OCR?",
                            "hit_at_1": True,
                            "hit_at_k": True,
                            "reciprocal_rank": 1.0,
                            "retrieval_seconds": 0.2,
                            "backend_used": "chroma",
                            "groundedness_proxy": 1.0,
                        }
                    ],
                    "support_status": "fully_supported",
                    "error": None,
                },
                {
                    "run_id": "run-1",
                    "case_id": "case-ocr",
                    "group": "ocr_vlm",
                    "status": "success",
                    "case_name": "cv_lucas_real_document",
                    "document_type": "cv_resume",
                    "support_status": "partially_supported",
                    "variant_results": [
                        {
                            "variant": "legacy_pdf",
                            "latency_s": 0.8,
                            "scores": {
                                "avg_f1": 0.4,
                                "emails": {"f1": 0.5},
                                "phones": {"f1": 0.0},
                                "name": {"f1": 0.5},
                                "location": {"f1": 0.6},
                            },
                            "helped_vs_legacy": False,
                            "name_status": "not_found",
                            "location_status": "not_found",
                        },
                        {
                            "variant": "evidence_with_vl",
                            "latency_s": 1.4,
                            "scores": {
                                "avg_f1": 0.7,
                                "emails": {"f1": 0.8},
                                "phones": {"f1": 0.0},
                                "name": {"f1": 1.0},
                                "location": {"f1": 1.0},
                            },
                            "helped_vs_legacy": True,
                            "name_status": "confirmed",
                            "location_status": "confirmed",
                        },
                    ],
                    "error": None,
                },
            ]
        )

        self.assertEqual(len(normalized["rerankers"]), 1)
        self.assertEqual(len(normalized["reranker_questions"]), 1)
        self.assertEqual(len(normalized["ocr_vlm"]), 2)
        self.assertEqual(normalized["ocr_vlm"][1]["variant"], "evidence_with_vl")

    def test_round2_aggregation_helpers_produce_rankings(self) -> None:
        reranker_summary = aggregate_reranker_events(
            [
                {
                    "status": "success",
                    "candidate_id": "vector_only_local_baseline",
                    "candidate_label": "Vector only",
                    "candidate_role": "baseline",
                    "provider_requested": "ollama",
                    "model_requested": "embeddinggemma:300m",
                    "support_status": "fully_supported",
                    "hit_at_1": 0.5,
                    "hit_at_k": 1.0,
                    "mrr": 0.75,
                    "average_retrieval_seconds": 0.12,
                    "avg_groundedness_proxy": 0.5,
                },
                {
                    "status": "success",
                    "candidate_id": "hybrid_rerank_current_default",
                    "candidate_label": "Hybrid rerank",
                    "candidate_role": "current_default",
                    "provider_requested": "ollama",
                    "model_requested": "embeddinggemma:300m",
                    "support_status": "fully_supported",
                    "hit_at_1": 1.0,
                    "hit_at_k": 1.0,
                    "mrr": 1.0,
                    "average_retrieval_seconds": 0.2,
                    "avg_groundedness_proxy": 0.9,
                },
            ]
        )
        ocr_summary = aggregate_ocr_vlm_events(
            [
                {
                    "status": "success",
                    "variant_results": [
                        {"variant": "legacy_pdf", "latency_s": 0.7, "scores": {"avg_f1": 0.4}, "helped_vs_legacy": False},
                        {"variant": "evidence_no_vl", "latency_s": 1.0, "scores": {"avg_f1": 0.6}, "helped_vs_legacy": True},
                        {"variant": "evidence_with_vl", "latency_s": 1.5, "scores": {"avg_f1": 0.7}, "helped_vs_legacy": True},
                    ],
                }
            ]
        )

        self.assertEqual(reranker_summary["best_tradeoff"]["candidate_id"], "hybrid_rerank_current_default")
        self.assertEqual(ocr_summary["best_ocr_tradeoff"]["variant"], "evidence_no_vl")
        self.assertEqual(ocr_summary["best_vlm_tradeoff"]["variant"], "evidence_with_vl")


if __name__ == "__main__":
    unittest.main()
