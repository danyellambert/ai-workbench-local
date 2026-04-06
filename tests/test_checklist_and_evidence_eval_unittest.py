import importlib.util
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKLIST_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "evaluate_checklist_regression.py"
EVIDENCE_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "evaluate_evidence_cv_gold_set.py"
CHECKLIST_FIXTURE_PATH = PROJECT_ROOT / "phase5_eval" / "fixtures" / "06_checklist_who_surgical_gold.json"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checklist_module = _load_module("checklist_regression_eval", CHECKLIST_SCRIPT_PATH)
evidence_module = _load_module("evidence_cv_gold_eval", EVIDENCE_SCRIPT_PATH)


class ChecklistAndEvidenceEvalTests(unittest.TestCase):
    def test_checklist_eval_does_not_flag_cross_phase_overlap_as_collapsed_item(self) -> None:
        fixture = checklist_module._load_fixture(CHECKLIST_FIXTURE_PATH)
        payload = {
            "items": [
                {
                    "id": "item-1",
                    "title": "Confirm the patient’s name, procedure, and where the incision will be made",
                    "description": "Confirm the patient’s name, procedure, and where the incision will be made.",
                    "source_text": "Confirm the patient’s name, procedure, and where the incision will be made.",
                    "evidence": "Confirm the patient’s name, procedure, and where the incision will be made.",
                    "category": "Before skin incision",
                },
                {
                    "id": "item-2",
                    "title": "To Surgeon, Anaesthetist and Nurse: What are the key concerns for recovery and management of this patient",
                    "description": "To Surgeon, Anaesthetist and Nurse: What are the key concerns for recovery and management of this patient?",
                    "source_text": "To Surgeon, Anaesthetist and Nurse: What are the key concerns for recovery and management of this patient?",
                    "evidence": "What are the key concerns for recovery and management of this patient?",
                    "category": "Before patient leaves operating room",
                },
            ]
        }

        evaluation = checklist_module._evaluate_checklist_payload(payload, fixture)

        self.assertEqual(evaluation["collapsed_items"], [])

    def test_evidence_score_single_accepts_grounded_location_superset_match(self) -> None:
        score = evidence_module._score_single(
            predicted="43 Kiwi Lane, Auckland, NZ",
            expected="Auckland, NZ",
            status="confirmed",
        )

        self.assertEqual(score["tp"], 1)
        self.assertEqual(score["recall"], 1.0)


if __name__ == "__main__":
    unittest.main()