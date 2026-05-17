import tempfile
import unittest
from pathlib import Path

from src.services.evidenceops_repository import (
    build_evidenceops_repository_snapshot,
    diff_evidenceops_repository_snapshots,
)
from src.storage.phase95_evidenceops_repository_snapshot import (
    load_evidenceops_repository_snapshot,
    save_evidenceops_repository_snapshot,
)


class Phase95EvidenceOpsRepositorySnapshotTests(unittest.TestCase):
    def test_snapshot_roundtrip_and_diff_detect_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repository_root = Path(tmp_dir) / "repo"
            snapshot_path = repository_root / ".phase95_evidenceops_repository_snapshot.json"
            (repository_root / "policies").mkdir(parents=True)
            policy_path = repository_root / "policies" / "POL-001_Information_Security_Policy_v1.pdf"
            policy_path.write_text("policy-v1", encoding="utf-8")

            first_snapshot = build_evidenceops_repository_snapshot(repository_root)
            save_evidenceops_repository_snapshot(snapshot_path, first_snapshot)
            loaded_snapshot = load_evidenceops_repository_snapshot(snapshot_path)

            policy_path.write_text("policy-v2", encoding="utf-8")
            (repository_root / "audit").mkdir(parents=True)
            (repository_root / "audit" / "AUD-001_Control_Test.md").write_text("audit", encoding="utf-8")
            second_snapshot = build_evidenceops_repository_snapshot(repository_root)
            diff = diff_evidenceops_repository_snapshots(loaded_snapshot, second_snapshot)

        self.assertIsNotNone(loaded_snapshot)
        self.assertEqual(loaded_snapshot["summary"]["total_documents"], 1)
        self.assertEqual(diff["changed_documents_count"], 1)
        self.assertEqual(diff["new_documents_count"], 1)
        self.assertEqual(diff["removed_documents_count"], 0)
        self.assertEqual(diff["changed_documents"][0]["document_id"], "POL-001")
        self.assertEqual(diff["new_documents"][0]["document_id"], "AUD-001")


if __name__ == "__main__":
    unittest.main()