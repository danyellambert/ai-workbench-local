import unittest

from src.storage.phase8_eval_diagnosis import build_eval_diagnosis


class Phase8EvalDiagnosisTests(unittest.TestCase):
    def test_build_eval_diagnosis_flags_healthy_and_adaptation_candidate_tasks(self) -> None:
        entries = [
            {
                "id": 1,
                "created_at": "2026-03-29T07:00:00",
                "task_type": "summary",
                "status": "PASS",
                "score": 5,
                "max_score": 5,
                "reasons": [],
            },
            {
                "id": 2,
                "created_at": "2026-03-29T07:01:00",
                "task_type": "summary",
                "status": "PASS",
                "score": 4,
                "max_score": 5,
                "reasons": [],
            },
            {
                "id": 3,
                "created_at": "2026-03-29T07:02:00",
                "task_type": "summary",
                "status": "PASS",
                "score": 5,
                "max_score": 5,
                "reasons": [],
            },
            {
                "id": 4,
                "created_at": "2026-03-29T07:03:00",
                "task_type": "extraction",
                "status": "FAIL",
                "score": 1,
                "max_score": 5,
                "reasons": ["quality_score_below_target"],
            },
            {
                "id": 5,
                "created_at": "2026-03-29T07:04:00",
                "task_type": "extraction",
                "status": "FAIL",
                "score": 2,
                "max_score": 5,
                "reasons": ["quality_score_below_target"],
            },
            {
                "id": 6,
                "created_at": "2026-03-29T07:05:00",
                "task_type": "extraction",
                "status": "FAIL",
                "score": 1,
                "max_score": 5,
                "reasons": ["quality_score_below_target"],
            },
            {
                "id": 7,
                "created_at": "2026-03-29T07:06:00",
                "task_type": "extraction",
                "status": "FAIL",
                "score": 2,
                "max_score": 5,
                "reasons": ["quality_score_below_target"],
            },
            {
                "id": 8,
                "created_at": "2026-03-29T07:07:00",
                "task_type": "extraction",
                "status": "PASS",
                "score": 4,
                "max_score": 5,
                "reasons": [],
            },
        ]

        diagnosis = build_eval_diagnosis(entries)
        self.assertEqual(diagnosis["total_runs"], 8)
        self.assertEqual(diagnosis["top_failure_reasons"][0]["reason"], "quality_score_below_target")

        summary_row = next(item for item in diagnosis["task_diagnosis"] if item["task_type"] == "summary")
        extraction_row = next(item for item in diagnosis["task_diagnosis"] if item["task_type"] == "extraction")

        self.assertEqual(summary_row["health_label"], "healthy")
        self.assertEqual(summary_row["recommended_action"], "prompt_rag_stack_currently_sufficient")
        self.assertEqual(extraction_row["health_label"], "needs_iteration")
        self.assertEqual(extraction_row["adaptation_priority"], "high")
        self.assertEqual(extraction_row["recommended_action"], "consider_task_specific_model_adaptation_after_more_eval_cases")
        self.assertTrue(any(item["task_type"] == "extraction" for item in diagnosis["adaptation_candidates"]))
        self.assertEqual(
            diagnosis["decision_summary"]["global_recommendation"],
            "consider_targeted_adaptation_only_for_specific_tasks",
        )
        self.assertTrue(
            any(item["task_type"] == "summary" for item in diagnosis["decision_summary"]["prompt_rag_sufficient_tasks"])
        )
        self.assertTrue(
            any(item["task_type"] == "extraction" for item in diagnosis["decision_summary"]["adaptation_candidate_tasks"])
        )

    def test_build_eval_diagnosis_special_cases_checklist_reasoning(self) -> None:
        entries = [
            {
                "id": 10,
                "created_at": "2026-03-29T08:00:00",
                "task_type": "checklist",
                "status": "FAIL",
                "score": 18,
                "max_score": 22,
                "reasons": ["collapsed items detected: 2"],
            },
            {
                "id": 11,
                "created_at": "2026-03-29T08:01:00",
                "task_type": "checklist",
                "status": "FAIL",
                "score": 19,
                "max_score": 22,
                "reasons": ["collapsed items detected: 1"],
            },
            {
                "id": 12,
                "created_at": "2026-03-29T08:02:00",
                "task_type": "checklist",
                "status": "PASS",
                "score": 22,
                "max_score": 22,
                "reasons": [],
            },
        ]

        diagnosis = build_eval_diagnosis(entries)
        checklist_row = next(item for item in diagnosis["task_diagnosis"] if item["task_type"] == "checklist")
        self.assertEqual(checklist_row["recommended_action"], "improve_checklist_decomposition_and_source_alignment")
        self.assertEqual(checklist_row["top_reasons"][0]["reason"], "collapsed items detected: 2")
        self.assertTrue(
            any(item["task_type"] == "checklist" for item in diagnosis["decision_summary"]["iteration_before_adaptation_tasks"])
        )