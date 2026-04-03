import tempfile
import unittest
from pathlib import Path

from src.storage.phase8_eval_import import import_eval_history_reports
from src.storage.phase8_eval_store import append_eval_run, load_eval_runs, summarize_eval_runs


class Phase8EvalStoreTests(unittest.TestCase):
    def test_append_load_and_summarize_eval_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "phase8_eval.sqlite3"
            append_eval_run(
                db_path,
                {
                    "suite_name": "structured_smoke_eval",
                    "task_type": "summary",
                    "case_name": "fixture:summary",
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                    "status": "PASS",
                    "score": 5,
                    "max_score": 5,
                    "latency_s": 1.2,
                    "needs_review": False,
                    "metrics": {"parse_recovery_used": False},
                },
            )
            append_eval_run(
                db_path,
                {
                    "suite_name": "checklist_regression",
                    "task_type": "checklist",
                    "case_name": "fixture:who-checklist",
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                    "status": "WARN",
                    "score": 8,
                    "max_score": 10,
                    "latency_s": 2.4,
                    "needs_review": True,
                    "context_strategy": "document_scan",
                    "metrics": {"coverage": 0.8},
                    "reasons": ["coverage below target"],
                },
            )

            entries = load_eval_runs(db_path)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["suite_name"], "checklist_regression")
            self.assertTrue(entries[0]["needs_review"])
            self.assertEqual(entries[1]["metrics"]["parse_recovery_used"], False)

            filtered_by_suite = load_eval_runs(db_path, suite_name="structured_smoke_eval")
            self.assertEqual(len(filtered_by_suite), 1)
            self.assertEqual(filtered_by_suite[0]["task_type"], "summary")

            filtered_by_task = load_eval_runs(db_path, task_type="checklist")
            self.assertEqual(len(filtered_by_task), 1)
            self.assertEqual(filtered_by_task[0]["suite_name"], "checklist_regression")

            limited = load_eval_runs(db_path, limit=1)
            self.assertEqual(len(limited), 1)
            self.assertEqual(limited[0]["suite_name"], "checklist_regression")

            summary = summarize_eval_runs(entries)
            self.assertEqual(summary["total_runs"], 2)
            self.assertEqual(summary["status_counts"]["PASS"], 1)
            self.assertEqual(summary["status_counts"]["WARN"], 1)
            self.assertEqual(summary["suite_counts"]["structured_smoke_eval"], 1)
            self.assertEqual(summary["task_counts"]["checklist"], 1)
            self.assertEqual(summary["needs_review_rate"], 0.5)
            self.assertEqual(summary["avg_score_ratio"], 0.9)
            self.assertEqual(summary["suite_leaderboard"][0]["suite_name"], "structured_smoke_eval")

    def test_import_eval_history_reports_backfills_known_json_reports_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            reports_dir = root / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            db_path = root / "phase8_eval.sqlite3"

            (reports_dir / "phase5_structured_eval_20260328_231333.json").write_text(
                """
                {
                  "generated_at": "2026-03-28T23:13:33.192732",
                  "provider": "ollama",
                  "model": null,
                  "tasks": [
                    {
                      "task": "summary",
                      "suite_name": "structured_real_document_eval",
                      "status": "PASS",
                      "score": 5,
                      "max_score": 5,
                      "reasons": [],
                      "success": true,
                      "validation_error": null,
                      "parsing_error": null
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )

            (reports_dir / "phase8_agent_workflow_eval_20260330_100000.json").write_text(
                """
                {
                  "generated_at": "2026-03-30T10:00:00",
                  "routing_results": [
                    {
                      "suite_name": "document_agent_routing_eval",
                      "task_type": "document_agent_routing",
                      "case_name": "routing-case-1",
                      "status": "PASS",
                      "score": 4,
                      "max_score": 4,
                      "latency_s": 0.001,
                      "metrics": {"score_ratio": 1.0},
                      "reasons": [],
                      "metadata": {"actual_intent": "document_question"}
                    }
                  ],
                  "workflow_results": [
                    {
                      "suite_name": "langgraph_workflow_eval",
                      "task_type": "langgraph_guardrails",
                      "case_name": "workflow-case-1",
                      "status": "WARN",
                      "score": 3,
                      "max_score": 4,
                      "latency_s": 0.002,
                      "metrics": {"score_ratio": 0.75},
                      "reasons": ["transition_correct"],
                      "metadata": {"actual_transition": "retry_with_retrieval"}
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )

            (reports_dir / "checklist_regression_20260324_222845.json").write_text(
                """
                {
                  "generated_at": "2026-03-24T22:28:45.131868",
                  "provider": "ollama",
                  "model": null,
                  "context_strategy": "document_scan",
                  "resolved_document": {
                    "document_id": "doc-1",
                    "name": "9789241598590_eng.pdf"
                  },
                  "evaluation": {
                    "status": "FAIL",
                    "expected_items": 22,
                    "matched_items": 22,
                    "coverage": 1.0,
                    "duplicate_ids": [],
                    "artifact_items": [],
                    "collapsed_items": [1],
                    "style_issue_items": [],
                    "reasons": ["collapsed items detected: 1"]
                  }
                }
                """,
                encoding="utf-8",
            )

            (reports_dir / "evidence_cv_eval_metrics.json").write_text(
                """
                {
                  "gold_set": "phase5_eval/reports/evidence_cv_mini_gold_set.json",
                  "per_file": [
                    {
                      "file": "data/synthetic/resumes_ui_test/example.pdf",
                      "scores": {
                        "legacy": {
                          "emails": {"precision": 1.0, "recall": 1.0},
                          "phones": {"precision": 1.0, "recall": 1.0},
                          "name": {"precision": 1.0, "recall": 0.0},
                          "location": {"precision": 1.0, "recall": 0.0}
                        },
                        "evidence_with_vl": {
                          "emails": {"precision": 0.5, "recall": 1.0},
                          "phones": {"precision": 1.0, "recall": 1.0},
                          "name": {"precision": 1.0, "recall": 1.0},
                          "location": {"precision": 0.0, "recall": 0.0}
                        }
                      }
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )

            counts = import_eval_history_reports(reports_dir, db_path)
            self.assertEqual(counts["structured_real_document_eval"], 1)
            self.assertEqual(counts["checklist_regression"], 1)
            self.assertEqual(counts["evidence_cv_gold_eval"], 2)
            self.assertEqual(counts["document_agent_routing_eval"], 1)
            self.assertEqual(counts["langgraph_workflow_eval"], 1)

            entries = load_eval_runs(db_path)
            self.assertEqual(len(entries), 6)
            summary = summarize_eval_runs(entries)
            self.assertEqual(summary["total_runs"], 6)
            self.assertIn("structured_real_document_eval", summary["suite_counts"])
            self.assertIn("evidence_cv_gold_eval", summary["suite_counts"])
            self.assertIn("document_agent_routing_eval", summary["suite_counts"])

            counts_second_run = import_eval_history_reports(reports_dir, db_path)
            self.assertEqual(counts_second_run["structured_real_document_eval"], 0)
            self.assertEqual(counts_second_run["checklist_regression"], 0)
            self.assertEqual(counts_second_run["evidence_cv_gold_eval"], 0)
            self.assertEqual(counts_second_run["document_agent_routing_eval"], 0)
            self.assertEqual(counts_second_run["langgraph_workflow_eval"], 0)
            self.assertEqual(len(load_eval_runs(db_path)), 6)