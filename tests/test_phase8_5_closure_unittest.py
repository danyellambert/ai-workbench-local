import unittest

from src.services.phase8_5_closure import (
    build_adaptation_scaffold_rows,
    build_phase8_5_closure_summary,
    render_phase8_5_closure_markdown,
)


class Phase85ClosureTests(unittest.TestCase):
    def _audit_summary(self) -> dict[str, object]:
        return {
            "benchmark_run_dir": "benchmark_runs/phase8_5_matrix/run-1",
            "benchmark_run_id": "run-1",
            "support_status": {
                "round0": {"implemented": True, "evidence_bundle_complete": True},
                "round1": {"implemented": True, "evidence_bundle_complete": True},
                "round2": {"implemented": True, "evidence_bundle_complete": False},
                "round3": {"implemented": True, "evidence_bundle_complete": True},
            },
        }

    def _decision_summary(self) -> dict[str, object]:
        return {
            "runtime_model_decisions": {
                "best_local_runtime_by_use_case": [
                    {
                        "use_case_id": "ops_update_summary",
                        "best_local_candidate": {"candidate": "ollama::qwen2.5:7b"},
                    }
                ]
            },
            "embedding_decisions": {
                "best_embedding_strategy": {"candidate": "ollama::embeddinggemma:300m"}
            },
            "reranker_decisions": {
                "best_reranker_tradeoff": {"candidate_id": "hybrid_rerank_current_default"}
            },
            "ocr_vlm_observations": {
                "best_ocr_tradeoff": {"variant": "evidence_no_vl"},
                "best_vlm_tradeoff": {"variant": "evidence_with_vl"},
            },
            "adaptation_decision": {
                "adaptation_candidates": [
                    {
                        "task_type": "extraction",
                        "failure_pattern": ["quality_score_below_target"],
                        "current_baseline_quality": {"pass_rate": 0.4, "fail_rate": 0.6, "avg_score_ratio": 0.58},
                        "adaptation_priority": "high",
                        "non_training_alternatives_remaining": [],
                        "why_prompt_rag_retrieval_changes_were_not_enough": "No clearer non-training alternative remains.",
                        "minimal_lora_peft_experiment": {
                            "experiment_type": "future_lora_peft_scaffold_only",
                            "task_scope": "extraction",
                            "primary_success_metric": "schema_adherence",
                            "baseline_quality": {"pass_rate": 0.4, "fail_rate": 0.6, "avg_score_ratio": 0.58},
                            "target_quality": {"target_avg_score_ratio": 0.8, "target_fail_rate_max": 0.3},
                            "scope_constraints": ["single narrow task only"],
                        },
                        "recommended_action": "consider_task_specific_model_adaptation_after_more_eval_cases",
                    }
                ]
            },
        }

    def _fully_complete_audit_summary(self) -> dict[str, object]:
        return {
            "benchmark_run_dir": "benchmark_runs/phase8_5_matrix/run-complete",
            "benchmark_run_id": "run-complete",
            "support_status": {
                "round0": {"implemented": True, "evidence_bundle_complete": True},
                "round1": {"implemented": True, "evidence_bundle_complete": True},
                "round2": {"implemented": True, "evidence_bundle_complete": True},
                "round3": {"implemented": True, "evidence_bundle_complete": True},
            },
        }

    def test_build_adaptation_scaffold_rows_validates_candidate_rows(self) -> None:
        rows = build_adaptation_scaffold_rows(self._decision_summary())
        self.assertEqual(rows[0]["task_type"], "extraction")
        self.assertEqual(rows[0]["minimal_lora_peft_experiment"]["experiment_type"], "future_lora_peft_scaffold_only")

    def test_build_phase8_5_closure_summary_marks_partial_round2_support(self) -> None:
        summary = build_phase8_5_closure_summary(
            audit_summary=self._audit_summary(),
            decision_summary=self._decision_summary(),
        )
        markdown = render_phase8_5_closure_markdown(summary)

        self.assertIn("round0_audit_preflight_layer", summary["fully_supported"])
        self.assertIn("round2_reranker_ocr_vlm_evidence_bundle_in_latest_run", summary["partially_supported"])
        self.assertIn("## Adaptation scaffolds", markdown)

    def test_build_phase8_5_closure_summary_marks_fully_closed_when_all_rounds_have_complete_evidence(self) -> None:
        summary = build_phase8_5_closure_summary(
            audit_summary=self._fully_complete_audit_summary(),
            decision_summary=self._decision_summary(),
        )

        self.assertEqual(summary["phase_status"], "phase8_5_fully_closed_local_execution_complete")
        self.assertIn("round2_reranker_ocr_vlm_workflow", summary["fully_supported"])
        self.assertEqual(summary["partially_supported"], [])


if __name__ == "__main__":
    unittest.main()