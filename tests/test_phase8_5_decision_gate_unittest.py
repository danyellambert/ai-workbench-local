import unittest

from src.services.phase8_5_decision_gate import (
    build_phase8_5_decision_summary,
    render_phase8_5_decision_markdown,
)


class Phase85DecisionGateTests(unittest.TestCase):
    def _manifest(self) -> dict[str, object]:
        return {
            "benchmark_id": "phase8_5_matrix",
            "manifest_version": "1.0",
            "groups": {
                "generation": {
                    "provider_model_pairs": [
                        {"provider": "ollama", "model": "qwen2.5:7b", "role": "baseline_local"},
                        {"provider": "ollama", "model": "qwen2.5-coder:7b", "role": "challenger_local"},
                    ]
                }
            },
        }

    def _benchmark_events(self) -> list[dict[str, object]]:
        return [
            {
                "group": "generation",
                "status": "success",
                "run_id": "run-1",
                "use_case_id": "ops_update_summary",
                "use_case_label": "Ops update summary",
                "benchmark_use_case": "executive_summary",
                "provider_requested": "ollama",
                "model_requested": "qwen2.5:7b",
                "runtime_bucket": "local",
                "runtime_path": "direct_runtime",
                "use_case_fit_score": 0.82,
                "format_adherence": 0.92,
                "groundedness_score": 0.60,
                "latency_s": 1.4,
            },
            {
                "group": "generation",
                "status": "success",
                "run_id": "run-1",
                "use_case_id": "ops_update_summary",
                "use_case_label": "Ops update summary",
                "benchmark_use_case": "executive_summary",
                "provider_requested": "ollama",
                "model_requested": "qwen2.5-coder:7b",
                "runtime_bucket": "local",
                "runtime_path": "direct_runtime",
                "use_case_fit_score": 0.90,
                "format_adherence": 0.97,
                "groundedness_score": 0.68,
                "latency_s": 1.2,
            },
            {
                "group": "generation",
                "status": "success",
                "run_id": "run-1",
                "use_case_id": "cv_structured_extraction",
                "use_case_label": "CV structured extraction",
                "benchmark_use_case": "structured_extraction",
                "provider_requested": "ollama",
                "model_requested": "qwen2.5:7b",
                "runtime_bucket": "local",
                "runtime_path": "direct_runtime",
                "use_case_fit_score": 0.61,
                "format_adherence": 0.70,
                "groundedness_score": 0.52,
                "latency_s": 1.5,
            },
        ]

    def _benchmark_summary(self, *, embedding_change: bool = True, reranker_change: bool = True) -> dict[str, object]:
        embedding_ranking = [
            {
                "candidate": "ollama::embeddinggemma:300m",
                "provider": "ollama",
                "model": "embeddinggemma:300m",
                "candidate_role": "baseline",
                "avg_mrr": 0.55,
                "avg_hit_at_1": 0.50,
                "avg_retrieval_seconds": 0.40,
            },
            {
                "candidate": "ollama::bge-m3:latest",
                "provider": "ollama",
                "model": "bge-m3:latest",
                "candidate_role": "challenger",
                "avg_mrr": 0.66 if embedding_change else 0.56,
                "avg_hit_at_1": 0.65 if embedding_change else 0.52,
                "avg_retrieval_seconds": 0.44,
            },
        ]
        reranker_ranking = [
            {
                "candidate_id": "vector_only_local_baseline",
                "candidate_role": "baseline",
                "provider": "ollama",
                "model": "embeddinggemma:300m",
                "avg_mrr": 0.58,
                "avg_hit_at_1": 0.50,
                "avg_groundedness_proxy": 0.50,
                "avg_retrieval_seconds": 0.20,
            },
            {
                "candidate_id": "hybrid_rerank_current_default",
                "candidate_role": "current_default",
                "provider": "ollama",
                "model": "embeddinggemma:300m",
                "avg_mrr": 0.72 if reranker_change else 0.59,
                "avg_hit_at_1": 0.75,
                "avg_groundedness_proxy": 0.63 if reranker_change else 0.51,
                "avg_retrieval_seconds": 0.25,
            },
        ]
        return {
            "total_cases": 5,
            "successful_cases": 5,
            "failed_cases": 0,
            "embeddings": {
                "candidate_ranking": embedding_ranking,
                "top_candidate": embedding_ranking[1],
            },
            "rerankers": {
                "candidate_ranking": reranker_ranking,
                "best_tradeoff": reranker_ranking[1],
            },
            "ocr_vlm": {
                "best_ocr_tradeoff": {"variant": "evidence_no_vl"},
                "best_vlm_tradeoff": {"variant": "evidence_with_vl"},
                "variant_ranking": [{"variant": "evidence_with_vl", "avg_f1": 0.7}],
                "support_level": "partially_supported",
            },
        }

    def _eval_summary(self) -> dict[str, object]:
        return {
            "total_runs": 6,
            "pass_rate": 0.5,
            "fail_rate": 0.33,
            "avg_score_ratio": 0.69,
            "needs_review_rate": 0.16,
        }

    def _eval_diagnosis(self) -> dict[str, object]:
        return {
            "healthy_tasks": [
                {
                    "task_type": "summary",
                    "pass_rate": 1.0,
                    "avg_score_ratio": 0.92,
                    "health_label": "healthy",
                }
            ],
            "persistent_failure_tasks": [
                {
                    "task_type": "extraction",
                    "fail_rate": 0.8,
                    "recent_fail_rate": 0.8,
                    "recommended_action": "consider_task_specific_model_adaptation_after_more_eval_cases",
                }
            ],
            "adaptation_candidates": [
                {
                    "task_type": "extraction",
                    "pass_rate": 0.2,
                    "fail_rate": 0.8,
                    "avg_score_ratio": 0.44,
                    "adaptation_priority": "high",
                    "recommended_action": "consider_task_specific_model_adaptation_after_more_eval_cases",
                    "top_reasons": [
                        {"reason": "quality_score_below_target", "count": 4},
                        {"reason": "schema_coverage_incomplete", "count": 3},
                    ],
                }
            ],
            "task_diagnosis": [
                {
                    "task_type": "summary",
                    "health_label": "healthy",
                    "recommended_action": "prompt_rag_stack_currently_sufficient",
                },
                {
                    "task_type": "extraction",
                    "health_label": "needs_iteration",
                    "recommended_action": "consider_task_specific_model_adaptation_after_more_eval_cases",
                },
            ],
            "decision_summary": {
                "global_recommendation": "consider_targeted_adaptation_only_for_specific_tasks"
            },
        }

    def test_decision_summary_prefers_non_training_changes_before_adaptation(self) -> None:
        summary = build_phase8_5_decision_summary(
            benchmark_summary=self._benchmark_summary(embedding_change=True, reranker_change=True),
            benchmark_events=self._benchmark_events(),
            manifest=self._manifest(),
            preflight={"run_id": "run-1", "selected_groups": ["generation", "embeddings", "rerankers"]},
            eval_summary=self._eval_summary(),
            eval_diagnosis=self._eval_diagnosis(),
            benchmark_run_dir="benchmark_runs/phase8_5_matrix/run-1",
        )

        runtime_rows = summary["runtime_model_decisions"]["best_local_runtime_by_use_case"]
        summary_row = next(item for item in runtime_rows if item["use_case_id"] == "ops_update_summary")
        self.assertTrue(summary_row["change_recommended"])
        self.assertTrue(summary["embedding_decisions"]["change_recommended"])
        self.assertTrue(summary["reranker_decisions"]["change_recommended"])
        self.assertFalse(summary["adaptation_decision"]["adaptation_justified"])
        self.assertEqual(
            summary["adaptation_decision"]["global_recommendation"],
            "defer_adaptation_until_runtime_and_retrieval_changes_are_exhausted",
        )

    def test_decision_summary_marks_targeted_adaptation_when_no_clear_alternative_wins_remain(self) -> None:
        summary = build_phase8_5_decision_summary(
            benchmark_summary=self._benchmark_summary(embedding_change=False, reranker_change=False),
            benchmark_events=self._benchmark_events()[2:],
            manifest=self._manifest(),
            preflight={"run_id": "run-2", "selected_groups": ["generation"]},
            eval_summary=self._eval_summary(),
            eval_diagnosis=self._eval_diagnosis(),
            benchmark_run_dir="benchmark_runs/phase8_5_matrix/run-2",
        )

        self.assertTrue(summary["adaptation_decision"]["adaptation_justified"])
        candidate = summary["adaptation_decision"]["best_candidate"]
        self.assertEqual(candidate["task_type"], "extraction")
        self.assertEqual(candidate["minimal_lora_peft_experiment"]["experiment_type"], "future_lora_peft_scaffold_only")

    def test_render_phase8_5_decision_markdown_contains_required_sections(self) -> None:
        summary = build_phase8_5_decision_summary(
            benchmark_summary=self._benchmark_summary(embedding_change=False, reranker_change=False),
            benchmark_events=self._benchmark_events()[2:],
            manifest=self._manifest(),
            preflight={"run_id": "run-3", "selected_groups": ["generation"]},
            eval_summary=self._eval_summary(),
            eval_diagnosis=self._eval_diagnosis(),
            benchmark_run_dir="benchmark_runs/phase8_5_matrix/run-3",
        )
        markdown = render_phase8_5_decision_markdown(summary)

        self.assertIn("## Decision matrix by use case", markdown)
        self.assertIn("## Adaptation not needed yet", markdown)
        self.assertIn("## Adaptation candidates", markdown)

    def test_decision_summary_uses_effective_group_coverage_not_just_latest_preflight_groups(self) -> None:
        summary = build_phase8_5_decision_summary(
            benchmark_summary=self._benchmark_summary(embedding_change=True, reranker_change=True),
            benchmark_events=self._benchmark_events() + [
                {"group": "embeddings", "status": "success", "run_id": "run-4"},
                {"group": "rerankers", "status": "success", "run_id": "run-4"},
                {"group": "ocr_vlm", "status": "success", "run_id": "run-4"},
            ],
            manifest=self._manifest(),
            preflight={"run_id": "run-4", "selected_groups": ["rerankers"]},
            eval_summary=self._eval_summary(),
            eval_diagnosis=self._eval_diagnosis(),
            benchmark_run_dir="benchmark_runs/phase8_5_matrix/run-4",
        )

        self.assertEqual(
            summary["benchmark_overview"]["selected_groups"],
            ["embeddings", "generation", "ocr_vlm", "rerankers"],
        )
        self.assertEqual(summary["benchmark_overview"]["preflight_selected_groups"], ["rerankers"])


if __name__ == "__main__":
    unittest.main()