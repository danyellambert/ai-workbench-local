import json
import tempfile
import unittest
from pathlib import Path

from src.services.phase8_5_audit import build_phase8_5_audit, render_phase8_5_audit_markdown
from src.storage.phase8_eval_store import append_eval_run


class Phase85AuditTests(unittest.TestCase):
    def test_build_phase8_5_audit_reports_missing_round2_evidence_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest_dir = root / "phase8_eval" / "configs"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            (manifest_dir / "phase8_5_benchmark_matrix.json").write_text(
                json.dumps(
                    {
                        "groups": {
                            "generation": {},
                            "embeddings": {},
                            "rerankers": {},
                            "ocr_vlm": {},
                        }
                    }
                ),
                encoding="utf-8",
            )
            run_dir = root / "benchmark_runs" / "phase8_5_matrix" / "run-1"
            (run_dir / "aggregated").mkdir(parents=True, exist_ok=True)
            (run_dir / "aggregated" / "summary.json").write_text(
                json.dumps({"total_cases": 3, "successful_cases": 3, "failed_cases": 0}),
                encoding="utf-8",
            )
            (run_dir / "aggregated" / "latest_case_results.json").write_text(
                json.dumps(
                    [
                        {"group": "generation", "status": "success", "run_id": "run-1", "use_case_id": "summary"},
                        {"group": "embeddings", "status": "success", "run_id": "run-1", "candidate_id": "baseline"},
                    ]
                ),
                encoding="utf-8",
            )
            (run_dir / "manifest.resolved.json").write_text(
                json.dumps(
                    {
                        "groups": {
                            "generation": {},
                            "embeddings": {},
                            "rerankers": {},
                            "ocr_vlm": {},
                        }
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "preflight.json").write_text(
                json.dumps({"run_id": "run-1", "selected_groups": ["generation", "embeddings"]}),
                encoding="utf-8",
            )
            (run_dir / "environment_snapshot.json").write_text(
                json.dumps({"provider_inventory": {"ollama": {"available_chat_models": ["qwen2.5:7b"]}}}),
                encoding="utf-8",
            )
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            (scripts_dir / "report_phase8_5_decision_gate.py").write_text("# stub\n", encoding="utf-8")

            eval_db = root / ".phase8_eval_runs.sqlite3"
            append_eval_run(
                eval_db,
                {
                    "suite_name": "structured_smoke_eval",
                    "task_type": "summary",
                    "case_name": "fixture:summary",
                    "status": "PASS",
                    "score": 5,
                    "max_score": 5,
                },
            )

            audit = build_phase8_5_audit(project_root=root, benchmark_run_dir=run_dir, eval_db_path=eval_db)
            markdown = render_phase8_5_audit_markdown(audit)

        self.assertEqual(audit["benchmark_run_id"], "run-1")
        self.assertIn("rerankers", audit["manifest_groups"])
        self.assertIn("ocr_vlm", audit["manifest_groups"])
        self.assertEqual(sorted(audit["latest_run_manifest_groups"]), ["embeddings", "generation", "ocr_vlm", "rerankers"])
        self.assertTrue(audit["support_status"]["round1"]["implemented"])
        self.assertIn("produce one final evidence bundle containing rerankers + ocr_vlm together", audit["missing_pieces"]["round2"])
        self.assertIn("## Missing pieces by round", markdown)

    def test_build_phase8_5_audit_accepts_effective_group_coverage_across_resumed_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            manifest_dir = root / "phase8_eval" / "configs"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            (manifest_dir / "phase8_5_benchmark_matrix.json").write_text(
                json.dumps(
                    {
                        "groups": {
                            "generation": {},
                            "embeddings": {},
                            "rerankers": {},
                            "ocr_vlm": {},
                        }
                    }
                ),
                encoding="utf-8",
            )
            run_dir = root / "benchmark_runs" / "phase8_5_round1" / "run-combined"
            (run_dir / "aggregated").mkdir(parents=True, exist_ok=True)
            (run_dir / "aggregated" / "summary.json").write_text(
                json.dumps({"total_cases": 10, "successful_cases": 9, "failed_cases": 1}),
                encoding="utf-8",
            )
            (run_dir / "aggregated" / "latest_case_results.json").write_text(
                json.dumps(
                    [
                        {"group": "generation", "status": "success", "run_id": "run-a"},
                        {"group": "embeddings", "status": "success", "run_id": "run-b"},
                        {"group": "rerankers", "status": "success", "run_id": "run-c"},
                        {"group": "ocr_vlm", "status": "success", "run_id": "run-a"},
                    ]
                ),
                encoding="utf-8",
            )
            (run_dir / "manifest.resolved.json").write_text(
                json.dumps({"groups": {"generation": {}, "embeddings": {}, "rerankers": {}, "ocr_vlm": {}}}),
                encoding="utf-8",
            )
            (run_dir / "preflight.json").write_text(
                json.dumps({"run_id": "run-c", "selected_groups": ["rerankers"]}),
                encoding="utf-8",
            )
            (run_dir / "environment_snapshot.json").write_text(
                json.dumps({"provider_inventory": {"ollama": {"available_chat_models": ["qwen2.5:7b"]}}}),
                encoding="utf-8",
            )
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            (scripts_dir / "report_phase8_5_decision_gate.py").write_text("# stub\n", encoding="utf-8")

            eval_db = root / ".phase8_eval_runs.sqlite3"
            append_eval_run(
                eval_db,
                {
                    "suite_name": "structured_smoke_eval",
                    "task_type": "summary",
                    "case_name": "fixture:summary",
                    "status": "PASS",
                    "score": 5,
                    "max_score": 5,
                },
            )

            audit = build_phase8_5_audit(project_root=root, benchmark_run_dir=run_dir, eval_db_path=eval_db)

        self.assertEqual(sorted(audit["effective_groups_in_run_dir"]), ["embeddings", "generation", "ocr_vlm", "rerankers"])
        self.assertEqual(audit["missing_pieces"]["round1"], [])
        self.assertEqual(audit["missing_pieces"]["round2"], [])
        self.assertTrue(audit["support_status"]["round3"]["evidence_bundle_complete"])


if __name__ == "__main__":
    unittest.main()