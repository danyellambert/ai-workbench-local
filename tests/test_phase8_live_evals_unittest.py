import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_phase8_live_evals.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("phase8_live_evals", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


live_module = _load_module()


class Phase8LiveEvalsTests(unittest.TestCase):
    def test_build_live_eval_preflight_reports_missing_indexed_documents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            gold_manifest = root / "manifest.json"
            checklist_fixture = root / "checklist.json"
            evidence_gold = root / "evidence.json"
            document_path = root / "doc.pdf"
            gold_path = root / "gold.json"
            document_path.write_bytes(b"fake-pdf")
            gold_path.write_text("{}", encoding="utf-8")
            gold_manifest.write_text(
                '{"gold_sets": [{"task_type": "summary", "document_name": "doc.pdf", "document_path": "' + str(document_path) + '", "gold_path": "' + str(gold_path) + '"}]}',
                encoding="utf-8",
            )
            checklist_fixture.write_text('{"document_name": "checklist.pdf"}', encoding="utf-8")
            evidence_gold.write_text('{"documents": []}', encoding="utf-8")

            with patch.object(live_module, "_check_provider_profiles", return_value={"chat_ready": True, "embedding_ready": True}), patch.object(
                live_module,
                "_load_indexed_document_map",
                return_value={},
            ):
                preflight = live_module.build_live_eval_preflight(
                    provider="ollama",
                    gold_manifest_path=gold_manifest,
                    checklist_fixture_path=checklist_fixture,
                    evidence_gold_set_path=evidence_gold,
                )

        self.assertEqual(preflight["missing_indexed_documents"], ["doc.pdf"])
        self.assertFalse(preflight["structured_entries"][0]["indexed"])

    def test_build_live_eval_commands_includes_expected_suites(self) -> None:
        preflight = {
            "structured_entries": [
                {"task_type": "summary", "document_name": "doc.pdf", "runnable": True},
            ],
            "checklist_fixture": {"ready": True, "document_name": "checklist.pdf"},
            "evidence_gold_set": {"ready": True},
        }

        commands = live_module.build_live_eval_commands(
            provider="ollama",
            model="qwen2.5:7b",
            gold_manifest_path=Path("manifest.json"),
            checklist_fixture_path=Path("fixture.json"),
            evidence_gold_set_path=Path("evidence.json"),
            preflight=preflight,
            context_strategy="document_scan",
            skip_structured=False,
            skip_checklist=False,
            skip_evidence_cv=False,
            limit_structured_docs=None,
        )

        suite_names = [item["suite_name"] for item in commands]
        self.assertIn("structured_real_document_eval", suite_names)
        self.assertIn("checklist_regression", suite_names)
        self.assertIn("evidence_cv_gold_eval", suite_names)

    def test_run_live_eval_commands_captures_returncodes(self) -> None:
        with patch.object(live_module.subprocess, "run") as run_mock:
            run_mock.return_value.returncode = 0
            run_mock.return_value.stdout = "ok"
            run_mock.return_value.stderr = ""
            results = live_module.run_live_eval_commands(
                [
                    {"suite_name": "structured_real_document_eval", "label": "summary:doc", "argv": [sys.executable, "-c", "print('ok')"]}
                ]
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["returncode"], 0)
        self.assertIn("ok", results[0]["stdout_tail"])